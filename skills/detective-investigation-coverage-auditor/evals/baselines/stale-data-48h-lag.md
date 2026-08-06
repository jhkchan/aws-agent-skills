# Baseline (no-skill) response: stale-data-48h-lag

This file captures what a generic assistant produces WITHOUT the
detective-investigation-coverage-auditor skill loaded.

---

Your Detective behavior graph is enabled with all members collecting data.
However, account 222222222222 has a lastDataReceived timestamp of 2 days
ago, which suggests its data might be stale.

You should check whether there are any IAM permission issues or CloudTrail
problems in that account that might be preventing data ingestion.

GuardDuty and your organization configuration look healthy.
