# Baseline (no-skill) response: long-retention-cost-risk

This file captures what a generic assistant produces WITHOUT the
cloudwatch-logs-retention-auditor skill loaded.

---

This log group has a 3650-day (~10 year) retention policy. That's a
very long retention period and given the stored bytes are around 250 GB,
storage cost will be material. The group is encrypted with a customer
KMS key and has a WARN metric filter configured.

You might want to consider whether 10 years of retention is really
needed for this log group. If a shorter period (e.g., 365 days) is
acceptable, you could reduce cost by changing the retention policy.
