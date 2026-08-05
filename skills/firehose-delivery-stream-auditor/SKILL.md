---
name: firehose-delivery-stream-auditor
description: >-
  Audits Amazon Kinesis Data Firehose (firehose) delivery streams for
  encryption-at-rest gaps (explicit NoEncryption, missing CMK, or
  absent EncryptionConfiguration defaulting to bucket policy),
  S3-destination BufferingHints quota violations, Lambda transformation
  backup/DLQ posture, CloudWatch error-logging silence (LoggingConfig
  disabled or absent — transformation failures become invisible),
  source-backup absence under dynamic partitioning (silent data-loss
  vector), and dynamic-partitioning structural integrity (metadata
  extraction wiring, ExtendedS3 requirement, RetryDuration=0 trap).
  Emits a deterministic first-fail-wins verdict
  (NO_ENCRYPTION | CONFIG_GAP | OK) per delivery stream with enumerated
  findings and CLI remediation. Use when reviewing Firehose delivery
  streams, validating SSE-KMS CMK coverage, auditing Lambda
  transformation resilience, checking dynamic-partitioning source
  backup, or hardening stream posture before production deployment.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline configuration classification.
  Live-account audits use aws firehose describe-delivery-stream,
  list-delivery-streams, list-tags-for-delivery-stream, and aws kms
  describe-key (AWS CLI v2, SSO or key-based credentials).
keywords:
  - Kinesis Data Firehose
  - delivery stream
  - firehose
  - SSE-KMS
  - SSE-S3
  - NoEncryption
  - KMSEncryptionConfig
  - BufferingHints
  - Lambda transformation
  - ProcessingConfiguration
  - LoggingConfig
  - CloudWatch error logging
  - S3BackupConfiguration
  - source backup
  - DynamicPartitioningConfiguration
  - MetadataExtraction
  - ExtendedS3DestinationConfiguration
  - S3DestinationConfiguration
  - data loss vector
  - silent failure
  - StartDeliveryStreamEncryption
  - firehose audit
tags: [firehose, kinesis, analytics, encryption, kms, lambda-transform, dynamic-partitioning, s3-destination, audit]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Analytics
  verdict_shape: "NO_ENCRYPTION | CONFIG_GAP | OK"
  when_to_use: >-
    Reviewing a Firehose delivery stream before production deployment,
    checking for NoEncryption plaintext destinations, validating SSE-KMS
    CMK coverage on S3 destinations, auditing Lambda transformation
    resilience (buffer, DLQ, source backup), checking dynamic-partitioning
    source-backup posture, or hardening stream posture for compliance.
  activation_triggers:
    - "audit this Firehose delivery stream"
    - "is my Firehose stream encrypted"
    - "check Firehose Lambda transformation"
    - "is dynamic partitioning configured correctly"
    - "Firehose source backup missing"
    - "CloudWatch error logging disabled Firehose"
    - "BufferingHints out of range"
    - "firehose data loss vector"
    - "firehose NoEncryption destination"
  invocation_schema: >-
    Input: either (a) a Firehose delivery-stream configuration JSON
    (describe-delivery-stream output), optionally paired with related KMS
    key + S3 bucket metadata, OR (b) a delivery-stream name/ARN for
    live-account audit. Output: deterministic STREAM/VERDICT/REASON/
    FINDINGS/REMEDIATION block per stream, where
    VERDICT ∈ {NO_ENCRYPTION, CONFIG_GAP, OK, ERROR}.
---

# Kinesis Data Firehose Delivery Stream Auditor

## Mindset

**One-line takeaway:** encryption is the only verdict-altering dimension
— everything else (buffering, Lambda, logging, source backup, dynamic
partitioning) is a `CONFIG_GAP`. Firehose is a streaming pipeline, so
silent-failure modes (transformation errors with no logging, dynamic
partitioning without source backup) are the dominant data-loss vector,
not the obvious S3 destination.

Firehose is a managed pipeline: source → optional transformation →
destination. Three properties make it unlike batch storage:

- **`NoEncryption` is explicit.** Firehose's `EncryptionConfiguration`
  block has two literal modes: `{NoEncryption: {}}` and
  `{KMSEncryptionConfig: {AWSKMSKeyArn: ...}}`. There is no "explicit
  SSE-S3" choice — absence of the block means the stream inherits the
  bucket default (still encrypted if the bucket has SSE-S3, but the
  stream itself has no declarative encryption posture). Explicit
  `NoEncryption` is the only path to plaintext delivery.
- **Transformation failures are silent by default.** Pre-2023 streams
  had no in-process error logging; `LoggingConfig` was added later and
  defaults to disabled on streams created via certain SDK paths. With
  `LoggingConfig.Enabled: false`, Lambda transformation errors,
  `MetadataExtraction` parse failures, and dynamic-partitioning
  retry-exhaustion are all invisible — the operator sees green checkmarks
  while records drop.
- **Dynamic partitioning + missing source backup = guaranteed data loss
  on any extraction failure.** When DP is enabled, Firehose evaluates a
  JQ/JSON-path expression per record. If the expression fails (or
  `RetryDuration` expires), the record is discarded unless
  `S3BackupConfiguration` captures the pre-partitioned source. There is
  no automatic fallback.

## Quick reference — first-fail-wins verdict

| Condition (evaluate top-down) | Verdict | Step |
|---|---|---|
| `ExtendedS3DestinationConfiguration.EncryptionConfiguration.NoEncryption: {}` (explicit) | **NO_ENCRYPTION** | Step 1a |
| `S3DestinationConfiguration` (legacy) with no `EncryptionConfiguration` block AND bucket policy / account SCP does not enforce SSE | **NO_ENCRYPTION** | Step 1b |
| `EncryptionConfiguration` block absent on a destination that supports it (relies on implicit bucket default) | **CONFIG_GAP** | Step 1c |
| `KMSEncryptionConfig.AWSKMSKeyArn` set but the referenced CMK is in a different region from the stream | **CONFIG_GAP** | Step 1d |
| `BufferingHints.SizeInMBs` or `IntervalInSeconds` outside `[1,128]` / `[60,900]` | **CONFIG_GAP** | Step 2 |
| `ProcessingConfiguration.Enabled: true` with Lambda processor + `S3BackupMode: Disabled` | **CONFIG_GAP** | Step 3 |
| `ProcessingConfiguration.Enabled: true` with no Lambda `BufferSizeInMBs` (1-3) / `BufferIntervalInSeconds` (0-300) | **CONFIG_GAP** | Step 3 |
| `LoggingConfig.Enabled: false` OR `LoggingConfig` absent on a stream with any processing enabled | **CONFIG_GAP** | Step 4 |
| `DynamicPartitioningConfiguration.Enabled: true` AND no `S3BackupConfiguration` (or `SourceBackupConfiguration`) | **CONFIG_GAP** | Step 5a |
| `DynamicPartitioningConfiguration.Enabled: true` AND `RetryDuration: 0` (or absent) | **CONFIG_GAP** | Step 5b |
| DP enabled with no `MetadataExtraction` processor in `ProcessingConfiguration` | **CONFIG_GAP** | Step 5c |
| DP enabled on a stream with `S3DestinationConfiguration` (legacy, not `ExtendedS3*`) | **CONFIG_GAP** | Step 5d |
| `KMSEncryptionConfig` set + valid `BufferingHints` + LoggingConfig enabled + (DP off OR DP+source backup) + (Lambda off OR Lambda+backup) | **OK** | Step 6 |

NO_ENCRYPTION strictly dominates CONFIG_GAP — encryption is a
data-protection failure and is never co-reported with a config gap.

## Pre-flight: stream metadata gate

Before evaluating destination configuration, classify the stream itself.
Several attributes short-circuit the audit:

| Attribute | Value | Effect |
|---|---|---|
| `DeliveryStreamStatus` | `CREATING` / `DELETING` | Stream is not delivering. Skip destination audit; emit `VERDICT: OK, REASON: Stream not yet ACTIVE — no live data exposure.` Do NOT flag a CREATING stream for missing CloudWatch logs (the log group is created post-ACTIVE). |
| `DeliveryStreamStatus` | `STARTING` / `STOPPING` (encryption toggle) | Mid-toggle state during `StartDeliveryStreamEncryption` / `StopDeliveryStreamEncryption`. Re-evaluate after the operation completes — the in-flight config is not the steady state. |
| `DeliveryStreamType` | `DirectPut` | Source is a producer writing directly. No Kinesis Data Stream upstream — source-backup checks apply to Firehose's own buffers, not a Kinesis stream. |
| `DeliveryStreamType` | `KinesisStreamAsSource` | A Kinesis Data Stream is the source. The upstream stream's retention (24h-365d) is a separate audit; Firehose does not re-buffer source data. Note for the operator, but not verdict-impacting. |
| Destination type | `HttpEndpoint` / `Redshift` / `Amazonopensearchservice` / `Splunk` / `AmazonOpenSearchServerless` | Non-S3 destinations have their own buffering/encryption semantics. The encryption audit (Step 1) still applies where the destination exposes `S3BackupConfiguration` (Redshift/Splunk/OpenSearch all stage in S3 first). Skip Steps 2 and 6 for the destination-native buffering, but DO evaluate S3 backup (Step 5) for the staging bucket. |
| `DeliveryStreamEncryptionConfigurationConfig` | present (stream-level) | Stream-level encryption (separate from destination `EncryptionConfiguration`) is for the Firehose queue itself, not the S3 destination. Rare; only DirectPut streams with `Source` are eligible. Do not confuse with destination-level encryption. |

**If the delivery-stream configuration JSON is malformed** (invalid
JSON, missing `DestinationDestination` block), output:

```text
STREAM: <name>
VERDICT: ERROR
REASON: Delivery-stream configuration is not valid JSON or is missing the DestinationSet — cannot classify.
REMEDIATION: Retrieve the canonical config with `aws firehose describe-delivery-stream --delivery-stream-name <name> --output json` and re-audit.
```

**Multi-stream / account-wide sweep note (pagination):** `aws firehose
list-delivery-streams` returns at most 10 streams per page by default
(`--limit` max 10, **not** the AWS-wide 50 or 100). Use
`--exclusive-start-delivery-stream-name` to iterate; silently truncating
the list is the most common missed-stream bug. For each stream,
`describe-delivery-stream` returns a single config document (no
pagination), but `list-tags-for-delivery-stream` paginates separately at
50 per page.

## Process — Classification logic (apply in order, first-fail-wins)

### Step 0: Expert knowledge — non-obvious Firehose behaviors that change classification

Each behavior below will produce a false positive if ignored:

- **`NoEncryption: {}` is an explicit, deliberate opt-out, not a default.**
  Firehose has no `SSE-S3` literal in the API. If you do not specify
  `KMSEncryptionConfig`, Firehose writes to S3 using whatever the bucket
  defaults to (typically SSE-S3 AES256). The only path to plaintext
  delivery is to set `NoEncryption: {}` explicitly — which means a
  `NoEncryption` finding is always a deliberate operator choice (or a
  Terraform module bug), never an oversight. Treat it as the highest-
  severity finding.

- **The destination field name is `ExtendedS3DestinationConfiguration`,
  NOT `S3DestinationConfiguration` (legacy).** The legacy field is
  frozen — no dynamic partitioning, no Lambda-aware backup, no
  ErrorOutputPrefix. Streams created after ~2019 should use
  `ExtendedS3DestinationConfiguration` exclusively. If you see
  `S3DestinationConfiguration` on a stream with DP enabled, it is a
  structural impossibility (Firehose API rejects it at creation), which
  means the input is stale or fabricated — re-fetch.

- **`LoggingConfig` is the in-process error log, not delivery metrics.**
  `LoggingConfig.LogGroupName` captures Firehose transformation errors
  (Lambda invocation failures, JQ parse errors, dynamic-partitioning
  retries). CloudWatch metrics (`AWS/Firehose` namespace) are always
  emitted regardless. An operator who checks metrics and sees
  `DeliveryToS3.Success` green may have zero transformation errors
  reaching S3 (silent drops) — only the log group reveals it. Pre-2023
  streams had no LoggingConfig at all; for those, treat absence as
  CONFIG_GAP only when processing is enabled.

- **`S3BackupMode: FailedDataOnly` (default) vs `Enabled` (all data).**
  The default backup captures only records Firehose itself flags as
  failed — but Lambda-transformation failures where the function returns
  success with malformed output are NOT captured by `FailedDataOnly`.
  Use `Enabled` for any stream where transformation correctness is
  load-bearing.

- **Dynamic partitioning `RetryDuration` is in seconds, max 300 (5min).**
  Default is 300. A value of `0` disables retry — a single JQ parse
  failure discards the record immediately. Treat `RetryDuration: 0` on
  a DP-enabled stream as a data-loss config gap regardless of source
  backup (source backup captures the raw record, not the partitioning
  intent).

- **DP requires `ExtendedS3DestinationConfiguration` + a
  `MetadataExtraction` processor with a JQ expression.** The expression
  runs per record. If the record is not valid JSON, the JQ parse fails.
  If your source emits JSON arrays (not newline-delimited JSON), every
  record will fail — wire a `RecordDeAggregation` processor BEFORE
  `MetadataExtraction`.

- **`KMSEncryptionConfig.AWSKMSKeyArn` must be a fully-qualified ARN,
  not a key ID or alias.** Firehose does not resolve aliases. A bare
  `mrk-abc123` or `alias/prod-firehose` value is silently accepted at
  creation time and fails at the first delivery attempt. Treat a
  non-ARN `AWSKMSKeyArn` as CONFIG_GAP.

- **The CMK must be in the SAME region as the delivery stream.** A
  multi-region key (`mrk-`) is permitted but each stream binds to one
  replica. Cross-region references fail at delivery time.

- **`ErrorOutputPrefix` uses magic templating: `{firehose:errorType}`,
  `{timestamp:yyyy-MM-dd-HH-mm-ss}`, `{partitionKeyFromQuery:...}`.**
  Without `ErrorOutputPrefix`, all errors land in a single prefix and
  you cannot distinguish Lambda transformation errors from S3 delivery
  errors. Recommend (not verdict-impacting) — surface in REMEDIATION.

- **`StartDeliveryStreamEncryption` / `StopDeliveryStreamEncryption`
  are state-changing APIs, not config edits.** They toggle encryption
  on an ACTIVE stream and take 5-60 seconds. A re-audit immediately
  after calling them will see `DeliveryStreamStatus: STARTING` /
  `STOPPING`, not the new steady state. Wait for ACTIVE.

- **BufferingHints interact with compression.** When
  `DataFormatConversionConfiguration` (JSON→Parquet/ORC) is enabled,
  the 128 MB `SizeInMBs` cap is per-block, but Parquet row-groups are
  typically 128 MB compressed ≈ 1-2 GB uncompressed. Operators who set
  `SizeInMBs: 1` thinking they want low latency end up with thousands
  of tiny Parquet files — a Glue/Athena query performance disaster.
  Flag only as a recommendation, not CONFIG_GAP.

- **`DeleteDeliveryStream --allow-force-delete` succeeds even with data
  in flight.** There is no undelete. Pre-flight must capture config
  before any destructive operation.

- **The S3 bucket policy and Firehose encryption are independent
  controls.** A bucket with `bucket-key-enabled` SSE-KMS will reject
  Firehose writes if Firehose is configured with `NoEncryption` — but
  only if the bucket policy enforces SSE. A bucket with no policy
  enforcement accepts plaintext writes silently. Do not assume the
  bucket enforces what Firehose does not.

- **`Amazon OpenSearch Service` / `Splunk` destinations stage data in
  S3 first.** They have their own `S3BackupConfiguration` for the
  staging buffer. Evaluate it for encryption + buffering as if it were
  a primary S3 destination, even though the user-facing destination is
  the index.

- **Tag-based access control is not evaluated by this skill.** If the
  audit reveals tags like `Environment=prod` or `PCI=true`, note them
  in REMEDIATION for downstream tag-policy enforcement — but do not
  make them verdict-impacting.

### Step 1: Encryption evaluation (drives NO_ENCRYPTION verdict)

Inspect `ExtendedS3DestinationConfiguration.EncryptionConfiguration`
(or `S3DestinationConfiguration.EncryptionConfiguration` on legacy
streams, or `S3BackupConfiguration.EncryptionConfiguration` for
staged destinations):

- **Step 1a — explicit NoEncryption:** if the block is
  `{NoEncryption: {}}` → **NO_ENCRYPTION**. Data is written to S3 in
  plaintext (modulo bucket-default enforcement). This is the highest-
  precedence finding; emit and stop.

- **Step 1b — legacy S3DestinationConfiguration with no encryption
  config AND no bucket-default evidence:** if the input is a legacy
  `S3DestinationConfiguration` with no `EncryptionConfiguration` AND
  no metadata showing the bucket enforces SSE → **NO_ENCRYPTION**. We
  cannot prove encryption; the legacy field provides no in-band
  guarantee. If the input explicitly states the bucket has SSE-S3 or
  SSE-KMS enforced via bucket policy, downgrade to CONFIG_GAP (the
  Firehose stream itself is unmanaged, but data is encrypted via the
  bucket layer).

- **Step 1c — absent EncryptionConfiguration on ExtendedS3:** if
  `ExtendedS3DestinationConfiguration` is present but the
  `EncryptionConfiguration` sub-block is missing entirely →
  **CONFIG_GAP**. ExtendedS3 streams should declare encryption
  explicitly; absence means the stream inherits the bucket default,
  which is operationally invisible (you have to inspect two resources
  to know the posture). Do NOT classify as NO_ENCRYPTION — S3 itself
  applies SSE-S3 by default if no bucket policy enforces otherwise,
  so data is still encrypted at rest in the common case.

- **Step 1d — CMK cross-region or non-ARN:** if
  `KMSEncryptionConfig.AWSKMSKeyArn` is set but the value is not a
  valid ARN, or the ARN's region differs from the stream's region →
  **CONFIG_GAP**. The stream will fail at delivery time. (A multi-
  region key ARN matching the stream region is fine.)

- **Step 1 — pass:** if `KMSEncryptionConfig.AWSKMSKeyArn` is a valid
  same-region ARN → encryption dimension passes; proceed to Step 2.

**NO_ENCRYPTION short-circuits** — do not evaluate Steps 2-5 if Step
1a or 1b fires. Encryption is a data-protection control that dominates
all configuration concerns.

### Step 2: S3 destination buffering (BufferingHints)

For each S3 destination (ExtendedS3, legacy S3, backup, staging),
inspect `BufferingHints`:

| Field | Valid range | Default | CONFIG_GAP trigger |
|---|---|---|---|
| `SizeInMBs` | `1` - `128` | `5` | outside range |
| `IntervalInSeconds` | `60` - `900` | `300` | outside range |

- Out-of-range values are quota violations (`ValidationException` at
  creation) — but Terraform/CloudFormation drift or a hand-edited config
  can produce them. Flag as CONFIG_GAP.
- Missing `BufferingHints` block entirely → use defaults; NOT a finding.
- `SizeInMBs: 128` with `IntervalInSeconds: 60` is valid but creates
  large files quickly — recommend (not flag) tuning for the downstream
  query engine (Athena, Glue).

### Step 3: Lambda transformation posture

If `ProcessingConfiguration.Enabled: true` and the `Processors` list
contains a processor with `Type: Lambda`:

- **Lambda buffer parameters:** the Lambda processor must specify
  `BufferSizeInMBs` (range 0.2-3 MiB, but the API only accepts whole
  MBs in [`1`, `3`]) and `BufferIntervalInSeconds` (range 60-900).
  Missing or out-of-range → **CONFIG_GAP**.
- **Source backup:** if `S3BackupMode` is `Disabled` (or absent) when
  Lambda transformation is enabled → **CONFIG_GAP**. A Lambda function
  that silently drops or malforms records has no recovery path without
  the source backup. `S3BackupMode: FailedDataOnly` does NOT catch
  Lambda-side silent corruption — only Firehose-detected failures.
  Recommend `Enabled`.
- **Lambda function DLQ:** Firehose does not require a Lambda DLQ
  (Firehose itself retries), but if the function has no DLQ and no
  destination-on-failure, asynchronous invocation failures are lost.
  Recommend (do not flag) configuring `DeadLetterConfig` on the
  function.

If `ProcessingConfiguration.Enabled: false` or no Lambda processor →
skip Step 3.

### Step 4: CloudWatch error logging

Inspect `LoggingConfig` (top-level on
`DeliveryStreamConfiguration`, not per-destination):

- `LoggingConfig.Enabled: false` AND any processing (Lambda, dynamic
  partitioning, format conversion) is enabled → **CONFIG_GAP**.
  Transformation failures are silent.
- `LoggingConfig` absent on a stream created after 2023-11-01 (when
  LoggingConfig became default-on for new streams) → **CONFIG_GAP**.
  Indicates a non-standard creation path.
- `LoggingConfig.Enabled: true` but `LogGroupName` is empty or does
  not match `arn:aws:logs:...` conventions → **CONFIG_GAP**.
- Pass condition: `Enabled: true` + valid `LogGroupName`.

For streams with no processing enabled (no Lambda, no DP, no format
conversion), LoggingConfig absence is NOT a finding — there are no
transformation errors to log.

### Step 5: Source backup under dynamic partitioning

If `ExtendedS3DestinationConfiguration.DynamicPartitioningConfiguration.Enabled: true`:

- **Step 5a — source backup required:** the stream MUST have
  `ExtendedS3DestinationConfiguration.S3BackupConfiguration`
  populated (or a top-level `SourceBackupConfiguration` on newer API
  versions). DP can fail per-record (JQ parse error) and Firehose
  will discard the record on retry exhaustion. Without source backup,
  this is silent data loss. Missing → **CONFIG_GAP**.

- **Step 5b — RetryDuration:** `DynamicPartitioningConfiguration.RetryDuration`
  in seconds, range `0`-`300`. If `RetryDuration: 0` (or absent with
  DP enabled) → **CONFIG_GAP**. Zero retry means any extraction
  failure is immediately fatal.

- **Step 5c — MetadataExtraction processor:** DP requires a
  `MetadataExtraction` processor in `ProcessingConfiguration.Processors`
  with `Parameters` containing `JsonParsingEngine` (`JQ-1.6`) and
  `MetaDataExtractionQuery` (the JQ expression). Missing or malformed
  → **CONFIG_GAP**. DP without extraction logic is structurally
  impossible (API rejects it at creation) — its presence indicates a
  stale or fabricated input.

- **Step 5d — ExtendedS3 requirement:** DP is incompatible with the
  legacy `S3DestinationConfiguration`. If the input shows DP enabled
  on a legacy destination → **CONFIG_GAP** (and note the input is
  suspect).

If DP is disabled or absent → skip Step 5 entirely.

### Step 6: Aggregation

Apply first-fail-wins ordering:

```text
if Step 1a or 1b fires:  verdict = NO_ENCRYPTION
elif any of Step 1c, 1d, 2, 3, 4, 5 fires:  verdict = CONFIG_GAP
else:  verdict = OK
```

NO_ENCRYPTION is reported alone (it dominates). For CONFIG_GAP, list
all fired findings in FINDINGS — do not stop at the first, because
multiple gaps compound (e.g., a stream with no LoggingConfig AND no
source backup has two independent data-loss vectors).

For OK, briefly note which dimensions passed to give the operator
confidence the audit was complete.

## Output format (per delivery stream)

```text
STREAM: <delivery-stream-name>
VERDICT: NO_ENCRYPTION | CONFIG_GAP | OK
REASON: <1-2 sentences citing the fired step and the worst finding>
FINDINGS:
  - [<SEVERITY>] <finding description (Step N)>
  - [<SEVERITY>] <finding description (Step N)>
REMEDIATION: <specific CLI per finding, or "None required" if OK>
```

Severity is informational (CRITICAL / HIGH / MEDIUM / LOW) and does
not change the verdict. It helps the operator prioritise when multiple
findings fire. Suggested mapping: NO_ENCRYPTION=CRITICAL; missing
source backup under DP=HIGH; LoggingConfig disabled=HIGH; buffering
quota violation=MEDIUM; everything else=LOW.

### Worked example — DP without source backup, CMK set

```text
STREAM: events-stream-prod
VERDICT: CONFIG_GAP
REASON: Dynamic partitioning is enabled but S3BackupConfiguration is
absent — any JQ extraction failure causes silent record loss (Step 5a).
LoggingConfig is also absent, so the failures would be invisible.
FINDINGS:
  - [HIGH] DP enabled with no S3BackupConfiguration — silent data-loss vector (Step 5a)
  - [HIGH] LoggingConfig absent with processing enabled — transformation errors invisible (Step 4)
  - [LOW] RetryDuration not set on DynamicPartitioningConfiguration (defaults to 300, verify intent) (Step 5b)
REMEDIATION:
  1. Add S3BackupConfiguration to the ExtendedS3 destination:
     aws firehose update-destination --delivery-stream-name events-stream-prod \
       --current-delivery-stream-version-id <version> \
       --destination-id destinationId-000000000001 \
       --extended-s3-update '{ "S3BackupConfiguration": { "RoleARN": "...", "BucketARN": "...", "Prefix": "backup/", "BufferingHints": {"SizeInMBs": 5, "IntervalInSeconds": 300} } }'
  2. Enable CloudWatch error logging:
     aws firehose update-destination ... --extended-s3-update (LoggingConfig is top-level: use aws firehose update-destination with the appropriate top-level field if your CLI version supports it, otherwise recreate the stream).
```

## Edge-case handling

- **Multi-destination streams (per-account destinations were deprecated
  in 2019).** Modern Firehose is single-destination per stream. If the
  input shows multiple `DestinationSet` entries, the input is stale —
  re-fetch with `describe-delivery-stream`.

- **`DeliveryStreamStatus: DELETING`.** A stream mid-deletion cannot
  accept new config but existing buffered data is still delivered (or
  dropped on force-delete). Emit `VERDDICT: OK, REASON: Stream is
  DELETING — no steady state to audit.` and do not flag.

- **Stream created via CloudFormation with `AWS::KinesisFirehose::DeliveryStream`.**
  CloudFormation drift detection does not cover `BufferingHints` or
  `ProcessingConfiguration` sub-fields — a hand-edit via `update-destination`
  will not appear in CloudFormation drift. Note in REMEDIATION when the
  config appears CloudFormation-managed.

- **KMS key disabled or pending deletion.** If the referenced CMK is
  `Disabled` or `PendingDeletion`, Firehose writes will fail with
  `KMSNotAccessible`. Surface as CONFIG_GAP (not NO_ENCRYPTION — the
  config declares encryption; the key is unavailable). Reference the
  kms-key-policy-auditor skill for key-state evaluation.

- **Bucket deleted or renamed out from under the stream.** Firehose
  does not pre-validate bucket existence after creation. A stream
  pointing at a deleted bucket will silently fail every delivery.
  Surface as CONFIG_GAP with `REASON: S3 destination bucket does not
  exist or is not accessible`.

- **Mixed SSE on backup vs primary.** If the primary destination uses
  CMK and the `S3BackupConfiguration` uses `NoEncryption` → the
  verdict is NO_ENCRYPTION (Step 1a fires on the backup destination).
  Backup plaintext is still plaintext at rest.

- **`Prefix` templating without partitionKeyFromQuery.** When DP is
  enabled, the `Prefix` field uses `{:partitionKeyFromQuery:...}` tokens.
  A literal `Prefix: "events/"` without the token means DP keys are
  ignored for path layout — data lands in a single prefix despite DP
  extraction. Recommend (do not flag) as a configuration smell.

## Anti-Patterns — NEVER

- NEVER classify `NoEncryption: {}` as anything other than NO_ENCRYPTION.
  It is an explicit, deliberate opt-out of at-rest encryption — the
  only API path to plaintext Firehose delivery. "But the bucket has
  SSE-KMS enforced" is not a defense; Firehose writes will fail at
  delivery time, which is an availability problem on top of a security
  problem.

- NEVER treat an absent `EncryptionConfiguration` block on
  `ExtendedS3DestinationConfiguration` as NO_ENCRYPTION. ExtendedS3
  streams fall back to the S3 bucket default, which is almost always
  SSE-S3 AES256. The finding is CONFIG_GAP (encryption is not
  declaratively managed at the Firehose layer) — calling it
  NO_ENCRYPTION is a false positive that causes alert fatigue.

- NEVER flag `BufferingHints` defaults (5 MiB / 300s) as a config gap.
  They are sensible AWS-shipped defaults. Only flag out-of-range
  values or (in REMEDIATION, not FINDINGS) pathological combinations
  like `SizeInMBs: 128` + `IntervalInSeconds: 60`.

- NEVER assume `S3BackupMode: FailedDataOnly` provides resilient backup.
  It captures only records Firehose itself flags as failed — Lambda
  functions returning 200 with malformed output are treated as success
  and the corrupted output is delivered without backup. For
  transformation-critical streams, `Enabled` (all data) is the only
  safe mode.

- NEVER classify a missing `LoggingConfig` on a stream with NO
  processing enabled as a config gap. There are no transformation
  errors to log — the finding is a false positive that produces noise.

- NEVER recommend disabling dynamic partitioning as remediation for a
  missing source backup. DP is the workload's reason for existing
  (event-routed S3 layouts). The remediation is to ADD source backup,
  not to remove the partitioning capability.

- NEVER call `StartDeliveryStreamEncryption` /
  `StopDeliveryStreamEncryption` without first verifying
  `DeliveryStreamStatus: ACTIVE`. Calling either during a CREATING or
  already-STARTING state returns `ValidationException` and provides no
  rollback path.

- NEVER conflate stream-level `DeliveryStreamEncryptionConfiguration`
  (queue-level encryption, DirectPut-only) with destination-level
  `EncryptionConfiguration`. They are independent controls with
  independent audit dimensions.

- NEVER treat a CMK referenced by alias (`alias/prod-firehose`) as
  valid. The `AWSKMSKeyArn` field requires a fully-qualified ARN.
  Aliases are silently accepted at creation and fail at first
  delivery. Flag as CONFIG_GAP.

- NEVER rely on CloudWatch metrics (`AWS/Firehose`) to detect
  transformation failures. Metrics show `DeliveryToS3.Success` as long
  as Firehose successfully writes SOMETHING to S3 — silently-dropped
  records do not move the metric. The LoggingConfig log group is the
  only authoritative source.

- NEVER assume `update-destination` is reversible. It is not — there
  is no rollback. The previous config is overwritten atomically.
  Always capture `describe-delivery-stream` output before any update
  for forensic reconstruction.

- NEVER flag a legacy `S3DestinationConfiguration` stream as CONFIG_GAP
  purely for being legacy. Legacy streams predate ExtendedS3 and are
  fully supported. Flag only if the legacy stream attempts to use DP
  or per-record processing (which ExtendedS3 is required for).

- NEVER recommend a multi-region CMK (`mrk-`) without confirming the
  stream's region has a replica. A multi-region key ARN resolves to a
  specific replica; the stream binds to that replica at creation.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`update-destination`, `StartDeliveryStreamEncryption`,
  `StopDeliveryStreamEncryption`, `DeleteDeliveryStream`), emit:
  `CONFIRM: About to <action> on stream <name> in account <account>.
  This affects <consequence>. Proceed? (yes/no)`. Do NOT execute
  until the operator confirms.
- **Capture current config before any update.**
  `aws firehose describe-delivery-stream --delivery-stream-name <name> --output json > /tmp/<name>-backup-$(date +%s).json`.
  `update-destination` is not reversible — the only rollback is a
  captured snapshot.
- **Verify `DeliveryStreamStatus: ACTIVE`** before any update. Updates
  to non-ACTIVE streams return `ValidationException`.
- **Verify the operator's role can call `firehose:UpdateDestination`.**
  Most read-only auditor roles CANNOT. Surface this BEFORE proposing
  the CLI command — a failed `AccessDenied` mid-remediation leaves
  the stream in an inconsistent state if the operator then attempts
  partial remediation manually.
- **For DP source-backup additions:** verify the backup bucket exists
  and the Firehose role has `s3:PutObject` on the backup prefix
  BEFORE running `update-destination`. A misconfigured backup bucket
  causes the update to succeed but every subsequent delivery to fail.
- **For CMK rotation / replacement:** the new CMK's key policy must
  grant the Firehose service principal
  `kms:GenerateDataKey` + `kms:Decrypt` BEFORE the
  `update-destination` call. Otherwise the first delivery post-update
  fails with `KMSNotAccessible`.
- **For `DeleteDeliveryStream --allow-force-delete`:** this is
  irreversible and drops in-flight buffered data. Require explicit
  operator sign-off AND a captured `describe-delivery-stream` backup.
- Prefer additive updates (add `S3BackupConfiguration`,
  enable `LoggingConfig`) over destructive updates (remove a
  processor, change the bucket). Additive updates cannot break the
  existing delivery path.

## Remediation guidance

**Ordering principle:** prefer additive over destructive. Add source
backup before changing the primary destination. Enable LoggingConfig
before changing transformation logic — otherwise the change is
unobservable.

### For NO_ENCRYPTION — explicit NoEncryption

1. Identify why `NoEncryption` was set. Common causes: a Terraform
   module that omits the block, a legacy stream from before SSE-KMS
   support, or a deliberate choice for a non-sensitive workload.
2. If the workload is sensitive (PII, financial, healthcare), enable
   SSE-KMS with a customer-managed key:
   ```bash
   aws firehose update-destination \
     --delivery-stream-name <name> \
     --current-delivery-stream-version-id <version> \
     --destination-id destinationId-000000000001 \
     --extended-s3-update '{
       "EncryptionConfiguration": {
         "KMSEncryptionConfig": { "AWSKMSKeyArn": "arn:aws:kms:us-east-1:111111111111:key/abc-123" }
       }
     }'
   ```
3. If the workload is non-sensitive and SSE-S3 (AES256) is acceptable,
   REMOVE the explicit `NoEncryption` block so the stream inherits the
   bucket default declaratively:
   ```bash
   # Update with an EncryptionConfiguration block that uses bucket default
   # (Firehose will write with SSE-S3 unless the bucket enforces SSE-KMS)
   aws firehose update-destination ... --extended-s3-update '{"EncryptionConfiguration": {"NoEncryption": {}}}'
   # ^ This is the literal API — to REMOVE the explicit opt-out, omit
   # the block entirely in the update payload, or use a fresh destination config.
   ```
4. Verify the CMK policy grants Firehose before the update (see
   Pre-flight). Re-audit with this skill after `DeliveryStreamStatus`
   returns to ACTIVE.

### For CONFIG_GAP — absent EncryptionConfiguration (Step 1c)

1. Add an explicit `KMSEncryptionConfig` block referencing a same-region
   CMK (preferred), or document acceptance of bucket-default SSE-S3 in
   the workload's risk register.
2. Re-audit after the update — the block should appear under
   `ExtendedS3DestinationConfiguration.EncryptionConfiguration`.

### For CONFIG_GAP — BufferingHints out of range (Step 2)

1. Correct the values to within `[1,128]` MiB and `[60,900]` seconds.
2. For Parquet/ORC destinations, prefer `SizeInMBs: 128` to amortise
   row-group write cost; for JSON/CSV, prefer the 5 MiB default.
3. `aws firehose update-destination --extended-s3-update '{"BufferingHints": {"SizeInMBs": 64, "IntervalInSeconds": 300}}'`

### For CONFIG_GAP — Lambda transformation without source backup (Step 3)

1. Add `S3BackupConfiguration` to the ExtendedS3 destination with a
   dedicated backup bucket and prefix:
   ```bash
   aws firehose update-destination --extended-s3-update '{
     "S3BackupMode": "Enabled",
     "S3BackupConfiguration": {
       "RoleARN": "arn:aws:iam::111111111111:role/firehose-backup",
       "BucketARN": "arn:aws:s3:::firehose-backup-prod",
       "Prefix": "lambda-source/",
       "BufferingHints": {"SizeInMBs": 5, "IntervalInSeconds": 300}
     }
   }'
   ```
2. Verify the backup bucket's lifecycle policy — long-running
   transformation streams accumulate backup data indefinitely.

### For CONFIG_GAP — LoggingConfig disabled or absent (Step 4)

1. Enable on the stream (top-level config, not per-destination):
   ```bash
   aws firehose update-destination --delivery-stream-name <name> \
     --current-delivery-stream-version-id <version> \
     --destination-id destinationId-000000000001 \
     --extended-s3-update '{"...": "..."}'
   # LoggingConfig is a top-level field on certain CLI versions; on older
   # versions, recreate the stream. Verify with: aws firehose help update-destination
   ```
2. Set a retention period on the log group (`logs put-retention-policy`)
   — Firehose error volume can be high on misconfigured transformations.

### For CONFIG_GAP — DP without source backup (Step 5a)

1. Add `S3BackupConfiguration` (same guidance as Step 3). The backup
   captures the pre-partitioned raw record, which is the recovery
   source when JQ extraction fails.
2. Verify the JQ expression against representative records using
   `jq '<expr>'` locally before relying on it in production.

### For CONFIG_GAP — DP with RetryDuration: 0 (Step 5b)

1. Set `RetryDuration` to 300 (the max) for maximum resilience:
   ```bash
   aws firehose update-destination --extended-s3-update '{
     "DynamicPartitioningConfiguration": {"Enabled": true, "RetryDuration": 300}
   }'
   ```
2. Investigate WHY RetryDuration is 0 — it is not the default, which
   means an operator explicitly chose immediate-fail semantics.

### For OK

1. No remediation required.
2. Recommend verifying the CMK rotation status (refer to
   kms-key-policy-auditor) — encryption posture is only as strong as
   the key.
3. Recommend an `ErrorOutputPrefix` template if not set:
   `!{partitionKeyFromQuery:errorType}/!{timestamp:yyyy/MM/dd}/` —
   enables error triage without full log inspection.
4. Recommend `S3BackupMode: Enabled` (all data) over
   `FailedDataOnly` for streams where transformation correctness is
   load-bearing.

## Deep reference: Firehose destination-shape matrix

| Destination type | EncryptionConfiguration supported | BufferingHints | S3BackupConfiguration | DP supported |
|---|---|---|---|---|
| `ExtendedS3DestinationConfiguration` | Yes (NoEncryption / KMSEncryptionConfig) | Yes | Yes | Yes |
| `S3DestinationConfiguration` (legacy) | Yes (same) | Yes | No | No |
| `HttpEndpointDestinationConfiguration` | No (endpoint-side) | Yes (seconds only) | Yes (staging) | No |
| `RedshiftDestinationConfiguration` | Yes (on the S3 staging copy) | Yes (copy command size) | Yes (staging) | No |
| `AmazonopensearchserviceDestinationConfiguration` | Yes (on S3 staging) | Yes | Yes (staging + backup) | No |
| `SplunkDestinationConfiguration` | Yes (on S3 backup) | Yes | Yes | No |
| `AmazonOpenSearchServerlessDestinationConfiguration` | Yes (on S3 staging) | Yes | Yes | No |

**Audit scope rule:** for non-S3 destinations, evaluate encryption and
backup on the S3 staging/backup layer (Steps 1, 3, 5). Skip Step 2's
size hints unless the destination exposes native buffering (most do
in seconds only, not MiB).

## Recent AWS features (2024-2026)

- **Apache Iceberg support (2024-2025):** Firehose can now deliver data directly to Apache Iceberg tables in S3. Auditors should verify that Iceberg table destinations have appropriate KMS encryption and that the commit frequency is tuned for the workload.
- **Snowflake and Redshift destination improvements (2024):** Enhanced Snowflake and Redshift destination support with improved buffering and error handling. Auditors should verify that destination credentials use Secrets Manager rather than plaintext.
- **Microsoft Fabric / OneLake destination (2024-2025):** Firehose now supports Microsoft Fabric OneLake as a destination. Auditors should verify that cross-cloud credentials are scoped appropriately.
- **Data transformation with Lambda — enhanced error handling:** Improved Lambda transformation error reporting with dead-letter queue support. The skill already covers this, but auditors should verify the DLQ is configured and monitored.

## Domain

AWS CloudOps / Kinesis Data Firehose Analytics & Data-Protection.
