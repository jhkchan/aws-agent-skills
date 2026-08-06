# Baseline (no-skill) response: job-failed-no-coverage

This file captures what a generic assistant produces WITHOUT the
macie-data-classification-auditor skill loaded.

---

It looks like there is a classification job configured but it has failed.
The job "pii-scan-prod" has a status of FAILED, so it is not producing
any findings. Automated discovery is also disabled.

You should investigate why the job failed and try to fix it. It could be
an IAM permission issue or the bucket might not exist anymore. You should
also consider enabling automated discovery as a backup.
