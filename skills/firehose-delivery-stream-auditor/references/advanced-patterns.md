# Kinesis Data Firehose Delivery Stream Auditor — advanced patterns (moved from SKILL.md)

Loaded on demand — content moved verbatim from SKILL.md (progressive disclosure; nothing deleted).

## Mindset (moved from SKILL.md)

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

## Step 0: Expert knowledge — non-obvious Firehose behaviors (moved from SKILL.md)

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

## Edge-case handling (moved from SKILL.md)

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

## Deep reference: Firehose destination-shape matrix (moved from SKILL.md)

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

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **Apache Iceberg support (2024-2025):** Firehose can now deliver data directly to Apache Iceberg tables in S3. Auditors should verify that Iceberg table destinations have appropriate KMS encryption and that the commit frequency is tuned for the workload.
- **Snowflake and Redshift destination improvements (2024):** Enhanced Snowflake and Redshift destination support with improved buffering and error handling. Auditors should verify that destination credentials use Secrets Manager rather than plaintext.
- **Microsoft Fabric / OneLake destination (2024-2025):** Firehose now supports Microsoft Fabric OneLake as a destination. Auditors should verify that cross-cloud credentials are scoped appropriately.
- **Data transformation with Lambda — enhanced error handling:** Improved Lambda transformation error reporting with dead-letter queue support. The skill already covers this, but auditors should verify the DLQ is configured and monitored.
