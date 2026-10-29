# ASTRA Decision-Rule Calibration

Fitted on seed 7 (n = 120); scored on unseen seeds 42, 1, 2, 3, 4.

| Rule | TV | w_PT | w_AR |
| :--- | ---: | ---: | ---: |
| Default (judgement) | 0.700 | 0.60 | 0.40 |
| Calibrated (learned) | 0.800 | 0.30 | 0.70 |

Calibration-set balanced accuracy: 100.0%, threshold margin: 0.040.

## Mean over unseen test seeds

| Policy | Accuracy | Balanced acc. | Precision | Recall | FPR |
| :--- | ---: | ---: | ---: | ---: | ---: |
| Formula alone, default rule | 65.7% | 67.3% | 100.0% | 34.6% | 0.0% |
| Formula + escalation, default rule | 100.0% | 100.0% | 100.0% | 100.0% | 0.0% |
| Formula alone, calibrated rule | 100.0% | 100.0% | 100.0% | 100.0% | 0.0% |
| Formula + escalation, calibrated rule | 100.0% | 100.0% | 100.0% | 100.0% | 0.0% |

## Per seed (formula alone, default vs calibrated)

| Seed | Default acc. | Default recall | Default FPR | Calibrated acc. | Calibrated recall | Calibrated FPR |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 42 | 65.8% | 34.9% | 0.0% | 100.0% | 100.0% | 0.0% |
| 1 | 65.8% | 34.9% | 0.0% | 100.0% | 100.0% | 0.0% |
| 2 | 65.8% | 34.9% | 0.0% | 100.0% | 100.0% | 0.0% |
| 3 | 65.0% | 33.3% | 0.0% | 100.0% | 100.0% | 0.0% |
| 4 | 65.8% | 34.9% | 0.0% | 100.0% | 100.0% | 0.0% |
