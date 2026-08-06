# Baseline (no-skill) response: no-retention-trumps-encryption

This file captures what a generic assistant produces WITHOUT the
cloudwatch-logs-retention-auditor skill loaded.

---

This log group has no retention policy and no KMS key associated. Logs
will be retained indefinitely and are encrypted at rest with the
default CloudWatch Logs service-managed key.

If you have compliance requirements around customer-managed keys, you
should associate a KMS CMK. You should also set a retention policy to
control storage cost.

The group is fairly small (~50 MB stored bytes), so this is not
urgent, but it's worth cleaning up.
