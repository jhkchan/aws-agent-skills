# Advanced Patterns — Kinesis Data Firehose Troubleshooter

Step-0 expert-knowledge deep dives and recent AWS features moved verbatim from SKILL.md for progressive disclosure. Load on demand.

## Step 0: Expert knowledge - non-obvious Firehose behaviors (moved from SKILL.md)

- **`describe-delivery-stream` returns the live config including all destination sub-fields.** The console collapses sub-config; the API returns `S3DestinationUpdate`, `ExtendedS3DestinationUpdate`, `RedshiftDestinationUpdate`, `ElasticsearchDestinationUpdate`, `AmazonopensearchserviceDestinationUpdate`, `SnowflakeDestinationUpdate`, `HttpEndpointDestinationUpdate`, `SplunkDestinationUpdate` as separate blocks.
- **Firehose never silently drops records without leaving a trace.** Failed records go to S3 backup (if enabled) or surface as `DeliveryTo*.Success < 100`. Always enable CloudWatch logging + S3 backup before debugging.
- **Lambda transforms are invoked with buffered batches, not single records.** Buffering hints control cadence: 1-3 MB or 60-900 sec. A Lambda slower than the buffer cadence produces backpressure, not single-record failures.
- **Lambda transform output is capped at 6 MB per invocation.** Records that grow during enrichment (JSON expansion, join with reference data) can exceed this cap. The entire batch is dropped to S3 backup if the response exceeds 6 MB.
- **Data format conversion uses Glue Data Catalog schema.** If the Glue table schema does not match the input JSON, conversion produces 0-byte Parquet/ORC objects that look successful on `DeliveryToS3.Success` but are unreadable by Athena or other engines.
- **Parquet/ORC conversion requires the input to be valid JSON.** CSV or raw text input to a conversion-enabled stream is rejected; the records go to S3 error backup. The `InputFormatConfiguration.Deserializer` must be a `OpenXJsonSerDe` or `HiveJsonSerDe`.
- **OpenSearch destination uses a circuit breaker.** If Firehose receives 429 (Too Many Requests) from OpenSearch for sustained periods, it engages a circuit breaker that pauses delivery for a sliding window. Default circuit breaker: `5 minutes` of sustained failures; recovery requires sustained success.
- **OpenSearch auth uses either IAM signing or basic auth (master user).** Mixed-mode failures are common: the Firehose role has IAM signing but the domain uses fine-grained access control with a master user - Firehose needs both.
- **Redshift destination uses a staging S3 bucket + COPY command.** The COPY runs as the Redshift cluster's IAM role, not Firehose's. The cluster role must have `s3:GetObject` on the staging bucket. Most Redshift delivery failures are staging-bucket IAM or COPY column mismatches.
- **KMS key policy must grant the Firehose service principal.** `delivery.stream.amazonaws.com` needs `kms:GenerateDataKey` and `kms:Decrypt` on the key. A key policy that allows only the customer account root will deny Firehose even though the key is "enabled."
- **S3 bucket region must match the Firehose region.** Cross-region buckets are not supported by Firehose (with the explicit exception of S3 backup with a separate bucket). A bucket-region mismatch produces `AccessDenied` on `PutObject`.
- **Firehose to Snowflake uses a private Snowflake endpoint, not the public account URL.** Verify the `SnowflakeDestinationConfiguration.PrivateLinkVPCEId` and the Snowflake integration grant. Most Snowflake destination failures are private-link unreachable or integration not granted.
- **HTTP endpoint delivery retries with exponential backoff.** After the configured max retries, records go to S3 error backup. The endpoint must return HTTP 200 within the configured timeout.
- **Splunk destination uses HEC (HTTP Event Collector) tokens.** The token is stored in Secrets Manager; the Firehose role must have `secretsmanager:GetSecretValue`. An expired or rotated token produces 403 from Splunk.
- **Buffering hints affect both latency and cost.** Larger buffers (e.g., 128 MB / 900 sec) reduce S3 PUT costs but increase `DataFreshness`. Smaller buffers reduce latency but multiply S3 requests. Always tune for the workload, not the defaults.
- **Firehose does not support in-place config edits to a destination.** Use `update-destination` with the current version ID; concurrent updates conflict with `VersionId does not match`.
- **Dynamic partitioning (2024) uses Lambda-derived partition keys.** A Lambda that returns no partition key causes records to route to the default prefix only. Verify the `DynamicPartitioningConfiguration` and the Lambda metadata returned.

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **Firehose to Snowflake (GA 2024):** Native destination supporting Snowflake PrivateLink VPC endpoints and key-pair auth via Secrets Manager. Verify `SnowflakeDestinationConfiguration.PrivateLinkVPCEId` and the Snowflake integration grant. Most failures are private-link unreachable or integration not granted.
- **HTTP endpoint delivery (expanded 2024-2025):** Generic HTTP endpoint destination now supports custom headers, retry policy, and per-record success/failure reporting. Verify the endpoint returns 200 within the configured timeout; retries back up to S3 error backup after exhaustion.
- **Splunk delivery enhancements (2024-2025):** HEC ack support, buffered retry, and Secrets Manager token rotation. Verify HEC `ack = 1` on the Splunk side; Firehose relies on ack to confirm writes.
- **Dynamic partitioning (2024-2025):** Lambda-derived partition keys enable S3 partition-on-the-fly. A Lambda that returns no partition key routes all records to the default prefix; verify `DynamicPartitioningConfiguration.RetryDuration`.
- **Parquet / ORC conversion via Glue (2024-2026):** Improved SerDe support including `OpenXJsonSerDe` case-insensitivity, `TimestampFormats`, and nested struct handling. Verify the Glue table schema matches the producer JSON exactly.
- **Firehose within a VPC (2024-2025):** Firehose can now deliver to private destinations (OpenSearch in VPC, private HTTP endpoints, Snowflake PrivateLink) without a NAT gateway. Verify the Firehose VPC config and the destination security group allows Firehose subnets.
- **Multi-AZ delivery + enhanced CloudWatch metrics (2025-2026):** Multi-AZ delivery for high-throughput streams; per-destination `DataFreshness`, `ThrottledRecords`, and per-Lambda-invocation duration are now available. Verify the dashboard uses the correct per-destination metric.

