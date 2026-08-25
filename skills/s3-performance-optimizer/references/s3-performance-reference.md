# S3 Performance Reference Guide

Supplementary reference for the S3 Performance Optimizer skill. Loaded
on-demand when an optimisation needs multipart size guidance, S3 Select
format support, Express One Zone naming, pre-signed URL expiry caps, or
CloudWatch metric definitions.

## Multipart upload sizing matrix

| Object size | Recommended part size | Recommended parallelism | Notes |
|---|---|---|---|
| < 100 MB | n/a (single PUT) | 1 | Multipart overhead exceeds benefit |
| 100 MB - 500 MB | 25 MB | 5 | 4-20 parts; small enough to retry |
| 500 MB - 5 GB | 100 MB | 10 | 5-50 parts |
| 5 GB - 50 GB | 500 MB | 10 | 10-100 parts |
| 50 GB - 500 GB | 1 GB | 10 | 50-500 parts |
| 500 GB - 5 TB (max) | 5 GB | 10 (cap; S3 limits 10,000 parts) | At the part-count cap |

S3 limits:
- Minimum part size (except last): 5 MB.
- Maximum part count per object: 10,000.
- Maximum object size: 5 TB.
- Maximum part size: 5 GB.

AWS CLI flags:
- `--expected-size <bytes>`: hint to the CLI for part sizing.
- `--multipart-chunksize <size>`: explicit part size.
- `--max-concurrent-requests <n>`: parallel parts (default 10).

## Byte-range fetch patterns

| Range header | Returns |
|---|---|
| `Range: bytes=0-1023` | First 1024 bytes (head) |
| `Range: bytes=-1024` | Last 1024 bytes (tail) |
| `Range: bytes=1024-` | From offset 1024 to end |
| `Range: bytes=0-1023,4096-5119` | Two ranges (counted as 2 GETs) |

S3 returns `HTTP 206 Partial Content` with a `Content-Range` header.

Common patterns:
- Tail reads (log trailer, file footer, index offset): `Range:
  bytes=-N`.
- Header reads (magic bytes, schema, manifest): `Range: bytes=0-N`.
- Parallel full read: 10 concurrent `Range` requests at offsets
  `[0, size/10, 2*size/10, ...]` — equivalent to multipart download.

## S3 Select format support

| Format | S3 Select | Compression | Notes |
|---|---|---|---|
| CSV / TSV | Yes | GZIP, BZIP2 | FileHeaderInfo: USE / IGNORE / NONE |
| JSON | Yes | GZIP | Lines (newline-delimited) or document mode |
| Parquet | Yes | (no extra; columnar) | Column pruning + predicate pushdown; SSE-KMS needs key context |
| ORC | No | — | Use Athena |
| Avro | No | — | Use Athena or Glue |
| Excel, PDF, Word | No | — | Use other tools |

S3 Select SQL syntax:
- `SELECT s.col1, s.col2 FROM s3object s WHERE s.col1 > 1000`
- `LIMIT` clause supported for sampling.
- Aggregate functions: `COUNT`, `SUM`, `AVG`, `MIN`, `MAX`.
- Cast functions: `CAST(s.col AS INTEGER)`.

Pricing (us-east-1, 2026): $0.002 per 1,000 SELECT requests + $0.0007
per GB scanned. Compared to a full GET ($0.0004 per 1,000 + full
egress), S3 Select wins on large objects with high selectivity.

## S3 Express One Zone naming and limits

Directory bucket name format:
`<base-name>--xaz-<az-id>--x-s3`

Example: `ml-models--xaz-use1-az2--x-s3`

| Property | Standard S3 | Express One Zone |
|---|---|---|
| Latency p99 | 10s-100s ms | single-digit ms |
| Availability SLA | 99.9% (multi-AZ) | 99.95% (single-AZ) |
| Durability | 11 nines (multi-AZ replication) | 11 nines within the AZ |
| Min object size charge | 128 KB | 128 KB |
| Per-GB price (us-east-1) | Standard tier | ~2-3x Standard |
| Per-request price | Standard | ~2x Standard |
| Multipart upload | Yes | Yes |
| Byte-range fetch | Yes | Yes |
| S3 Select | Yes | Yes |
| Versioning | Yes | No (in 2026) |
| Replication (CRR/SRR) | Yes | No (in 2026) |
| Bucket policies | Yes | Yes |

Workload fit:
- Strong fit: ML model serving, real-time personalisation, hot cache
  layer, transactional read/write, single-AZ-acceptable.
- Bad fit: backup / archival (cost), cross-region data lake (no CRR),
  regulatory multi-AZ workloads.

## Transfer Acceleration latency targets

| Source region to bucket region | Direct PUT p99 | Accelerated PUT p99 |
|---|---|---|
| Same region | 50-100 ms | 80-150 ms (worse — added edge hop) |
| Cross-continent (e.g., EU to US) | 200-500 ms | 80-150 ms |
| Asia-Pacific to US | 250-600 ms | 100-200 ms |
| Mobile / poor-quality last mile | Highly variable | Often 2-5x better |

Rule: enable Transfer Acceleration only when client-to-bucket distance
is significant. For same-region workloads, it adds latency.

## Pre-signed URL expiry caps

| Credential type | Maximum expiry | Default |
|---|---|---|
| IAM user (long-term access key) | 7 days (604,800 s) | 3,600 s (1 hour) |
| IAM role / STS-derived | 36 hours (129,600 s) | 3,600 s |
| SigV4 with custom signing proxy | Custom (no hard cap) | Custom |

After credential rotation, all pre-signed URLs issued by the old
credential become invalid immediately. Coordinate rotation windows.

## CloudWatch S3 request metric dimensions

| Dimension | Meaning |
|---|---|
| `BucketName` | Bucket name (always present) |
| `FilterId` | `EntireBucket` (default) or a configured metrics filter ID |

Per-filter metrics multiply the per-metric cost. Use `EntireBucket` for
cost-efficient monitoring; add per-prefix filters only when needed.

Key metrics for performance diagnosis:
- `FirstByteLatency` — TTFB (latency-bound workloads).
- `TotalRequestLatency` — end-to-end request time.
- `4xxErrors` — client-side errors (includes 429 SlowDown).
- `5xxErrors` — server-side errors (includes 503 throttling).
- `BytesDownloaded` / `BytesUploaded` — throughput.
- `PutRequests` / `GetRequests` / `ListRequests` / `HeadRequests` —
  request mix.
- `DeleteRequests` — useful for lifecycle tuning.

## S3 Batch Operations limits

| Property | Limit |
|---|---|
| Manifest format | CSV (S3 Inventory output) |
| Manifest source | S3 Inventory (daily/weekly) or custom CSV |
| Max objects per job | 10^9 |
| Concurrent jobs per account | 100,000 (default; adjustable) |
| Billed per object | ~$0.25 per million |
| Supported operations | Copy, Replace tags/ACL, Restore from Glacier, Invoke Lambda, Replicate, Object Lock retention |

S3 Inventory output:
- Daily or weekly manifest per bucket / prefix.
- CSV or ORC format.
- Lists object key, size, last-modified, storage class, encryption
  status, replication status, checksum.

Use the inventory manifest as the batch job input to avoid listing
millions of objects via `list-objects-v2`.

## HTTP/2 vs HTTP/1.1 on S3

| Property | HTTP/1.1 | HTTP/2 |
|---|---|---|
| Connections per client | Multiple (pool) | Single (multiplexed) |
| TLS handshake | Per connection | Once per connection |
| Per-request overhead on small objects | 30-100 ms (handshake amortised) | 5-30 ms (multiplexed) |
| SDK support | Default | Opt-in via SDK config |

S3 endpoints support HTTP/2 from 2018+. SDK opt-in:
- AWS CLI: `--cli-connect-timeout` and `--cli-read-timeout` affect
  HTTP/1.1; HTTP/2 requires an SDK-level config.
- boto3: not enabled by default; requires a custom HTTP adapter.
- AWS SDK for Java v2: `.httpConfiguration().httpProtocol(HTTP_2)`.
- AWS SDK for JavaScript v3: `requestHandler: new HttpHandler({ http2: true })`.

## Content-Encoding compression ratios

| Content-Type | gzip ratio | brotli ratio |
|---|---|---|
| JSON (verbose) | 6-10x | 7-12x |
| CSV | 5-8x | 6-9x |
| HTML | 5-8x | 6-10x |
| Logs (text) | 8-15x | 9-17x |
| XML | 6-9x | 7-11x |
| PNG / JPEG / MP4 / gzip archives | ~1x (re-compress wastes CPU) | ~1x |

S3 does not compress on read. Clients must accept the encoding
(`Accept-Encoding: gzip`); CloudFront decompresses on the fly when
configured with a response-cache policy that includes the
`Content-Encoding` header.

## AWS Health event categories that affect S3

| Category | Likely impact |
|---|---|
| `AWS_S3_SERVICE` | Region-wide S3 degradation |
| `AWS_S3_PERFORMANCE` | Elevated latency or throttling |
| `AWS_KMS_SERVICE` | SSE-KMS-encrypted objects fail to decrypt |

Always probe `aws health describe-events` for regional issues before
declaring a customer-side performance issue during a wide-impact
incident.

## Step 3: multipart upload part sizing table (moved from SKILL.md)

| Object size | Recommended part size | Recommended parallelism |
|---|---|---|
| 100 MB - 500 MB | 25 MB | 5 |
| 500 MB - 5 GB | 100 MB | 10 |
| 5 GB - 50 GB | 500 MB | 10 |
| 50 GB - 5 TB (max) | 1 GB | 10 (cap; S3 limits 10,000 parts) |

## Step 5: S3 Select format support table (moved from SKILL.md)

| Format | S3 Select supported | Notes |
|---|---|---|
| CSV / TSV | Yes | With or without header |
| JSON | Yes | Lines (newline-delimited) or document |
| Parquet | Yes | Column pruning + predicate pushdown |
| ORC, Avro | No | Use Athena / Glue |
| Excel, PDF | No | Use other tools |

## Step 7: Express One Zone workload fit table (moved from SKILL.md)

| Workload | Standard S3 | Express One Zone |
|---|---|---|
| Backup / archival | OK | No (cost) |
| ML training data | OK (large reads) | OK if latency-critical |
| Real-time personalisation | Marginal | Strong fit |
| Hot cache layer | Marginal | Strong fit (with replication elsewhere) |

## Step 9: pre-signed URL expiry table (moved from SKILL.md)

| Expiry | Use case |
|---|---|
| 60 seconds | High-security / per-request signing |
| 1 hour (default) | General |
| 12 hours | Long upload (multipart resume) |
| 7 days (max, IAM user) | Long-lived sharing |
| 36 hours (max, IAM role/STS) | Default for STS-derived credentials |

## Step 11: Batch Operations billing table (moved from SKILL.md)

| Operation | Billed as |
|---|---|
| Copy | Per object |
| Replace tags / ACL | Per object |
| Restore from Glacier | Per object + Glacier restore |
| Invoke Lambda | Per object + Lambda invocation |

## Step 13: content-encoding compression ratios (moved from SKILL.md)

| Content-Type | Typical gzip ratio |
|---|---|
| JSON / CSV / HTML | 5-10x |
| Logs (text) | 8-15x |
| Already-compressed (PNG, JPEG, MP4) | No gain |

