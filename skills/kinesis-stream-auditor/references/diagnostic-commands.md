# Diagnostic Commands — Kinesis Stream Auditor

Pre-flight gates and pre-flight safety check listings moved verbatim from SKILL.md for progressive disclosure. Load on demand.

## Pre-flight: stream metadata gate (run before classification) (moved from SKILL.md)

Before evaluating dimensions, classify the stream itself. Several attributes
short-circuit the audit.

**Multi-stream / account-wide sweep note (pagination):** when auditing every
stream in an account, `aws kinesis list-streams` returns at most 100 per page
(use `--next-token`). For each stream, also call `list-stream-consumers` (caps
at 100 per page) and `list-shards` (caps at 1,000 per page, use
`--next-token`). Always drain `NextToken` to completion — the long tail of
streams is where stale, unencrypted, or over-retained streams hide.

**Live-account pre-flight checks (skip if doing offline config audit):**
1. Verify the caller's identity can run `kinesis:UpdateStreamMode` /
   `StartStreamEncryption` if remediation is intended — most read-only auditor
   roles CANNOT, and remediation commands will fail with `AccessDenied`.
2. Verify CloudWatch has the `AWS/Kinesis` namespace ingesting — without it,
   `GetRecords.IteratorAgeMilliseconds` (the stream-level consumer-lag metric)
   has no data and the audit cannot assess consumer health.
3. Snapshot `aws kinesis list-stream-consumers --stream-arn <arn>` BEFORE any
   mode or encryption change — consumers are not migrated automatically when
   switching from KMS to NONE; they continue to decrypt with the old key until
   they re-read from `TRIM_HORIZON`.

| Attribute | Value | Effect on audit |
|---|---|---|
| `StreamStatus` | `ACTIVE` | Normal operation. Proceed with full audit. |
| `StreamStatus` | `CREATING` | Stream not yet available. Note as operational: `PutRecord`/`GetRecords` fail. Classify metadata but mark transitional. |
| `StreamStatus` | `UPDATING` | Resharding or encryption change in progress. `UpdateShardCount` is blocked until ACTIVE. Note but do not block classification. |
| `StreamStatus` | `DELETING` | Stream being deleted — irrecoverable. Output ERROR: stream is being deleted. |
| `StreamMode` | `PROVISIONED` | Shard count is customer-managed. Evaluate shard cost, quota, and capacity. |
| `StreamMode` | `ON_DEMAND` | Shard count is auto-managed. Skip shard-count quota check. Evaluate per-stream-hour cost vs data volume. |

**If the stream configuration is malformed** (missing required fields,
unparseable), output:

```text
STREAM: <stream-name>
VERDICT: ERROR
REASON: Stream configuration is incomplete or malformed — cannot classify.
REMEDIATION: Retrieve the canonical summary with aws kinesis describe-stream-summary --stream-name <name> and re-audit.
```

## Pre-flight safety checks (run before any remediation CLI) (moved from SKILL.md)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`StartStreamEncryption`, `StopStreamEncryption`, `UpdateShardCount`,
  `IncreaseStreamRetentionPeriod`, `DecreaseStreamRetentionPeriod`,
  `UpdateStreamMode`), the auditor MUST emit:
  `CONFIRM: About to <action> on stream <name> in account <account>. This
  affects <consequence>. Proceed? (yes/no)`
  Do NOT execute the CLI command until the operator confirms.

- **StartStreamEncryption key-id validation.** When emitting a
  `StartStreamEncryption` command, verify the KeyId exists and the KMS key is
  ENABLED: `aws kms describe-key --key-id <id>`. A key in `Disabled` or
  `PendingDeletion` state will cause `StartStreamEncryption` to fail with
  `KMSDisabledException`.

- **Retention decrease is irreversible for expired data.** When emitting
  `DecreaseStreamRetentionPeriod`, note that records older than the new
  retention period are immediately deleted and unrecoverable. Confirm no
  consumer needs the older data before decreasing.

- **UpdateStreamMode is one-way for on-demand to provisioned.** Switching
  from ON_DEMAND to PROVISIONED sets the shard count based on the current
  on-demand capacity. Verify the resulting shard count is within budget
  before switching. Switching back to ON_DEMAND is possible but takes effect
  immediately.

- **Enhanced fan-out consumer registration cost.** Each enhanced fan-out
  consumer incurs per-consumer-AU-hour charges (~$0.028/consumer-AU-hour in
  us-east-1). Confirm the consumer is needed before recommending
  `RegisterStreamConsumer`.

- **Capture pre-change state for rollback.** Before any modification, capture:
  `aws kinesis describe-stream-summary --stream-name <name> --output json >
  /tmp/<name>-backup-$(date +%s).json`. There is no undo for retention
  decreases or encryption-key changes.

