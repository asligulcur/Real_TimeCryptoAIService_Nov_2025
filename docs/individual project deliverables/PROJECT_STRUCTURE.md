# Project Structure

This document outlines the final directory structure of the Real-Time Crypto Volatility Detection project.

```
.
├── README.md
├── PROJECT_STRUCTURE.md
├── requirements.txt
├── config.yaml                              # Main configuration file
│
├── FINAL_INSTRUCTOR_ASSESSMENT.md          # Instructor evaluation (98/100)
├── HANDOFF_COMPLETE.md                     # Handoff package checklist
├── INSTRUCTOR_EVALUATION.md                # Initial evaluation
│
├── data/
│   ├── processed/
│   │   ├── features.parquet
│   │   ├── reference_features.parquet
│   │   ├── test_data.parquet
│   │   └── train_data.parquet
│   └── raw/                                # Empty (raw data stored in Kafka topic ticks.raw)
│
├── docker/
│   ├── compose.yaml
│   └── Dockerfile.ingestor
│
├── docs/
│   ├── PROJECT_EXECUTIVE_SUMMARY.md
│   ├── scoping_brief.pdf
│   ├── feature_spec.md
│   ├── model_card_v1.md                    # Production model card
│   ├── genai_appendix.md
│   ├── predictions_analysis.md             # Predictions validation report
│   ├── handoff_scope.md                    # Handoff philosophy guide
│   └── _archive/
│       ├── learning/
│       │   └── Complete_Learning_Study_Guide.md
│       └── TEACHING_METHOD.md
│
├── features/
│   └── build_features.py
│
├── models/
│   ├── MODEL_CARD.md                       # Detailed model documentation
│   ├── MODEL_CARD.pdf                      # PDF version
│   ├── train.py
│   ├── infer.py
│   ├── artifacts/
│   │   ├── random_forest.joblib
│   │   └── logistic_regression.joblib
│   └── data/
│       ├── train.parquet
│       └── test.parquet
│
├── notebooks/
│   ├── eda.ipynb
│   └── 03_model_training.ipynb
│
├── reports/
│   ├── evidently_data_drift_report.html
│   ├── model_evaluation_summary.md
│   └── model_evaluation_report.pdf
│
├── scripts/
│   ├── ws_ingest.py
│   ├── kafka_consume_check.py
│   └── replay.py
│
├── tests/
│   ├── check_mlflow_runs.py
│   ├── test_mlflow_runs.py
│   └── test_inference_speed.py
│
├── handoff/                                 # Team Project Handoff Package
│   ├── README.md                           # Team quick start guide
│   ├── config.yaml                         # Configuration
│   ├── .env.example                        # Environment template
│   ├── requirements.txt                    # Dependencies
│   │
│   ├── docker/                             # Infrastructure
│   │   ├── compose.yaml
│   │   └── Dockerfile.ingestor
│   │
│   ├── docs/                               # Documentation
│   │   ├── feature_spec.md
│   │   ├── model_card_v1.md
│   │   └── genai_appendix.md
│   │
│   ├── models/artifacts/                   # Pre-trained models
│   │   ├── random_forest.joblib
│   │   └── logistic_regression.joblib
│   │
│   ├── data/                               # Sample data
│   │   ├── raw_10min_slice.parquet
│   │   └── features_10min_slice.parquet
│   │
│   └── reports/                            # Evaluation artifacts
│       ├── predictions.csv
│       ├── model_eval.md
│       ├── model_eval.pdf
│       └── evidently_data_drift_report.html
│
└── mlruns/                                 # MLflow experiment tracking
    └── (Experiment data for 3+ models)
```

---

## Key Components Guide

### Core Application Logic
-   **`config.yaml`**: Main configuration file for all components (Kafka, MLflow, features, models).
-   **`docker/compose.yaml`**: The master file that defines and orchestrates all services (Kafka, Zookeeper, MLflow).
-   **`scripts/ws_ingest.py`**: **(Milestone 1)** Connects to the Coinbase WebSocket, ingests live data, and publishes it to the `ticks.raw` Kafka topic.
-   **`features/build_features.py`**: **(Milestone 2)** Consumes from `ticks.raw`, engineers features (volatility, returns), and saves them to a Parquet file.
-   **`models/train.py`**: **(Milestone 3)** The definitive script for training, evaluating, and logging the Z-Score, Logistic Regression, and Random Forest models with MLflow.
-   **`models/infer.py`**: **(Milestone 3)** Loads the production model and runs inference, with a `--benchmark` flag to test performance.

### Data
-   **`data/processed/features.parquet`**: The final, clean dataset used for training and testing the models.
-   **`data/processed/train_data.parquet`**: Training split (80%).
-   **`data/processed/test_data.parquet`**: Test split (20%).

### Documentation
-   **`README.md`**: The main entry point for understanding the project, its setup, and how to run it.
-   **`PROJECT_STRUCTURE.md`**: (This file) A map of the project's final directory structure.
-   **`docs/PROJECT_EXECUTIVE_SUMMARY.md`**: A high-level summary of the project's goals, architecture, and key results.
-   **`docs/scoping_brief.pdf`**: The initial business case and project scope.
-   **`docs/feature_spec.md`**: A detailed specification of the features engineered for the model (17KB, publication-quality).
-   **`docs/model_card_v1.md`**: Production model documentation following industry standards.
-   **`docs/genai_appendix.md`**: A log of all interactions with Generative AI, as required (14+ documented instances).
-   **`docs/predictions_analysis.md`**: Comprehensive analysis validating model predictions behavior (95/5 NORMAL/SPIKE split).
-   **`docs/handoff_scope.md`**: Philosophy and rationale for what belongs in handoff package vs. main repository.
-   **`docs/_archive/learning/Complete_Learning_Study_Guide.md`**: A comprehensive guide detailing the key concepts and learnings from each milestone.

### Models & Experiments
-   **`models/MODEL_CARD.md`**: Detailed documentation for the final production model (Random Forest).
-   **`models/artifacts/`**: Pre-trained model files (Random Forest: 102KB, Logistic Regression: 1.5KB).
-   **`mlruns/`**: The directory where MLflow stores all experiment tracking data. This is the ground truth for all model versions and metrics (3+ runs logged).

### Reports & Notebooks
-   **`notebooks/eda.ipynb`**: Exploratory Data Analysis, including the data-driven threshold selection for volatility spikes (95th percentile = 0.041799).
-   **`reports/evidently_data_drift_report.html`**: The final data drift report (776KB).
-   **`reports/model_evaluation_summary.md`**: A summary of the final model comparison.
-   **`reports/model_evaluation_report.pdf`**: PDF version of model evaluation.

### Testing & Validation
-   **`tests/check_mlflow_runs.py`**: Validates ≥2 MLflow runs exist (requirement verification).
-   **`tests/test_mlflow_runs.py`**: MLflow connection and run validation.
-   **`tests/test_inference_speed.py`**: Performance benchmark test (validates < 2x real-time requirement).

### Handoff Package (Team Project)
-   **`handoff/`**: Complete, deployment-ready package for team project (16 files, ~3.8MB).
    -   Pre-trained models (ready to load)
    -   Sample data (10-minute slice: raw + features)
    -   Documentation (feature spec, model card, GenAI appendix)
    -   Docker setup (compose.yaml, Dockerfile.ingestor)
    -   Configuration (config.yaml, .env.example)
    -   Sample predictions (predictions.csv with 32,233 predictions)
    -   See `docs/handoff_scope.md` for philosophy and rationale.

### Assessment Documents
-   **`FINAL_INSTRUCTOR_ASSESSMENT.md`**: Comprehensive instructor evaluation (Grade: 98/100, A+).
-   **`HANDOFF_COMPLETE.md`**: Step-by-step handoff package completion checklist.
-   **`INSTRUCTOR_EVALUATION.md`**: Initial evaluation and feedback.
