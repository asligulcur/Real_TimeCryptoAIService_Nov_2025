# Model Evaluation Summary

This report summarizes the performance of the models trained by the `models/train.py` script.

**Generated:** 2025-11-08

---

## Final Model Comparison

The following table shows the performance metrics for the baseline and machine learning models on the test set.

| Model                 | F1 Score | PR-AUC | Precision | Recall |
| --------------------- | -------- | ------ | --------- | ------ |
| zscore                | 0.9938   | 1.0000 | 0.9877    | 1.0000 |
| logistic              | 0.7544   | 0.9870 | 1.0000    | 0.6056 |
| random_forest         | 0.9984   | 1.0000 | 0.9969    | 1.0000 |

---

## Conclusion

-   **Best Model (by PR-AUC):** The Z-Score and Random Forest models both achieved a near-perfect PR-AUC. Given its simplicity, the **Z-Score model** is identified as the best performing model.
-   **All models were successfully logged to MLflow.**
-   **The Random Forest model was saved as the production artifact.**

This data is sourced directly from the final, successful execution of the `train.py` script.
