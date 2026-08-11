# Destinations and Buffering — Firehose Delivery Stream Deployer

Deep reference on Firehose destination configuration (S3, OpenSearch,
HTTP endpoint, Redshift), buffering hints trade-offs (latency vs cost,
format-specific tuning), S3 prefix patterns (Hive-style partitioning
for Athena), backup configuration, and retry settings. Loaded on
demand by the skill — kept out of the main SKILL.md body so the
provisioning procedure stays scannable.

## S3 destination

The most common and flexible destination. Firehose delivers records to
S3 objects with configurable prefix, buffering, compression, and
encryption.

### S3 prefix patterns

Firehose supports dynamic expressions in S3 prefixes using `!{...}`
syntax:

```text
Time-based expressions:
  !{timestamp:yyyy}    → 4-digit year
  !{timestamp:MM}      → 2-digit month
  !{timestamp:dd}      → 2-digit day
  !{timestamp:HH}      → 2-digit hour

Error expressions (error prefix only):
  !{firehose:error-output-type}   → error type (e.g., DataFormatConversion)

Partition key expressions (with Lambda metadata extraction):
  !{partitionKeyFromQuery:mykey}  → partition key from Lambda metadata
```

**Hive-style partitioning (for Athena/Glue):**

```text
Prefix: data/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/

Resulting S3 keys:
  data/year=2026/month=01/day=15/2026-01-15-10-30-00-abc.parquet
  data/year=2026/month=01/day=15/2026-01-15-10-45-00-def.parquet
```

**Flat prefix (BAD for analytics — scans all files):**

```text
Prefix: data/

Resulting S3 keys:
  data/2026-01-15-10-30-00-abc.parquet
  data/2026-01-15-10-45-00-def.parquet
```

**Error prefix:**

```text
Error prefix: errors/!{firehose:error-output-type}/year=!{timestamp:yyyy}/month=!{timestamp:MM}/

Resulting error keys:
  errors/DataFormatConversion/year=2026/month=01/2026-01-15-10-30-00-abc
  errors/LambdaFunctionError/year=2026/month=01/2026-01-15-10-45-00-def
```

### S3 compression formats

| Format | When to use | Notes |
|---|---|---|
| UNCOMPRESSED | With Parquet/ORC format conversion | Parquet has built-in compression |
| GZIP | For JSON/CSV delivered to S3 | Good compression, slow decompression |
| SNAPPY | For JSON/CSV delivered to S3 | Fast decompression, less compression |
| ZIP | Rarely used | ZIP archive format |

**NEVER use GZIP with Parquet format conversion.** Parquet has built-in
compression (Snappy by default). Setting CompressionFormat to GZIP with
format conversion causes double-compression, which wastes CPU and may
cause issues.

## OpenSearch destination

Firehose writes to an OpenSearch index using the bulk API. Configure
domain ARN, index name, index rotation, and retry behavior.

### Index rotation

| Rotation period | Index name pattern | When to use |
|---|---|---|
| NoRotation | `<index-name>` | Small volumes, manual index management |
| OneHour | `<index-name>-yyyy-MM-dd-HH` | High volume, time-based queries |
| OneDay | `<index-name>-yyyy-MM-dd` | Most common — daily indices |
| OneWeek | `<index-name>-yyyy-'W'ww` | Weekly reporting |
| OneMonth | `<index-name>-yyyy-MM` | Low volume, monthly reporting |

### Retry behavior

Failed writes to OpenSearch are retried for up to `DurationInSeconds`.
After the retry duration expires, failed documents go to the S3 backup
bucket (if `S3BackupMode` is `FailedDocumentsOnly`).

```text
Delivery attempt → OpenSearch
  ├── Success → document indexed
  └── Failure → retry (up to DurationInSeconds)
        ├── Retry succeeds → document indexed
        └── Retry exhausted → S3 backup bucket (FailedDocumentsOnly)
```

### OpenSearch buffering

For OpenSearch, use smaller buffer sizes (5 MB, 60-300s) to reduce
indexing latency. Large buffers cause bulk indexing spikes that can
overload the OpenSearch cluster.

## HTTP endpoint destination

Firehose POSTs batches of records to an HTTP endpoint. The endpoint
must return HTTP 200 within 30 seconds.

### Splunk HEC configuration

```bash
EndpointConfiguration:
  Url: https://splunk.example.com:8088/services/collector
  AccessKey: <HEC-token>
```

Firehose sends records in Splunk HEC JSON format. Each POST contains a
batch of records.

### Endpoint ACK contract

- HTTP 200: success (Firehose marks records as delivered).
- HTTP non-200 or timeout: failure (Firehose retries up to
  `DurationInSeconds`, then backs up to S3).

### Content encoding

Firehose supports GZIP content encoding for HTTP endpoint requests,
reducing bandwidth. Enable if the endpoint supports GZIP.

## Redshift destination

Firehose stages data to S3, then issues a COPY command to load the
data into a Redshift table.

### COPY flow

```text
Records → Firehose buffers → S3 staging file → COPY command → Redshift table
```

The COPY command loads the staged S3 file into the specified table.
Configure `CopyOptions` based on data format:

```bash
CopyCommand:
  DataTableName: events
  CopyOptions: "FORMAT AS JSON 'auto' IAM_ROLE 'arn:aws:iam::...'"
```

### Redshift COPY options

| Format | CopyOptions |
|---|---|
| JSON | `FORMAT AS JSON 'auto'` |
| CSV | `DELIMITER ',' SKIPHEADER 1` |
| Parquet | `FORMAT AS PARQUET` |

### Authentication

Firehose connects to Redshift using username/password (stored in
Secrets Manager or inline) or IAM role authentication.

## Buffering hints deep dive

### How buffering works

Firehose buffers incoming records and delivers them to the destination
when EITHER condition is met:
- `SizeInMBs`: buffered data reaches the specified size.
- `IntervalInSeconds`: the specified time elapses since the last
  delivery.

Whichever triggers first causes a flush.

### Format-specific recommendations

| Destination / Format | SizeInMBs | IntervalInSeconds | Rationale |
|---|---|---|---|
| S3 (JSON, no conversion) | 5-15 | 300 | Balance object count vs latency |
| S3 (Parquet) | 64-128 | 300-900 | Larger row groups = better compression + Athena |
| S3 (ORC) | 64-128 | 300-900 | Same rationale as Parquet |
| OpenSearch | 5 | 60-300 | Reduce bulk indexing overhead |
| HTTP endpoint | 5 | 60 | Low latency for SIEM |
| Redshift | 64-128 | 300-900 | Fewer, larger COPY operations |

### Parquet row group optimization

Parquet organizes data into row groups. Larger row groups compress
better and are more efficient for columnar reads. The optimal row group
size is 128 MB-1 GB.

```text
Buffering 5MB (default):
  → Many tiny Parquet files (each <5MB)
  → Each file has 1 small row group
  → Athena must open hundreds of files → slow, expensive

Buffering 128MB:
  → Fewer, larger Parquet files (~128MB)
  → Each file has 1 large row group
  → Athena opens 10x fewer files → fast, cheap
```

### Cost impact

S3 charges per PUT request ($0.005 per 1,000 requests). With 5 MB
buffering and 1 GB/hour throughput:
- 5 MB buffering: 200 PUTs/hour = ~146,000 PUTs/month
- 128 MB buffering: ~8 PUTs/hour = ~5,800 PUTs/month

Larger buffering reduces S3 PUT costs by 25x for the same throughput.

## Backup configuration

| Destination | Backup mode | What it backs up |
|---|---|---|
| S3 | SourceRecord | All source records before transformation |
| OpenSearch | FailedDocumentsOnly | Records that failed OpenSearch indexing |
| HTTP endpoint | FailedDataOnly | Records that failed HTTP delivery |
| Redshift | FailedDataOnly | Records that failed Redshift COPY |

**Best practice:** always enable backup in production. Use a separate
S3 bucket from the main delivery bucket to simplify reprocessing.

## Terraform example

```hcl
# Firehose delivery stream with S3 Parquet destination
resource "aws_kinesis_firehose_delivery_stream" "events" {
  name        = "events-to-s3-parquet"
  destination = "extended_s3"

  extended_s3_configuration {
    role_arn   = aws_iam_role.firehose.arn
    bucket_arn = aws_s3_bucket.data_lake.arn
    prefix     = "data/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/"
    error_output_prefix = "errors/!{firehose:error-output-type}/year=!{timestamp:yyyy}/month=!{timestamp:MM}/"

    buffering_size     = 128
    buffering_interval = 300

    data_format_conversion_configuration {
      enabled = true

      input_format_configuration {
        deserializer {
          open_x_json_ser_de {}
        }
      }

      output_format_configuration {
        serializer {
          parquet_ser_de {}
        }
      }

      schema_configuration {
        database_name = aws_glue_catalog_table.events.database_name
        table_name    = aws_glue_catalog_table.events.name
        role_arn      = aws_iam_role.firehose.arn
      }
    }

    processing_configuration {
      enabled = true

      processor {
        type = "Lambda"

        parameter {
          parameter_name  = "LambdaArn"
          parameter_value = aws_lambda_function.transform.arn
        }
        parameter {
          parameter_name  = "BufferSizeInMBs"
          parameter_value = "3"
        }
      }
    }
  }
}
```
