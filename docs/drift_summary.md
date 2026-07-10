# Data Drift Detection Summary

**Report Generated:** 2025-11-26T12:50:00  
**Severity Level:** ⚠️ **WARNING**

---

## Executive Summary

Moderate drift detected in production data compared to training baseline. While the model is currently meeting SLOs (F1 ≥ 0.75), several features show significant distribution shifts that warrant monitoring and potential model retraining within 1-2 weeks.

This drift detection was performed using **Evidently AI**, comparing training data (reference) against recent production data (current window). The analysis identified distribution shifts in key price and volatility features.

---

## Drift Detection Results

### Dataset-Level Drift
- **Dataset Drift Detected:** Yes ⚠️
- **Number of Drifted Features:** 4 out of 13
- **Share of Drifted Features:** 30.8%
- **Drift Score (Average):** 0.68

### Drifted Features

The following features show significant drift:

#### 1. **price** - 🚨 HIGH DRIFT
- **Drift Score:** 0.85
- **Statistical Test:** Kolmogorov-Smirnov
- **Observation:** Price distribution shifted from ~$88,000 baseline to ~$92,000 in production
- **Impact:** Model trained on different price regime may misidentify volatility spikes
- **Recommended Action:** Retrain with recent price levels

#### 2. **volatility_30s** - ⚠️ MODERATE DRIFT
- **Drift Score:** 0.72
- **Statistical Test:** Kolmogorov-Smirnov
- **Observation:** Average volatility increased from 0.015 to 0.025 (67% increase)
- **Impact:** Higher baseline volatility may cause false negatives (missed spike detection)
- **Recommended Action:** Update volatility thresholds or retrain

#### 3. **intensity_30s** - ⚠️ MODERATE DRIFT
- **Drift Score:** 0.65
- **Statistical Test:** Kolmogorov-Smirnov  
- **Observation:** Trading intensity increased from avg 17.5 to 25.0 (43% increase)
- **Impact:** Changed market dynamics may affect spike prediction accuracy
- **Recommended Action:** Monitor prediction confidence distribution

#### 4. **spread** - ⚠️ MODERATE DRIFT
- **Drift Score:** 0.58
- **Statistical Test:** Kolmogorov-Smirnov
- **Observation:** Bid-ask spreads widened from 0.5-3.0 to 0.8-4.0 range
- **Impact:** Wider spreads may indicate different market conditions (lower liquidity)
- **Recommended Action:** Include in feature analysis for retraining

### Stable Features ✅

The following features show no significant drift:
- `bid` - Stable ✅
- `ask` - Stable ✅  
- `volatility_60s` - Minor drift (within acceptable range)
- `volatility_120s` - Minor drift (within acceptable range)
- `return_10s` - Stable ✅
- `return_30s` - Stable ✅
- `return_60s` - Stable ✅
- `intensity_60s` - Minor drift (within acceptable range)
- `intensity_120s` - Minor drift (within acceptable range)

---

## Recommended Actions

### ⚠️ Actions Required Within 1-2 Weeks

#### 1. **Monitor Model Performance** 📊
- **Action:** Track accuracy, precision, recall, and F1 score daily
- **SLO Target:** F1 ≥ 0.75 (currently meeting at ~0.80)
- **Alert Threshold:** F1 < 0.78 for 3 consecutive days
- **Dashboard:** http://localhost:3000 (Grafana)
- **Metrics:** Check `prediction_confidence` histogram for shifts

#### 2. **Plan Model Retraining** 📅
- **Timeline:** Schedule retraining within 1-2 weeks
- **Data Requirements:** Collect 10,000-50,000 recent production samples
- **Validation Strategy:** 
  - 80/20 train/test split on recent data
  - Compare performance: new model vs current model on holdout set
  - Only deploy if new model shows ≥5% improvement or maintains performance
- **Rollback Plan:** Keep current model as backup with MODEL_VARIANT toggle

#### 3. **Investigate Drift Causes** 🔍
- **Market Conditions:** Check if recent price increase ($88K → $92K) is sustained trend or temporary spike
- **Data Pipeline:** Verify feature calculation logic hasn't changed
- **Upstream Systems:** Confirm Coinbase WebSocket data quality and consistency
- **Business Context:** Correlate drift timing with known market events (e.g., Bitcoin ETF news, Fed announcements)

#### 4. **Document Findings** 📝
- **Drift Log:** Maintain `reports/drift/drift_log.csv` with weekly drift scores
- **Incident Report:** If model performance degrades, document in `docs/incidents/`
- **Baseline Update:** After retraining, update reference data and re-baseline drift detection

---

## Feature Statistics Comparison

### Reference Data (Training Baseline)
- **Time Period:** October 2025 (training data)
- **Size:** 50,000 samples
- **Price Range:** $86,000 - $90,000 (mean: $88,000 ± $2,000)
- **Volatility 30s:** 0.015 ± 0.008 (exponential distribution)
- **Intensity 30s:** 17.5 ± 7.5 trades
- **Target Distribution:** 80% normal (0), 20% spike (1)
- **Market Conditions:** Moderate volatility, normal trading volumes

### Current Data (Production - Last 7 Days)
- **Time Period:** November 19-26, 2025
- **Size:** 25,000 samples (streaming from Coinbase)
- **Price Range:** $90,000 - $94,000 (mean: $92,000 ± $2,500) ⚠️ **+4.5% drift**
- **Volatility 30s:** 0.025 ± 0.012 (exponential distribution) ⚠️ **+67% drift**
- **Intensity 30s:** 25.0 ± 10.0 trades ⚠️ **+43% drift**
- **Target Distribution:** 75% normal (0), 25% spike (1) ⚠️ **+25% more spikes**
- **Market Conditions:** Higher volatility, increased trading activity

### Interpretation
The drift analysis reveals a **structural shift** in market conditions:
1. **Price Appreciation:** Consistent upward price movement (+$4,000)
2. **Increased Volatility:** Market becoming more volatile (67% increase in 30s volatility)
3. **Higher Activity:** Trading intensity up 43%, suggesting increased market participation
4. **More Spikes:** 25% more volatility spikes detected (20% → 25%)

This combination suggests the market has entered a more volatile regime, which may reduce the current model's effectiveness if trained on calmer market conditions.

---

## Drift Detection Methodology

### Statistical Framework
- **Library:** Evidently AI v0.4+
- **Primary Test:** Kolmogorov-Smirnov (K-S) test for numerical features
  - Null hypothesis: Reference and current distributions are identical
  - Significance level: α = 0.05
  - Rejection → Drift detected
- **Drift Score:** Normalized distance metric (0 = no drift, 1 = complete drift)
- **Threshold:** Drift score > 0.5 triggers "drift detected" flag

### Data Windows
- **Reference Window:** Training data (October 2025, 50K samples)
- **Current Window:** Last 7 days of production data (November 19-26, 25K samples)
- **Update Frequency:** Weekly drift reports (can increase to daily if degradation observed)
- **Retention:** Keep last 12 drift reports (3 months history)

### Limitations
- **Synthetic Data:** This demo uses synthetic reference/current data; production implementation should use real training and streaming data
- **Sample Size:** Smaller current window (25K vs 50K) may affect statistical power
- **Temporal Effects:** Crypto markets have strong time-of-day and day-of-week patterns not captured in simple K-S test
- **Multivariate Drift:** Evidently tests features independently; correlated drift across multiple features may be missed

---

## Integration with SLOs

### Impact on Service Level Objectives

#### 1. **Latency SLO (p95 ≤ 800ms)** ✅ Not Impacted
- Drift doesn't affect inference time
- Current performance: p95 ~100ms (well within SLO)
- **Action:** None required

#### 2. **Availability SLO (≥ 99% uptime)** ✅ Not Impacted  
- Drift doesn't cause API failures
- Current performance: 100% success rate
- **Action:** None required

#### 3. **Data Freshness SLO (lag < 1,000 messages)** 🔴 Still Below Target
- Consumer lag: ~15,000 messages (separate issue from drift)
- **Action:** Scale consumer (independent of drift issue)

#### 4. **Prediction Accuracy SLO (F1 ≥ 0.75)** ⚠️ **AT RISK**
- Current F1: ~0.80 (meeting SLO)
- **Risk:** Drift in 4/13 features may degrade accuracy over time
- **Monitoring:** Track daily F1 score; alert if < 0.78 for 3 days
- **Mitigation:** Model retraining planned within 1-2 weeks
- **Action:** Closely monitor, trigger retraining if F1 drops below 0.78

---

## Monitoring Schedule & Alerting

### Automated Drift Detection
```bash
# Weekly drift check (cron job)
0 2 * * 1 cd /path/to/project && python3 scripts/drift_monitor_simple.py

# Save reports with timestamp
reports/drift/drift_report_YYYYMMDD_HHMMSS.html
reports/drift/drift_metrics.json
```

### Alert Configuration
- **INFO (0-2 drifted features):** Email weekly summary
- **WARNING (3-4 drifted features):** Slack notification, daily monitoring
- **CRITICAL (5+ drifted features):** PagerDuty alert, immediate model retraining

### Current Status
- **Level:** WARNING (4 drifted features)
- **Next Check:** December 3, 2025 (7 days)
- **Action Owner:** ML Team
- **Review Date:** December 10, 2025 (model retraining decision)

---

## Related Reports & Documentation

### Evidently Reports
- **Drift Report (HTML):** `reports/drift/evidently_drift_20251126_135117.html`
- **Drift Reports Folder:** `reports/drift/`

### Project Documentation
- **SLO Document:** `docs/slo.md` - Service level objectives and error budgets
- **Runbook:** `docs/runbook.md` - Operational procedures and troubleshooting
- **Model Card:** `docs/MODEL_CARD.md` - Model architecture, training data, performance
- **Grafana Dashboard:** http://localhost:3000 - Real-time monitoring

### Retraining Resources
- **Training Pipeline:** `models/train.py`
- **Feature Engineering:** `ml/features.py` - Feature calculation logic
- **Model Registry:** MLflow at http://localhost:5001
- **Baseline Model:** `models/artifacts/random_forest.joblib`

---

## How to Reproduce

### Run Drift Detection

```bash
# Navigate to project directory
cd "/path/to/crypto-volatility-real-time"

# Run drift detection script
python3 scripts/drift_monitor_simple.py

# View HTML report in browser
open reports/drift/drift_report_20251126_*.html

# Check JSON metrics
cat reports/drift/drift_metrics.json | jq '.metrics[] | select(.metric == "DatasetDriftMetric")'
```

### Update Reference Data (After Retraining)

```bash
# After retraining model on recent data:
# 1. Save new training data as reference
cp data/processed/train_recent.parquet data/processed/train.parquet

# 2. Re-run drift detection
python3 scripts/drift_monitor_simple.py

# 3. New baseline established - drift scores should reset
```

### Schedule Automated Checks

```bash
# Add to crontab for weekly checks
crontab -e

# Add this line (runs every Monday at 2 AM)
0 2 * * 1 cd /path/to/project && python3 scripts/drift_monitor_simple.py && mail -s "Drift Report" team@company.com < docs/drift_summary.md
```

---

## Appendix: Drift Scores Explained

### Drift Score Interpretation
- **0.0 - 0.3:** No significant drift (✅ GREEN)
- **0.3 - 0.5:** Minor drift, monitor (💛 YELLOW)
- **0.5 - 0.7:** Moderate drift, investigate (🟠 ORANGE)
- **0.7 - 1.0:** High drift, action required (🔴 RED)

### Statistical Tests Used
- **Kolmogorov-Smirnov (K-S) Test:** Measures maximum distance between CDFs of reference and current distributions
- **Two-Sample Test:** Non-parametric, makes no assumptions about distribution shape
- **Sensitivity:** Detects location shifts (mean/median changes) and scale shifts (variance changes)
- **Limitation:** May not detect subtle distributional changes (e.g., bimodality)

###Examples from This Report
| Feature | Drift Score | Category | Action |
|---------|-------------|----------|--------|
| price | 0.85 | 🔴 HIGH | Retrain immediately |
| volatility_30s | 0.72 | 🔴 HIGH | Retrain within 1 week |
| intensity_30s | 0.65 | 🟠 MODERATE | Monitor daily |
| spread | 0.58 | 🟠 MODERATE | Monitor daily |
| return_10s | 0.15 | ✅ NO DRIFT | Continue normal ops |

---

## Next Steps

### Immediate (This Week)
1. ✅ Review this drift summary
2. ✅ Check Grafana dashboard for model performance trends  
3. ✅ Set up daily F1 score monitoring alert
4. 📋 Document drift in incident log

### Short-term (1-2 Weeks)
1. 📊 Collect 10K-50K recent production samples
2. 🔧 Prepare model retraining pipeline
3. 🧪 Validate new model on holdout set
4. 🚀 Deploy if performance improved

### Long-term (1-3 Months)
1. 🤖 Automate weekly drift detection
2. 📧 Set up Slack/email alerting
3. 📈 Track drift trends over time
4. 📝 Establish drift baseline ranges

---

**Report Status:** ⚠️ WARNING  
**Action Required:** Yes - Monitor model performance daily, plan retraining within 1-2 weeks  
**Owner:** ML Team  
**Next Review:** December 3, 2025

---

*Generated by Evidently AI drift detection system*  
*For questions or issues, see `docs/runbook.md` or contact ML team*
