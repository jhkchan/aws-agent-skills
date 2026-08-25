# Diagnostic Commands (load on demand) — CloudWatch Logs Retention Auditor

Pre-flight safety checks moved verbatim from SKILL.md. Load on demand before emitting any remediation CLI.


---

## Pre-flight safety checks (run before any remediation CLI) (moved from SKILL.md)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`PutRetentionPolicy`, `AssociateKmsKey`, `DeleteLogGroup`,
  `PutMetricFilter`, `PutSubscriptionFilter`, `DeleteMetricFilter`,
  `DeleteSubscriptionFilter`, `PutAnomalyDetector`), the auditor MUST
  emit:
  `CONFIRM: About to <action> on log group <name> in account
  <account>. This affects <consequence>. Proceed? (yes/no)`.
  Do NOT execute the CLI command until the operator confirms.
- **Back up filters before modification.** Capture
  `aws logs describe-metric-filters --log-group-name <name> --output json`
  and `aws logs describe-subscription-filters --log-group-name <name>
  --output json` BEFORE any change — filters are not versioned.
- **Verify retention value is in the allowed list** (1, 3, 5, 7, 14,
  30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 2192, 2557,
  2922, 3288, 3653). `PutRetentionPolicy` with any other value returns
  `InvalidParameterException` without changing state.
- **Verify CMK region and policy before `AssociateKmsKey`.** Region
  must match; key policy must permit `logs.<region>.amazonaws.com` to
  call `kms:GenerateDataKey` + `kms:Decrypt`. Without this, PutLogEvents
  and GetLogEvents fail immediately.
- **Confirm KMS-request cost tolerance** before CMK association.
  Estimate PutLogEvents batches/sec and project monthly KMS cost at
  $0.03 per 10,000 GenerateDataKey calls.
- **For `DeleteLogGroup`:** incident-response-only. Irreversible;
  deletes all streams and stored events; breaks producers until they
  recreate the group. Verify by checking CloudTrail for recent
  `PutLogEvents` before deletion.
- **For cross-account subscription filter changes:** audit the
  destination policy in the recipient account BEFORE modifying the
  sender's filter. Fixing the sender side does not close the boundary.
- **Prefer additive over destructive changes.** Add filters / detectors
  / alarms (do not break existing access). Removing a subscription
  filter or shortening retention can break downstream consumers —
  capture backup and coordinate with owners first.
