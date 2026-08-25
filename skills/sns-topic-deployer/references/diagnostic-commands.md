# Diagnostic Commands — SNS Topic Deployer

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Pre-flight safety checks (run before any deployment CLI)

- **Confirm the topic name is available:** `create-topic` is idempotent —
  returns the ARN if it exists.
- **For FIFO topics, confirm name ends in `.fifo`.** Suffix is permanent.
- **For SSE-KMS, confirm the KMS key exists** and the policy grants
  subscriber access: `aws kms describe-key` + `aws kms get-key-policy`.
- **For cross-account topics, confirm BOTH** topic policy AND subscriber
  IAM/key policies allow access (intersection required).
- **For delivery logging, confirm the CloudWatch IAM role exists** with
  trust policy for `sns.amazonaws.com`.
- **For mobile push, confirm the platform application exists:**
  `aws sns list-platform-applications`.
- **Capture existing configuration for rollback** (if updating):
  `aws sns get-topic-attributes --topic-arn <arn> --output json > backup.json`.
  Topic attributes are not versioned — no undo without backup.
