# Baseline (no-skill) response: untriaged-high-pii-findings

This file captures what a generic assistant produces WITHOUT the
macie-data-classification-auditor skill loaded.

---

Macie has found some sensitive data in your S3 buckets. There are 3 high
severity findings:

1. AWS credentials found in s3://customer-data/exports/q3-customers.csv
2. Social security numbers (45000) found in the same file
3. Credit card numbers (12000) found in s3://customer-data/exports/payment-history.csv

These findings have not been archived yet. You should review them and
take action. The AWS credentials finding is especially concerning — you
should rotate those keys immediately.

The classification job completed successfully and Security Hub export is
enabled, which is good.
