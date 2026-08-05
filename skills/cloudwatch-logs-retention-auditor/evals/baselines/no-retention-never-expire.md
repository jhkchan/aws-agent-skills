# Baseline (no-skill) response: no-retention-never-expire

This file captures what a generic assistant produces WITHOUT the
cloudwatch-logs-retention-auditor skill loaded — the contrast that
proves the skill adds structure (deterministic VERDICT, enumerated
FINDINGS, specific remediation, first-fail-wins ordering).

---

This CloudWatch Logs group doesn't have a retention policy set, which
means logs are kept indefinitely. That can lead to growing storage
costs over time. The group does have a KMS key associated and an
error-count metric filter configured, which is good.

You may want to set a retention period that matches your operational
or compliance needs, e.g., 30, 60, or 90 days. You can do this with
the AWS CLI or console.

Stored bytes are around 524 MB so the current cost impact is limited,
but it will keep growing without a retention policy.
