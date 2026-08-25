# Diagnostic Commands (load on demand) — Billing Account Auditor

Live-account pre-flight and data-collection command listings moved verbatim from SKILL.md. Loaded on demand.

---

## Live-account data collection commands (moved from SKILL.md)

**Live-account data collection commands:**

```bash
# Root MFA + access-key status
aws iam get-account-summary --profile <p> --query 'SummaryMap.[AccountMFAEnabled,AccountAccessKeysPresent]'

# IAM billing access (account-level master switch — NOT in IAM)
aws account get-contact-information --profile <p>  # billing contact email
# The IAM-billing-access setting is console-only:
# Billing console → Account → IAM User and Role Access to Billing Information

# Cost Anomaly Detection monitors
aws ce list-cost-anomaly-monitors --profile <p> --region us-east-1

# Cost Anomaly Detection subscriptions (alerts)
aws ce get-anomaly-subscriptions --profile <p> --region us-east-1 \
  --monitor-arn <monitor-arn>

# Budgets
aws budgets describe-budgets --account-id <acct> --profile <p>

# Free-tier usage alerts (console preference, no direct CLI):
# Billing console → Billing preferences → Receive Free Tier Usage Alerts
```
