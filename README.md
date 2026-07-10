# Real-Time Crypto Volatility Detection

A streaming ML system that ingests live BTC-USD market data from Coinbase, engineers rolling-window features in real time, serves volatility-spike predictions over an HTTP API, and monitors the whole pipeline with Prometheus, Grafana, and Evidently.

The interesting part of this project is not the model — it's the operational scaffolding around it: resilient WebSocket ingestion with exponential backoff and a circuit breaker, Kafka buffering, a rule-based fallback model with an env-var rollback switch, a full metrics/dashboards/alerting stack, and drift detection. That is the story worth reading.

> **On the model metric:** the classifier here is a deliberate stand-in, and its scores are not presented as a performance result. The label is a threshold on `volatility_60s`, which the model also receives as an input feature, so the reported F1 ≈ 0.998 / PR-AUC ≈ 1.0 reflect target leakage rather than predictive skill. The [Results](#results--the-leakage-caveat) section documents this precisely. The value of the project is the production pipeline, not the model.

---

## Why this design is interesting

Real-time inference on market data is mostly a systems problem. Prices arrive continuously and unreliably, the upstream feed drops, consumers fall behind, and a bad model needs to be pulled without downtime. This project treats those concerns as first-class:

- **Ingestion survives a flaky upstream.** The WebSocket ingestor reconnects with exponential backoff (1s → 60s cap, up to 10 attempts) and wraps the Kafka producer in a circuit breaker and per-message send retries.
- **Kafka decouples produce from consume.** Ticks land on `ticks.raw`; the featurizer computes features into `ticks.features`. A slow or restarting consumer doesn't drop upstream data.
- **There is a fallback model and a rollback path.** A rule-based baseline can replace the ML model via a single environment variable (`MODEL_VARIANT=baseline`) plus an API restart.
- **The system is observable.** The API exposes Prometheus metrics (latency histograms, request/error counters, prediction-class and confidence distributions); a separate exporter publishes Kafka consumer lag; Grafana visualizes it; Evidently produces drift reports.

---

## Architecture

```
┌───────────────────────────────────────────────────────────────────────────┐
│ INGESTION                                                                   │
│   Coinbase WebSocket  ──▶  ws_ingest_resilient.py                           │
│   (live BTC-USD ticks)     • exponential backoff reconnect                  │
│                            • circuit breaker + Kafka send retries           │
└───────────────────────────────────┬───────────────────────────────────────┘
                                     ▼  produces to topic ticks.raw
┌───────────────────────────────────────────────────────────────────────────┐
│ MESSAGE QUEUE                                                               │
│   Zookeeper (2181)  ◀──  Apache Kafka (9092 host / 29092 internal)          │
│                          topics: ticks.raw, ticks.features                  │
└───────────────────────────────────┬───────────────────────────────────────┘
                                     ▼  consumed by
┌───────────────────────────────────────────────────────────────────────────┐
│ FEATURE ENGINEERING                                                         │
│   features/featurizer.py  (rolling 500-tick buffer, deque)                  │
│     • returns        windows 10s / 30s / 60s                                │
│     • volatility     windows 30s / 60s / 120s  (std of tick returns)        │
│     • trade intensity windows 30s / 60s / 120s                              │
│     • bid-ask spread  → 13 features total; written to Parquet + Kafka       │
└───────────────────────────────────┬───────────────────────────────────────┘
                                     ▼
┌───────────────────────────────────────────────────────────────────────────┐
│ SERVING                                                                     │
│   FastAPI (8000): /predict  /predict/batch  /health  /version  /metrics     │
│     ├─▶ Random Forest (production, models/artifacts/random_forest.joblib)   │
│     └─▶ Rule-based baseline (fallback via MODEL_VARIANT=baseline)           │
│   MLflow (5001 → 5000): experiment tracking + artifacts                     │
└───────────────────────────────────┬───────────────────────────────────────┘
                                     ▼  exposes /metrics
┌───────────────────────────────────────────────────────────────────────────┐
│ MONITORING                                                                  │
│   kafka_lag_monitor.py (9091)  ──▶  Prometheus (9090)  ──▶  Grafana (3000)  │
│   Evidently  ──▶  HTML drift reports (reports/drift/)                       │
└───────────────────────────────────────────────────────────────────────────┘
```

Components in `docker/compose.yaml`: Zookeeper, Kafka, MLflow, API, Prometheus, Grafana. The ingestor, featurizer, and Kafka-lag exporter run as standalone Python processes (not in Compose) — see the pipeline commands below.

---

## Quickstart

Requires Docker and Python 3.11+ (the API image uses Python 3.13).

```bash
git clone <repo-url> && cd <repo-dir>
cp .env.example .env

# Start infra + API (Kafka, Zookeeper, MLflow, Prometheus, Grafana, API)
cd docker && docker compose up -d

# Install Python deps for the pipeline scripts (run from repo root)
cd .. && pip install -r requirements.txt

# Verify the API
curl http://localhost:8000/health
```

Run the live data pipeline (separate terminals, from repo root):

```bash
python scripts/ws_ingest_resilient.py       # Coinbase ticks -> Kafka ticks.raw
python features/featurizer.py                # features -> ticks.features + Parquet
python scripts/kafka_lag_monitor.py          # consumer-lag exporter on :9091
```

Try a prediction:

```bash
curl -X POST http://localhost:8000/predict -H 'Content-Type: application/json' \
  -d '{"price":91234.56,"bid":91234.0,"ask":91235.0,"spread":1.0,
       "volatility_30s":0.0123,"volatility_60s":0.0145,"volatility_120s":0.0167,
       "return_10s":0.0001,"return_30s":0.0003,"return_60s":0.0005,
       "intensity_30s":15.2,"intensity_60s":28.5,"intensity_120s":52.3}'
```

Consoles: API docs `http://localhost:8000/docs` · MLflow `http://localhost:5001` · Prometheus `http://localhost:9090` · Grafana `http://localhost:3000` (admin/admin). Note: the Prometheus config scrapes the API (`:8000`) and the lag exporter (`:9091`); the lag panel stays empty until `kafka_lag_monitor.py` is running.

---

## Results & the leakage caveat

**Do not quote the model accuracy as a real-world result.** The training pipeline as written measures a near-tautology.

How the label is built (`scripts/create_train_test_split.py:36`):

```python
df['volatility_spike'] = (df['volatility_60s'] > 0.041799).astype(int)
```

The exact same `volatility_60s` column is then included in the model's input features (`models/train.py:56-63`, `config.yaml:67-80`, `api/main.py:50-64`). So the model is handed the quantity the label is a deterministic threshold of. Two consequences:

- The reported test scores (Random Forest F1 ≈ 0.9984, PR-AUC ≈ 1.0; even the trivial z-score baseline scores F1 ≈ 0.994) reflect the model rediscovering `volatility_60s > 0.0418`, not predicting anything. The three volatility features account for ~79% of Random Forest feature importance (`models/artifacts/feature_importance.csv`).
- Because the label uses the *current* `volatility_60s` rather than a *future* window, this is not a forecasting task at all as coded — despite `config.yaml` declaring `target_horizon: 60`. The horizon is never applied.

The train/test split is an additional, secondary problem: it is a **random** stratified `train_test_split` (`scripts/create_train_test_split.py:57-62`), not a temporal split, which leaks across time for a time-series problem. (This is moot next to the label leakage above, but worth fixing too.)

**To make the metric meaningful, the label must be decoupled from the features** — e.g. define the target as a *future* volatility spike over a forward horizon (using `target_horizon`), exclude present/overlapping volatility columns from the feature set, and switch to a time-ordered (walk-forward) split. Until then, treat the model as a placeholder and the pipeline — not the score — as the deliverable.

What *is* verified and honest to report:

| Item | Measured value | Source |
|---|---|---|
| Feature dataset size | 32,237 feature rows (25,789 train / 6,448 test) | `data/processed/*.parquet` |
| Spike rate (label prevalence) | ~5.0% | computed from the data |
| Model inference cost | ~0.004 ms/sample (batched, ~248k samples/s) | `models/artifacts/inference_benchmark.txt` |
| End-to-end HTTP p95 latency | 189 ms over a 20-request load test | `LOAD_TEST_REPORT.md` |

Note the latency: single-prediction *model* inference is microseconds, but the measured end-to-end HTTP p95 was 189 ms on a small (20-request) load test — which the report itself flags as failing a <100 ms target. The "~100 ms p95" figure in older docs is not supported by the artifact; the honest number is 189 ms p95 at very low load, dominated by HTTP/serialization overhead rather than the model.

---

## Key engineering decisions

**Resilient ingestion.** `scripts/ws_ingest_resilient.py` implements exponential backoff (1s base, 60s cap, ×2, up to 10 attempts), a circuit breaker with a half-open probe state, and a Kafka producer wrapped in send-retry logic. `scripts/kafka_consumer_resilient.py` adds reconnection and commit-retry handling with offset commits on shutdown.

**Kafka as a buffer.** Decoupling ingestion from featurization means a restarting or lagging featurizer replays from Kafka instead of losing ticks.

**Baseline fallback + rollback.** `ml/baseline.py` is a transparent rule-based predictor (weighted thresholds on volatility, return, intensity). The API selects it via `MODEL_VARIANT=baseline`, enabling a fast rollback when the ML model misbehaves. (See limitations for a Docker packaging caveat.)

**Observability.** `api/main.py` defines ~12 Prometheus metric families — latency histograms (`predict_latency_seconds`, `api_request_duration_seconds`), request/error counters, prediction-class and confidence distributions, and model-variant gauges. `scripts/kafka_lag_monitor.py` exports four consumer-lag metrics on `:9091`. Prometheus scrapes both; a provisioned Grafana dashboard (`docker/grafana/dashboards/`) charts latency, error rate, and consumer lag.

**Drift detection.** Evidently generates data-drift reports (KS test, Wasserstein distance) into `reports/drift/`. See limitations.

**Experiment tracking.** `models/train.py` logs all three models (z-score baseline, logistic regression, Random Forest) with params, metrics, and artifacts to MLflow.

---

## Limitations & known issues

- **Model metric is leakage-driven** (see above) — the single most important thing to fix before presenting any accuracy claim.
- **Random, non-temporal split** for time-series data.
- **The API is decoupled from the live feature stream.** `/predict` takes a features JSON body; nothing currently consumes `ticks.features` and calls the API automatically. The streaming path and the serving path are demonstrated but not wired end to end.
- **Baseline rollback is not container-safe as packaged.** `Dockerfile.api` copies `api/` and `models/artifacts/` but not `ml/`, and `api/main.py` imports the baseline from `ml/baseline.py`. `MODEL_VARIANT=baseline` will therefore fail inside the built image until `ml/` is added to the Dockerfile.
- **Drift reports use synthetic data.** `scripts/generate_evidently_tutorial_style.py` fabricates reference/current samples with injected drift to demonstrate the real Evidently API; it does not (yet) run drift on the live feature distribution. It also requires a separate Python 3.11 environment due to an Evidently/Pydantic incompatibility with newer Python.
- **SLO figures in older docs are aspirational** — availability/error-rate/rollback-time numbers are targets, not results from a sustained production run. Only the values in the Results table are measured.

---

## Repository layout

```
scripts/     ws_ingest_resilient.py, kafka_consumer_resilient.py,
             kafka_lag_monitor.py, create_train_test_split.py, drift/replay tools
features/    featurizer.py — real-time rolling-window feature engineering
models/      train.py, infer.py, artifacts/ (random_forest.joblib, feature_importance.csv)
ml/          baseline.py — rule-based fallback model
api/         main.py (FastAPI), Dockerfile config, examples
docker/      compose.yaml, prometheus.yml, grafana/ provisioning + dashboards
data/        processed/ (features.parquet, train/test splits), eda/
docs/        MODEL_CARD.md, slo.md, runbook.md, drift docs, architecture diagram
reports/     model evaluation summaries, Evidently drift HTML
tests/       load test, inference-speed, integration, MLflow checks
config.yaml  central configuration (Kafka, WebSocket, features, model, monitoring)
```

More detail — SLO definitions, incident runbook, model card, and drift methodology — lives under `docs/`.

---

Author: Asli Gulcur. Data source: Coinbase Exchange WebSocket (`BTC-USD` ticker).
