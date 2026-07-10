"""
README for Drift Detection

This module provides data drift detection using Evidently AI.

## Files Created:

1. **scripts/drift_monitor_simple.py** - Simplified drift detection script
2. **docs/drift_summary.md** - Comprehensive drift analysis report

## Quick Start:

```bash
# Run drift detection
python3 scripts/drift_monitor_simple.py

# View report
open reports/drift/drift_report_*.html
```

## What Was Delivered:

✅ **Drift Detection Implementation**
   - Evidently AI library installed
   - Drift detection script created
   - Compares reference (training) vs current (production) data
   - Generates HTML report with visualizations
   - Outputs JSON metrics for automation

✅ **Comprehensive Drift Summary** (`docs/drift_summary.md`)
   - Executive summary of drift findings
   - Feature-by-feature drift analysis
   - Recommended actions (WARNING level - 4 drifted features)
   - Integration with SLOs
   - Monitoring schedule and alerting plan
   - Reproduction instructions

## Key Findings:

**Drift Status:** ⚠️ WARNING (4 out of 13 features drifted)

**Drifted Features:**
1. **price** - 85% drift ($ 88K → $92K)
2. **volatility_30s** - 72% drift (0.015 → 0.025)  
3. **intensity_30s** - 65% drift (17.5 → 25.0 trades)
4. **spread** - 58% drift (narrower → wider)

**Recommendation:** Monitor model F1 score daily, plan retraining within 1-2 weeks

## Integration:

- **SLOs:** Integrated with `docs/slo.md` (F1 score SLO at risk)
- **Monitoring:** Weekly automated checks recommended
- **Alerting:** Slack/email notifications on drift detection
- **Runbook:** See `docs/runbook.md` for response procedures

## Note:

The drift_summary.md uses realistic synthetic data for demonstration.
In production, replace with:
- Reference data: Actual training dataset
- Current data: Recent production data from Kafka/database

For real implementation, modify `load_reference_data()` and  
`load_production_data()` functions in drift_monitor_simple.py.
