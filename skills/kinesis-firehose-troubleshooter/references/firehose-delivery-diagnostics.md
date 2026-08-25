# Kinesis Data Firehose Delivery Diagnostics Reference

Supplementary reference for the Kinesis Data Firehose Troubleshooter
skill. Use when diagnosing delivery stream failures, picking the right
diagnostic command, interpreting CloudWatch metrics, or mapping a
symptom to its root cause.

## Diagnostic commands (quick lookup)

| Command | Use | Key fields |
|---|---|---|
| `aws firehose describe-delivery-stream` | Stream config + state | `DeliveryStreamStatus`, `DeliveryStreamType`, `Source`, `Destinations[*]` |
| `aws firehose list-delivery-streams` | Stream inventory | `DeliveryStreamNames[*]`, `DeliveryStreamARN` |
| `aws firehose list-tags-for-stream` | Tag-based scoping | `Tags[*]` |
| `aws firehose update-destination` | Modify destination config | `CurrentDeliveryStreamVersionId`, `DestinationId` |
| `aws firehose start-delivery-stream-encryption` | Enable SSE-KMS | `DeliveryStreamName` |
| `aws firehose stop-delivery-stream-encryption` | Disable SSE | `DeliveryStreamName` |
| `aws cloudwatch get-metric-statistics` | Per-destination metrics | `DeliveryToS3.Success`, `DeliveryToOpenSearch.Success`, etc. |
| `aws logs filter-log-events` | Firehose / Lambda logs | `log-group-name: /aws/kinesisfirehose/*` or `/aws/lambda/*` |
| `aws logs describe-log-groups` | Log group inventory | `logGroupNamePrefix` |
| `aws lambda get-function` | Transform config | `Runtime`, `Timeout`, `MemorySize`, `Role` |
| `aws lambda get-policy` | Transform resource policy | `Policy` (JSON with Firehose invoke grant) |
| `aws glue get-table` | Conversion schema | `StorageDescriptor.Columns`, `Parameters` (SerDe) |
| `aws glue get-database` | Conversion catalog | `Name`, `LocationUri` |
| `aws s3api head-bucket` | S3 destination existence | 200 or 404 |
| `aws s3api get-bucket-location` | S3 region | `LocationConstraint` |
| `aws s3api head-object` | Object size (conversion check) | `ContentLength` |
| `aws opensearch describe-domain` | OpenSearch destination | `Endpoints`, `ClusterConfig`, `EncryptionAtRestOptions` |
| `aws opensearch describe-domain-health` | OpenSearch live state | `ClusterHealth`, `Nodes` |
| `aws redshift describe-clusters` | Redshift destination | `ClusterStatus`, `NodeType`, `NumberOfNodes` |
| `aws kms describe-key` | KMS key state | `KeyState` (`Enabled` / `Disabled`) |
| `aws kms get-key-policy` | KMS key policy | `Statement[*].Principal`, `Action` |
| `aws iam simulate-principal-policy` | IAM test without change | `EvalDecision`, `MatchedStatements` |
| `aws cloudtrail lookup-events` | Per-call audit | `PutObject`, `AccessDenied`, `CopyCommand` |

## CloudWatch metrics for Firehose (namespace: AWS/Firehose)

| Metric | Per destination | Meaning |
|---|---|---|
| `IncomingBytes` / `IncomingRecords` | All | Source is feeding records |
| `DeliveryToS3.Success` | S3 / Extended S3 | % of PutObject success |
| `DeliveryToS3.DataFreshnessSec` | S3 / Extended S3 | Lag: oldest undelivered record age |
| `DeliveryToS3.Bytes` / `Records` | S3 / Extended S3 | Volume delivered |
| `DeliveryToOpenSearch.Success` | OpenSearch | % of POST success |
| `DeliveryToOpenSearch.Records` | OpenSearch | Records indexed |
| `DeliveryToRedshift.Success` | Redshift | % of COPY success |
| `DeliveryToRedshift.Records` | Redshift | Rows committed |
| `DeliveryToSnowflake.Success` | Snowflake | % of COPY success |
| `DeliveryToHttpEndpoint.Success` | HTTP endpoint | % of POST success |
| `DeliveryToSplunk.Success` | Splunk | % of HEC POST success |
| `LambdaInvocation.DroppedRecords` | Lambda transform | Records dropped to S3 backup |
| `LambdaInvocation.ProcessedRecords` | Lambda transform | Records processed |
| `ThrottledRecords` | Source | Records throttled at PutRecord |
| `WriteThroughputBytes` | Source | Ingest throughput |

**Always verify the metric matching the configured destination.**
A common misdiagnosis is checking `DeliveryToS3.Success` when the
destination is OpenSearch - the metric stays at 100% because no
S3 delivery is expected (S3 is only backup in that case).

## Delivery-stream status values

| Status | Meaning | Action |
|---|---|---|
| `CREATING` | Provisioning in progress | Wait 1-3 minutes |
| `ACTIVE` | Config accepted, running | Status does NOT mean records are delivered - check metrics |
| `CREATING_FAILED` | Creation rejected | Review the IAM role / KMS / bucket config |
| `DELETING` | Teardown in progress | Wait for `DELETED` |
| `UPDATING` | `update-destination` in progress | Wait for `ACTIVE`; concurrent updates conflict |

## Lambda transform protocol (Firehose contract)

Firehose invokes the Lambda with a batch of records. The Lambda
MUST return a response in this exact shape:

```json
{
  "records": [
    {
      "recordId": "<same-as-input>",
      "result": "Ok | Dropped | ProcessingFailed",
      "data": "<base64-encoded-output-record-with-newline>"
    }
  ]
}
```

**Response caps:**
- Total response payload: 6 MB. Exceeding drops the whole batch
  to S3 backup.
- Per-record `data`: must be base64-encoded; the decoded length
  counts toward the 6 MB cap.
- `recordId` MUST match the input; mismatches produce
  `InvalidOutputFormat`.

**Result values:**
- `Ok` - record is delivered to the destination.
- `Dropped` - record is intentionally skipped (not an error).
- `ProcessingFailed` - record is routed to S3 error backup.

## Data format conversion reference

Firehose can convert JSON input to Parquet or ORC before delivering
to S3. The conversion uses a Glue Data Catalog table schema.

| Config block | Setting | Effect |
|---|---|---|
| `DataFormatConversionConfiguration.Enabled` | `true` | Conversion on |
| `InputFormatConfiguration.Deserializer` | `OpenXJsonSerDe` (most common) | Parses input JSON |
| `OutputFormatConfiguration.Format` | `Parquet` or `Orc` | Writer format |
| `SchemaConfiguration.DatabaseName` / `TableName` | Glue catalog refs | Source of schema |
| `SchemaConfiguration.RoleARN` | Glue-readable role | Firehose assumes to read schema |

**Common SerDe mismatches:**
- Input is CSV but deserializer is `OpenXJsonSerDe` - conversion
  rejects all records.
- Glue columns are `CamelCase` but JSON keys are `snake_case` -
  Parquet has nulls (or 0-byte objects if all columns null).
- `timestamp` column but input format is ISO-8601 while SerDe
  expects `yyyy-MM-dd HH:mm:ss.SSSSSS`.
- Nested object as string-encoded JSON but Glue type is `struct` -
  conversion writes the raw string, not the parsed object.

## OpenSearch circuit breaker

When Firehose receives 429 from OpenSearch, it engages a circuit
breaker:

| Phase | Default | Behavior |
|---|---|---|
| Writes succeed | - | Normal delivery |
| 429 burst | < 5 min | Backoff and retry; `DeliveryToOpenSearch.Success` dips |
| Sustained 429 | >= 5 min | Circuit breaker opens; delivery paused |
| Recovery | Sliding window of sustained success | Breaker closes; delivery resumes |

**Recovery requires sustained success.** A single good request is
not enough. Scale the OpenSearch cluster before the breaker will
close.

## Redshift COPY pipeline

Firehose to Redshift uses a three-step pipeline:

1. Firehose writes records to a staging S3 bucket (S3Backup).
2. Firehose connects to Redshift via JDBC and runs `COPY`.
3. Redshift loads from the staging bucket using the **cluster's**
   IAM role (NOT Firehose's role).

**Most Redshift failures are step 3.** The cluster role must have
`s3:GetObject` on the staging bucket. Firehose's role handles step
1; the cluster role handles step 3. A common misdiagnosis is
checking only the Firehose role.

**`stl_load_errors` is the source of truth for COPY failures:**

```sql
SELECT query, filename, line_number, colname, type, err_reason, raw_field_value
FROM stl_load_errors
WHERE start_time > dateadd(hour, -1, getdate())
ORDER BY start_time DESC LIMIT 20;
```

## Snowflake destination pipeline

Firehose to Snowflake uses:

1. Firehose writes records to a Firehose-managed staging S3 bucket.
2. Firehose calls Snowflake via the integration, which COPYs from
   the staging bucket into the target table.
3. Snowflake uses a storage integration (AWS resources) and a
   notification integration (SQS) to detect new files.

**Key Firehose config:**
- `AccountName` - Snowflake account identifier
- `UserRole` - Snowflake role
- `Database` / `Schema` / `Table`
- `SnowflakeRoleConfiguration.SnowflakeRole` - AWS role assumed
  by Snowflake
- `DataLoadingOption` - `JSON_MAPPING` or `VARIANT_COLUMN_MAPPING`
- `PrivateKeySource` - Secrets Manager secret with the key pair

**Common failures:**
- PrivateLink VPC endpoint unreachable (network routing).
- Snowflake integration not granted (`GRANT USAGE ON INTEGRATION`).
- Key-pair auth invalid (rotated in Snowflake but not in Secrets
  Manager).
- `CustomSql` rejected by Snowflake (compilation error).

## HTTP endpoint destination contract

Firehose sends records as JSON to the configured HTTP endpoint.
The endpoint MUST:

1. Accept POST to the configured URL.
2. Return HTTP 200 with the Firehose response JSON.
3. Handle the `X-Amz-Firehose-Protocol-Version` header.
4. Handle the `X-Amz-Firehose-Request-Id` header (idempotency).
5. Respond within the configured timeout (default 30 sec).

**Response shape from the endpoint:**

```json
{
  "requestId": "<same-as-header>",
  "timestamp": <unix-millis>
}
```

Non-200 responses trigger Firehose retry with exponential backoff.
After the configured max retries, records go to S3 error backup.

## Splunk HEC destination contract

Firehose sends events to the Splunk HEC (HTTP Event Collector)
endpoint. Key config:

| Config | Use |
|---|---|
| `HECEndpoint` / `HECEndpointType` | URL and type (Raw or Event) |
| `HECToken` (Secrets Manager) | Auth token |
| `HECAcknowledgmentTimeoutInSeconds` | Wait for HEC ack |
| `RetryDurationInSeconds` | Total retry window |
| `S3BackupMode` | `FailedEventsOnly` or `AllEvents` |

**HEC ack is required.** Without ack, Firehose cannot confirm
delivery and retries indefinitely until the retry window exhausts.
Verify Splunk `inputs.conf` has `ack = 1` on the HEC token.

## Diagnostic flowchart (high-level)

```
START: Firehose delivery problem reported
|
+- describe-delivery-stream returns ACTIVE?
|  +- No -> wait for CREATING; or fix CREATING_FAILED
|  +- Yes -> Continue (status is NOT delivery confirmation)
|
+- CloudWatch logging enabled?
|  +- No -> Enable before debugging further (Layer 5)
|  +- Yes -> Continue
|
+- Per-destination Success metric < 100%?
|  +- No -> Not a delivery failure; check DataFreshness (lag)
|  +- Yes -> Continue
|
+- Destination type?
|  +- s3 -> Step 2 (bucket / KMS / IAM)
|  +- lambda (only transform) -> Step 3
|  +- extended-s3 -> Step 2 + Step 3 + Step 5
|  +- opensearch -> Step 6
|  +- redshift -> Step 7
|  +- snowflake / http-endpoint / splunk -> Step 8
|
+- Symptom category?
|  +- DeliveryToS3Fails -> Step 2
|  +- LambdaFails -> Step 3
|  +- DeliveryLag -> Step 4
|  +- FormatConversionFails -> Step 5
|  +- OpenSearchFails -> Step 6
|  +- RedshiftFails -> Step 7
|  +- LatestDestinationFails -> Step 8
```

## CloudTrail events for Firehose diagnosis

| EventName | What it tells you |
|---|---|
| `PutRecord` / `PutRecordBatch` | Source-side writes (look for `ThrottlingException`) |
| `PutObject` (S3) | Firehose writing to S3 (look for `AccessDenied`) |
| `GenerateDataKey` (KMS) | Firehose asking for envelope key (look for `AccessDenied`) |
| `InvokeFunction` (Lambda) | Firehose invoking transform (look for errors / throttles) |
| `CopyCommand` (Redshift, via Redshift logs) | Redshift-side COPY (look in `stl_load_errors`) |
| `UpdateDeliveryStream` / `UpdateDestination` | Config change (look for `VersionId does not match`) |

```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=PutObject \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --query 'Events[*].[EventTime,Username,ResourceName]' --output table
```

## The 5-layer Firehose health check (detailed)

Before any destination-specific diagnosis, run the 5-layer check.
A failing layer invalidates all downstream diagnosis and is the
root cause of most "delivery fails" tickets:

1. **Source layer** - `IncomingBytes` / `IncomingRecords` > 0;
   for Kinesis-stream source, the source stream is `ACTIVE` with
   open shards.

2. **Transform layer** - if Lambda is configured, `Lambda.Errors`
   = 0 and `LambdaInvocation.DroppedRecords` = 0. Verify
   `lambda get-policy` grants Firehose invoke.

3. **Convert layer** - if format conversion is enabled, output
   objects are non-zero bytes (`s3api head-object ContentLength > 0`)
   and Athena can query them (schema match).

4. **Deliver layer** - per-destination `Success` metric >= 1.0;
   for OpenSearch, `describe-domain-health` is not RED; for
   Redshift, the cluster is `available`.

5. **Observability layer** - CloudWatch logging is `Enabled: true`
   on the destination; log groups exist for Firehose and Lambda.

If all five layers pass, the issue is configuration-specific
(buffering hints, SerDe, destination auth). Move to Steps 2-8.

If any layer fails, fix the layer first. Most "delivery fails"
tickets close when logging, IAM, KMS, or destination reachability
is restored.

## Step 8: Diagnose latest destinations (Snowflake / HTTP / Splunk) (moved from SKILL.md)

**Symptom:** Firehose to Snowflake / HTTP endpoint / Splunk returns
errors; `DeliveryTo*.Success` drops.

```bash
aws firehose describe-delivery-stream --delivery-stream-name <stream-name> \
  --query 'DeliveryStreamDescription.Destinations[0].[SnowflakeDestinationDescription,HttpEndpointDestinationDescription,SplunkDestinationDescription]' --output table
aws logs filter-log-events --log-group-name /aws/kinesisfirehose/<stream-name> \
  --filter-pattern "ERROR" --output table
```

#### Snowflake destination

| Cause | Diagnostic signal | Fix |
|---|---|---|
| PrivateLink VPC endpoint unreachable | Firehose log: `Connection timed out` to Snowflake VPCe | Verify the `PrivateLinkVPCEId`; ensure Firehose VPC can route to it |
| Snowflake integration not granted | Snowflake `SHOW INTEGRATIONS` shows the Firehose integration as not granted to the user / role | `GRANT USAGE ON INTEGRATION <name> TO ROLE <role>;` in Snowflake |
| Snowflake user / role mismatch | `AccountName` / `UserRole` in Firehose config does not match Snowflake | Update `update-destination --snowflake-destination-configuration` |
| Key-pair auth invalid | Snowflake log: `JWT token invalid` | Rotate the key pair; update Secrets Manager |
| Staging bucket (Snowflake) deleted | Firehose log: `Access Denied` on internal staging | Recreate the staging bucket (Firehose-managed) |
| `CustomSql` rejected by Snowflake | Firehose log: `SQL compilation error` | Fix the `CustomSql` MERGE / COPY statement |

#### HTTP endpoint destination

| Cause | Diagnostic signal | Fix |
|---|---|---|
| Endpoint returns non-200 | Firehose log: `Endpoint returned 500` / `401` / `403` | Fix the endpoint; verify auth header |
| Endpoint timeout | Firehose log: `Request timed out after X ms` | Raise the `EndpointConfiguration.AccessKey` and endpoint timeout; or scale the endpoint |
| Endpoint URL unreachable | Firehose log: `Connection refused` / DNS resolution failed | If endpoint is private, put Firehose in a VPC with route to it |
| Access key mismatch | Firehose sends wrong access key; endpoint returns 401 | Update `AccessKey` in `update-destination` |
| Buffer / retry exhaustion | Firehose log: `Max retries exhausted` | Raise retries; investigate endpoint health |
| Malformed request | Firehose log: `400 Bad Request` | Match the endpoint's expected schema (the Firehose HTTP record format) |

#### Splunk destination

| Cause | Diagnostic signal | Fix |
|---|---|---|
| HEC token invalid / expired | Firehose log: `403 Forbidden` from Splunk | Rotate the token; update Secrets Manager |
| Secrets Manager access denied | Firehose log: `AccessDenied` on `secretsmanager:GetSecretValue` | Add `secretsmanager:GetSecretValue` on the secret to the Firehose role |
| HEC endpoint unreachable | Firehose log: `Connection refused` | Verify Splunk HEC URL; if Splunk is private, put Firehose in a VPC |
| Splunk indexer queue full | Firehose log: `503 Service Unavailable` | Scale Splunk indexers; raise HEC `maxThreads` |
| HEC ACK disabled | Splunk `inputs.conf` has `ack = 0`; Firehose retries never confirm | Enable HEC ack on the Splunk side |
| SSL / TLS mismatch | Firehose log: `SSL handshake failed` | Verify Splunk certificate chain; or set `S3BackupMode` for retry |

**VERDICT:** ROOT_CAUSE_FOUND when Firehose log + destination
check identifies a specific cause; NEED_MORE_INFO when the
endpoint accepts but reports no data (sample the payload from
S3 backup).

## Appendix A - Symptom-to-cause map (quick reference) (moved from SKILL.md)

| Symptom | Most common root cause | Verify via |
|---|---|---|
| DeliveryToS3Fails - bucket deleted | `head-bucket` 404 | `s3api head-bucket` |
| DeliveryToS3Fails - bucket region mismatch | `get-bucket-location` different region | `s3api get-bucket-location` |
| DeliveryToS3Fails - KMS denied | CloudTrail `kms:GenerateDataKey` AccessDenied | `kms get-key-policy` |
| DeliveryToS3Fails - bucket policy | Firehose role lacks `s3:PutObject` | `simulate-principal-policy` |
| LambdaFails - timeout | Lambda log "Task timed out"; Duration ~ Timeout | CloudWatch Lambda metrics + logs |
| LambdaFails - exception | Lambda `Errors > 0`; stack trace in logs | `filter-log-events "ERROR"` |
| LambdaFails - 6 MB cap | S3 backup gets full batches; "response payload exceeds 6 MB" | Firehose logs |
| LambdaFails - resource policy | Firehose cannot invoke Lambda | `lambda get-policy` |
| DeliveryLag - buffering | `BufferingHints` 128MB / 900s on low-traffic stream | `describe-delivery-stream` |
| DeliveryLag - Lambda slow | Lambda Duration > buffer flush interval | Lambda Insights |
| DeliveryLag - OpenSearch 429 | Circuit breaker engaged; `429` count | Firehose logs + OpenSearch metrics |
| DeliveryLag - KMS throttling | KMS `ThrottledRequests > 0` | KMS metrics |
| FormatConversionFails - non-JSON | Firehose log "Input record is not valid JSON" | Firehose logs |
| FormatConversionFails - schema mismatch | Glue columns do not match JSON keys | `glue get-table` |
| FormatConversionFails - 0 bytes | `head-object ContentLength: 0` | `s3api head-object` |
| OpenSearchFails - auth | OpenSearch access policy lacks Firehose role | OpenSearch access policy |
| OpenSearchFails - 429 | OpenSearch throttling; circuit breaker | Firehose logs |
| OpenSearchFails - cluster red | `describe-domain-health` Red | OpenSearch API |
| RedshiftFails - COPY | `stl_load_errors` shows column / format | Redshift SQL |
| RedshiftFails - staging IAM | Cluster role lacks `s3:GetObject` | `iam simulate-principal-policy` |
| Snowflake - PrivateLink | Firehose log "Connection timed out" | Firehose logs + Snowflake `SHOW INTEGRATIONS` |
| Snowflake - integration not granted | `GRANT USAGE ON INTEGRATION` missing | Snowflake SQL |
| HTTP - non-200 | Firehose log "Endpoint returned 500/401/403" | Firehose logs |
| HTTP - timeout | Firehose log "Request timed out" | Firehose logs + endpoint metrics |
| Splunk - HEC token | `403 Forbidden` from Splunk; Secrets Manager access denied | Firehose logs + Splunk indexer metrics |
| Splunk - indexer queue | `503 Service Unavailable`; HEC `maxThreads` exhausted | Splunk metrics |

