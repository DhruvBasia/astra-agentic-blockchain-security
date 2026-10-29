# ASTRA Learned-Classifier Baseline

Test population: seed 42 (n = 120). Cross-seed training population: seed 7. Cross-validation: stratified 5-fold on the test population. Isolation-forest contamination: 0.5.

## Hand-written rule on the test population

| Decision rule | Accuracy | Balanced acc. | Precision | Recall | FPR |
| :--- | ---: | ---: | ---: | ---: | ---: |
| Formula alone (TF >= TV) | 65.8% | 67.5% | 100.0% | 34.9% | 0.0% |
| Formula + escalation | 100.0% | 100.0% | 100.0% | 100.0% | 0.0% |

## Cross-validation on the test population

### agent-level features (9)

| Decision rule | Accuracy | Balanced acc. | Precision | Recall | FPR |
| :--- | ---: | ---: | ---: | ---: | ---: |
| Logistic regression | 100.0% | 100.0% | 100.0% | 100.0% | 0.0% |
| Random forest | 100.0% | 100.0% | 100.0% | 100.0% | 0.0% |
| Isolation forest (unsupervised) | 85.0% | 84.6% | 81.7% | 92.1% | 22.8% |

### indicator-level features

| Decision rule | Accuracy | Balanced acc. | Precision | Recall | FPR |
| :--- | ---: | ---: | ---: | ---: | ---: |
| Logistic regression | 100.0% | 100.0% | 100.0% | 100.0% | 0.0% |
| Random forest | 100.0% | 100.0% | 100.0% | 100.0% | 0.0% |
| Isolation forest (unsupervised) | 95.0% | 94.8% | 92.5% | 98.4% | 8.8% |

## Trained on another seed, tested on the test population

### agent-level features (9)

| Decision rule | Accuracy | Balanced acc. | Precision | Recall | FPR |
| :--- | ---: | ---: | ---: | ---: | ---: |
| Logistic regression | 100.0% | 100.0% | 100.0% | 100.0% | 0.0% |
| Random forest | 100.0% | 100.0% | 100.0% | 100.0% | 0.0% |
| Isolation forest (unsupervised) | 89.2% | 89.6% | 98.1% | 81.0% | 1.8% |

### indicator-level features

| Decision rule | Accuracy | Balanced acc. | Precision | Recall | FPR |
| :--- | ---: | ---: | ---: | ---: | ---: |
| Logistic regression | 100.0% | 100.0% | 100.0% | 100.0% | 0.0% |
| Random forest | 100.0% | 100.0% | 100.0% | 100.0% | 0.0% |
| Isolation forest (unsupervised) | 92.5% | 92.9% | 100.0% | 85.7% | 0.0% |

## Hand weights vs learned weights (agent-level)

| Feature | Hand weight | Learned coefficient |
| :--- | ---: | ---: |
| risk:Sybil | -0.30 | -1.799 |
| risk:Wallet | -0.20 | -0.902 |
| risk:Finney | -0.20 | -0.404 |
| risk:Eclipse | -0.30 | -1.939 |
| pt:I | +0.25 | +1.546 |
| pt:T | +0.20 | +0.704 |
| pt:N | +0.20 | +0.264 |
| pt:H | +0.20 | +0.162 |
| pt:B | +0.15 | -0.154 |

Standardised logistic-regression coefficients fitted on the training seed; positive favours admission. Compare signs and relative sizes with the hand weights.
