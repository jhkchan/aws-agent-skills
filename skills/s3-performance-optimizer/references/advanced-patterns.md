# Advanced Patterns — S3 Performance Optimizer

Deep-dive material moved from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Philosophy: four behaviours of a senior S3 engineer

Four behaviours separate a senior S3 engineer from a generalist:

- **Multipart upload is not optional above 100 MB.** A single PUT of a
  1 GB object uses one TCP stream and one TLS handshake; the throughput
  ceiling is the bandwidth-delay product of one stream. Multipart with
  10 parallel parts uses 10 streams and approaches link bandwidth.
- **Byte-range fetches turn one slow GET into many fast GETs.** Many
  workloads only need the first/last few KB (file trailers, headers,
  manifests). `Range: bytes=0-1023` returns in single-digit ms
  regardless of object size; a full GET of a 5 GB object returns in
  seconds.
- **S3 Express One Zone is a different storage class with different
  request semantics.** It is a directory bucket
  (`<bucket>--xaz-<az>--x-s3`) with single-digit-ms latency for both
  reads and writes, but it is single-AZ. Operators who enable it
  without flagging the availability trade-off risk data loss on an AZ
  failure.
- **Pre-signed URL expiry is a performance + security trade-off.**
  Short expiry forces re-signing (latency). Long expiry eliminates the
  round-trip but creates a window where a leaked URL is valid.

## Step 0: Non-obvious behaviours that change diagnosis

- **S3 auto-scales partitions per prefix since 2018, and removed the
  3,500 PUT / 5,500 GET per-second per-prefix cap in July 2023 for most
  workloads.** Operators who still pre-shard prefixes are usually doing
  unnecessary work. Only rates above ~10,000 per second on a single
  prefix benefit from sharding.

- **Multipart upload parts are parallel by default in the AWS SDK.**
  The CLI and SDK auto-select multipart above 8 MB; the part size is
  tunable. Operators who manually configure multipart often set the
  part count too low (default 10), leaving parallelism on the table.

- **Byte-range GET uses the same `Range` header as HTTP.** S3 supports
  `Range: bytes=START-END` and returns `206 Partial Content`. Multiple
  ranges in one request are supported but counted as multiple GETs.

- **S3 Select does NOT support encrypted Parquet with SSE-KMS until
  the SDK provides the key context.** Without it the request fails with
  AccessDenied.

- **S3 Express One Zone uses a different bucket ARN syntax.** Directory
  buckets are named `<bucket>--xaz-<az-id>--x-s3` and live in a single
  AZ. Existing application code that hardcodes the standard bucket ARN
  breaks when the bucket moves to Express One Zone.

- **Transfer Acceleration only helps when the client is far from the
  bucket region.** For same-region traffic it adds an S3 edge hop and
  can be slower than a direct PUT. Always measure with and without.

- **Pre-signed URL expiry caps at 7 days for IAM-user credentials and
  36 hours for IAM-role (STS) credentials.** Long-expiry URLs require
  IAM-user credentials or a custom signing proxy.

- **S3 Object Lambda transforms on read; it does not store the
  transformed object.** Each GET through the Object Lambda Access Point
  incurs the transform compute (Lambda) plus the S3 GET cost.

- **S3 Batch Operations are billed per-object-invocation (~$0.25 per
  million).** Use the manifest from S3 Inventory to avoid listing
  millions of objects.

- **HTTP/2 is supported on S3 endpoints but requires the SDK to opt
  in** (most default to HTTP/1.1). Confirm with `curl --http2`.

## Configuration dependency graph (ASCII flow)

```
Workload description (read shape, write shape, object size, request rate,
client geography, target latency / throughput)
    |
    v
+----------------------------------------------+
| Classification                               |
|   - Latency-bound? -> Step 7 (Express One Z) |
|   - Throughput-bound? -> Step 3 (Multipart)  |
|   - Request-rate-bound? -> Step 2 (Prefix)   |
|   - Partial read? -> Step 4 (Byte range)     |
|   - Filter pushdown? -> Step 5 (S3 Select)   |
+----------------------------------------------+
    |
    v
+----------------------------------------------+
| Bucket features (current state)              |
|   - Region, AZ topology                       |
|   - Transfer Acceleration on/off              |
|   - Storage class distribution                |
|   - CloudWatch request metrics on/off         |
|   - S3 Inventory configured                   |
+----------------------------------------------+
    |
    v
+----------------------------------------------+
| Client features                              |
|   - SDK HTTP version (1.1 vs 2)               |  Step 8
|   - Connection pool / keep-alive              |
|   - Multipart parallelism                     |  Step 3
|   - Pre-signed URL expiry                     |  Step 9
|   - Compression (gzip/br on/off)              |  Step 13
+----------------------------------------------+
    |
    v
+----------------------------------------------+
| Optimisation verdict                         |
|   - OPTIMIZED: target met                    |
|   - FURTHER_OPTIMIZATION_AVAILABLE: gap + fix|
+----------------------------------------------+
```

## Expert heuristic

The single highest-signal heuristic: **multipart upload parallelism with
10 parallel parts at 100 MB each is the right default for almost every
object > 100 MB.** S3 scales per TCP connection only up to the
bandwidth-delay product of one stream; multipart with parallel parts
opens multiple streams and approaches link bandwidth. A 1 GB single PUT
takes ~80 seconds on a 100 Mbps link; with 10 parallel parts it takes
~8 seconds. Second heuristic: **byte-range fetches turn a slow full GET
into a fast partial GET.** Many workloads only need the first/last few
KB. A `Range: bytes=0-1023` returns in single-digit ms regardless of
object size; a full GET of a 5 GB object returns in seconds. Third
heuristic: **S3 Express One Zone is the only S3 storage class that
delivers single-digit-ms p99 latency for both reads and writes** — but
it is single-AZ, so always pair it with cross-region replication for
non-recoverable data.

