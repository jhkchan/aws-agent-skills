---
name: s3-performance-optimizer
description: 'Optimises Amazon S3 performance across eleven dimensions: prefix distribution for partition allocation (auto-scale post-2018/2023), S3 Transfer Acceleration for cross-region uploads, multipart upload parallelism for large objects (>100 MB), byte-range fetches for partial reads, S3 Select for query pushdown (CSV/JSON/Parquet), S3 inventory for audit, CloudWatch request metrics (429 Slow Down, 503 throttling, FirstByteLatency), S3 Batch Operations for bulk processing, HTTP/2 connection reuse, pre-signed URL expiry tuning, S3 Object Lambda for on-demand transformation, S3 Express One Zone for single-digit-ms latency, multipart copy for large-object relocation, and content-encoding for transfer reduction. Distinguishes latency-bound from throughput-bound from request-rate-bound workloads. Emits OPTIMIZED or FURTHER_OPTIMIZATION_AVAILABLE per workload.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline classification works from pasted S3 access patterns, CloudWatch S3 metrics, and Storage Lens excerpts. Live- account optimisation uses aws s3api list-buckets / get-bucket-location / get-bucket-accelerate-configuration, aws s3control get-storage-lens-configuration, aws cloudwatch get-metric-statistics on AWS/S3 (FirstByteLatency, TotalRequestLatency, 4xxErrors, 5xxErrors), aws s3 ls / head-object /...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '3'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Storage
  task_type: optimize
  skill_class: capability
  lifecycle_status: active
  verdict_shape: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
  when_to_use: Optimising an S3-backed workload for latency, throughput, or request-rate — including prefix distribution for high-request-rate buckets, multipart upload for large PUTs, byte-range GETs for partial reads, S3 Select to push filtering into S3, S3 Express One Zone for single-digit-ms latency, Transfer Acceleration for cross-region uploads, HTTP/2 connection reuse, pre-signed URL expiry sizing, S3 Object Lambda for on-demand transformation, S3 Batch Operations for bulk processing, multipart copy for large object relocation, or content-encoding for transfer reduction.
  when_not_to_use: Cost-only optimisation of storage class / lifecycle (use s3-storage-class-optimizer, s3-lifecycle-optimizer, or s3-intelligent-tiering-optimizer), bucket policy / Block Public Access audits (use s3-public-access-auditor or s3-bucket-policy- deployer), access pattern troubleshooting (use s3-access- troubleshooter), replication setup (use s3-replication-operator), or Glacier restore workflows (use s3-glacier-restore-operator).
  activation_triggers: S3 performance, S3 latency, S3 throughput, S3 Slow Down 429, S3 503 throttling, S3 multipart upload, S3 Transfer Acceleration, S3 byte-range, S3 Select, S3 Express One Zone, S3 prefix distribution, S3 Object Lambda, S3 Batch Operations, S3 pre-signed URL, optimize S3 performance
  invocation_schema: 'Input: either (a) a workload description (bucket, prefix, object size profile, request rate, client geography, latency target) optionally paired with CloudWatch S3 metrics and Storage Lens excerpts, OR (b) a BucketName plus workload context for live-account optimisation. Output: a deterministic TARGET / VERDICT / REASON / LAYER / EVIDENCE / REMEDIATION block where VERDICT is in {OPTIMIZED, FURTHER_OPTIMIZATION_AVAILABLE} and LAYER is in {PREFIX_DISTRIBUTION, MULTIPART_UPLOAD, BYTE_RANGE_FETCH, S3_SELECT, TRANSFER_ACCELERATION, EXPRESS_ONE_ZONE, HTTP2_CONNECTION, PRESIGNED_URL, OBJECT_LAMBDA, BATCH_OPERATIONS, MULTIPART_COPY, CONTENT_ENCODING, ALREADY_OPTIMIZED, UNKNOWN}.'
  invocation_example: '# Minimal valid input (offline classification):

    Symptom: "S3 bucket receiving 8,000 PUT/sec; CloudWatch shows

    occasional 503 errors; p99 FirstByteLatency 250 ms."

    Bucket: prod-telemetry-ingest

    Region: us-east-1

    Workload: write-heavy ingest

    RequestRate: 8,000 PUT/sec

    AvgObjectSize: 12 KB

    ClientGeography: us-east-1 EC2

    TargetLatency: <50 ms p99

    '
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Amazon S3, S3 performance, multipart upload, Transfer Acceleration, byte-range fetch, S3 Select, S3 Express One Zone, prefix distribution, partition allocation, S3 Object Lambda, S3 Batch Operations, HTTP/2, 429 Slow Down, 503 throttling, pre-signed URL
  tags: s3, storage, performance-optimization, latency, throughput
---

# S3 Performance Optimizer

## Quick start

- **Workload -> first optimisation layer:** high PUT rate + small
  objects + 503/429 -> PREFIX_DISTRIBUTION; large objects (>100 MB) +
  slow PUT -> MULTIPART_UPLOAD; partial reads of large objects ->
  BYTE_RANGE_FETCH; full-scan CSV/JSON/Parquet -> S3_SELECT;
  cross-region uploads -> TRANSFER_ACCELERATION; single-digit-ms
  latency target -> EXPRESS_ONE_ZONE; repeated GETs of same object ->
  HTTP2_CONNECTION; clients report 403 -> PRESIGNED_URL.
- **Always measure before optimising.** CloudWatch S3 request metrics
  (`FirstByteLatency`, `TotalRequestLatency`, `4xxErrors`, `5xxErrors`)
  + Storage Lens identify whether the bottleneck is latency, throughput,
  or request rate. Optimising the wrong dimension is the #1 waste.
- **Latency-bound vs throughput-bound vs request-rate-bound are three
  different problems.** Latency-bound -> Express One Zone or connection
  reuse. Throughput-bound -> multipart + Transfer Acceleration.
  Request-rate-bound -> prefix distribution. NOT interchangeable.
- **Multipart upload is the single highest-impact change for large
  objects.** A 1 GB single PUT saturates one TCP stream; multipart with
  10 parallel parts at 100 MB each uses 10 streams and finishes ~10x
  faster.
- **S3 auto-scales partitions per-prefix since 2018, and removed the
  3,500/5,500 RPS cap in July 2023 for most workloads.** Operators who
  still shard prefixes "for performance" usually do unnecessary work.
  Only request rates >~10,000 RPS per prefix benefit from sharding.

## Mindset

S3 performance is the alignment between the workload's access pattern
and the S3 feature set. S3 is not slow; the wrong API choice is slow.
A 1 GB GET takes ~80 seconds over one TCP stream and ~8 seconds over 10
byte-range fetches. A 100 GB dataset scan via `select-object-content`
takes ~30 seconds; the same scan via client-side reads takes hours.
Senior S3 engineers start with the access pattern (read shape, write
shape, object size profile, client geography), pick the API/feature
that matches, and only then tune metrics.

## Philosophy

Moved to [references/advanced-patterns.md](references/advanced-patterns.md#philosophy-four-behaviours-of-a-senior-s3-engineer) — multipart above 100 MB, byte-range partial reads, Express One Zone trade-off, pre-signed expiry trade-off.
Load that reference on demand before executing this section.

## Quick reference — workload triage table

| Symptom / metric signal | Most likely layer | First probe |
|---|---|---|
| 429 Slow Down or 503 throttling | PREFIX_DISTRIBUTION | CloudWatch `4xxErrors`, `5xxErrors` |
| Large PUT > 100 MB slow | MULTIPART_UPLOAD | Client-side timing; current upload method |
| Only head/tail of large object read | BYTE_RANGE_FETCH | Access pattern: which byte offset? |
| CSV/JSON/Parquet full-scan slow | S3_SELECT | `select-object-content` prototype |
| Cross-region uploads slow | TRANSFER_ACCELERATION | Bucket accelerate config; client geography |
| p99 latency > 50 ms target | EXPRESS_ONE_ZONE | Latency target + bucket AZ requirements |
| Repeated GETs of same object | HTTP2_CONNECTION | SDK HTTP version; connection pool size |
| 403 from previously working URL | PRESIGNED_URL | URL expiry vs current timestamp |
| On-demand transformation needed | OBJECT_LAMBDA | Access pattern needs filtering/redaction? |
| Bulk object processing | BATCH_OPERATIONS | Operation type (copy/replace-tag/restore/invoke) |
| Large-object relocation slow | MULTIPART_COPY | `copy-object` vs `s3 cp --recursive` |
| Bandwidth-bound on textual payloads | CONTENT_ENCODING | `Content-Encoding` header; object size |

## Pre-flight: workload state and gather-info gate

Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#pre-flight-workload-state-and-gather-info-gate-commands) — bucket/feature discovery, CloudWatch request metrics, Storage Lens, S3 Select probe, byte-range probe.
Load that reference on demand before executing this section.

If CloudWatch request metrics are NOT enabled, recommend
`put-bucket-metrics-configuration` before diagnosing; without metrics,
optimisation is guesswork.

If the input is malformed (no BucketName, no workload description, no
access pattern context), emit:

Moved to [references/worked-examples.md](references/worked-examples.md#worked-example-malformed-input-verdict-unknown) — the full FURTHER_OPTIMIZATION_AVAILABLE / LAYER: UNKNOWN block for missing context.
Load that reference on demand before executing this section.

## Process — Optimisation decision tree

The tree is workload-driven. Each layer ends with either an actionable
optimisation (a probe that confirms the layer is the bottleneck) or a
pass. **Never emit OPTIMIZED without verifying the workload's stated
target is met by current config.**

### Step 0: Non-obvious behaviours that change diagnosis

Moved to [references/advanced-patterns.md](references/advanced-patterns.md#step-0-non-obvious-behaviours-that-change-diagnosis) — partition auto-scaling, SDK multipart defaults, Range semantics, SSE-KMS Select, Express ARN syntax, TA distance, presign caps, Object Lambda cost, Batch pricing, HTTP/2 opt-in.
Load that reference on demand before executing this section.

### Step 1: Workload entry — pick the optimisation branch

| Workload shape | Branch |
|---|---|
| PUT-heavy, > 5,000 RPS per prefix, 503/429 errors | Step 2 — Prefix distribution |
| Large PUT > 100 MB slow | Step 3 — Multipart upload |
| Read only head/tail of large objects | Step 4 — Byte-range fetch |
| Full-scan CSV/JSON/Parquet slow | Step 5 — S3 Select |
| Cross-region uploads | Step 6 — Transfer Acceleration |
| Latency target < 10 ms single-digit | Step 7 — Express One Zone |
| Repeated GETs of same object | Step 8 — HTTP/2 connection |
| 403 on previously working URL | Step 9 — Pre-signed URL |
| On-demand transform / redaction | Step 10 — Object Lambda |
| Bulk processing | Step 11 — Batch Operations |
| Large-object copy / relocation | Step 12 — Multipart copy |
| Textual payloads bandwidth-bound | Step 13 — Content encoding |
| Workload meets target | Step 14 — Already optimised |

### Step 2: PREFIX_DISTRIBUTION — high request rate per prefix

Symptom: 429 Slow Down or 503 throttling on a single prefix.
CloudWatch `4xxErrors` and `5xxErrors` show sustained spikes.

```bash
aws cloudwatch get-metric-statistics --namespace AWS/S3 \
  --metric-name 4xxErrors \
  --dimensions Name=BucketName,Value=<bucket> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 60 --statistics Sum --output json
```

S3 auto-scales partitions per prefix; the July 2023 announcement
removed the 3,500/5,500 per-second cap for almost all workloads. Only
rates above ~10,000 per second on a single prefix need sharding. If
your workload is below that threshold and still seeing 503/429, look
elsewhere (hot key, retry storm).

**Verdict:** If rate per prefix exceeds 10,000 sustained and no
sharding is in place, FURTHER_OPTIMIZATION_AVAILABLE with
`LAYER: PREFIX_DISTRIBUTION`. Fix: add a hash prefix to the key.

### Step 3: MULTIPART_UPLOAD — large PUT optimisation

Symptom: PUT of large objects (> 100 MB) is slow or stalls.

Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#step-3-probe-current-upload-method-and-multipart-timing) — head-object size check and single vs multipart upload timing.
Load that reference on demand before executing this section.

Moved to [references/s3-performance-reference.md](references/s3-performance-reference.md#step-3-multipart-upload-part-sizing-table-moved-from-skillmd) — part size and parallelism by object size band.
Load that reference on demand before executing this section.

**Verdict:** If the current upload uses single PUT above 100 MB,
FURTHER_OPTIMIZATION_AVAILABLE with `LAYER: MULTIPART_UPLOAD`.

### Step 4: BYTE_RANGE_FETCH — partial reads

Symptom: Client reads only the first/last few KB of a large object
(headers, trailers, manifests).

```bash
curl -sv "https://<bucket>.s3.<region>.amazonaws.com/<key>" \
  -o /dev/null -w 'full: %{time_total}s %{size_download}b\n'

curl -sv -H 'Range: bytes=0-1023' \
  "https://<bucket>.s3.<region>.amazonaws.com/<key>" \
  -o /dev/null -w 'range: %{time_total}s %{size_download}b\n'
```

**Verdict:** If the client reads only the first/last KB,
FURTHER_OPTIMIZATION_AVAILABLE with `LAYER: BYTE_RANGE_FETCH`. Fix:
switch to `Range: bytes=0-N` (head) or `Range: bytes=-N` (tail).

### Step 5: S3_SELECT — query pushdown

Symptom: Full-scan CSV/JSON/Parquet where only some records are needed.

```bash
aws s3api select-object-content \
  --bucket <bucket> --key <key> \
  --expression "SELECT s.id, s.amount FROM s3object s WHERE s.amount > 1000" \
  --expression-type SQL \
  --input-serialization '{"CSV": {"FileHeaderInfo": "USE"},
                          "CompressionType": "GZIP"}' \
  --output-serialization '{"CSV": {}}' /dev/stdout
```

S3 Select typically reduces bytes transferred 5-50x depending on
selectivity.

Moved to [references/s3-performance-reference.md](references/s3-performance-reference.md#step-5-s3-select-format-support-table-moved-from-skillmd) — CSV/JSON/Parquet supported; ORC/Avro/Excel/PDF not.
Load that reference on demand before executing this section.

**Verdict:** If the workload is a full-scan of CSV/JSON/Parquet and S3
Select is not in use, FURTHER_OPTIMIZATION_AVAILABLE with
`LAYER: S3_SELECT`.

### Step 6: TRANSFER_ACCELERATION — cross-region uploads

Symptom: Cross-region uploads are slow. Bucket region is far from the
client.

```bash
aws s3api get-bucket-accelerate-configuration --bucket <bucket> --output json

time aws s3 cp <file> s3://<bucket>/<key>
# After enabling Transfer Acceleration
time aws s3 cp <file> s3://<bucket>/<key> \
  --endpoint-url http://s3-accelerate.amazonaws.com
```

Transfer Acceleration routes through the nearest CloudFront edge POP
and uses Amazon's backbone to the bucket region. For same-region
traffic it adds latency; only enable for cross-region workloads.

**Verdict:** Cross-region workload with Transfer Acceleration off ->
FURTHER_OPTIMIZATION_AVAILABLE with `LAYER: TRANSFER_ACCELERATION`.

### Step 7: EXPRESS_ONE_ZONE — single-digit-ms latency

Symptom: Target latency is single-digit ms (ML model serving, hot
cache, transactional read).

```bash
aws s3api list-buckets --output json | \
  jq '.Buckets[] | select(.Name | contains("--xaz-"))'
```

S3 Express One Zone uses directory buckets, provides ~10x lower latency
(single-digit ms p99), costs more per GB and per request, and is
single-AZ. Always flag the availability trade-off before recommending.

Moved to [references/s3-performance-reference.md](references/s3-performance-reference.md#step-7-express-one-zone-workload-fit-table-moved-from-skillmd) — backup/ML/personalisation/hot-cache fit vs standard S3.
Load that reference on demand before executing this section.

**Verdict:** Latency target < 10 ms and bucket on standard S3 ->
FURTHER_OPTIMIZATION_AVAILABLE with `LAYER: EXPRESS_ONE_ZONE` (with
explicit availability caveat).

### Step 8: HTTP2_CONNECTION — connection reuse

Symptom: Repeated GETs of the same object; high TLS handshake overhead.

```bash
curl -sv --http2 "https://<bucket>.s3.<region>.amazonaws.com/<key>" \
  -o /dev/null 2>&1 | grep -E 'HTTP/'
```

Most AWS SDKs default to HTTP/1.1; opt in to HTTP/2 in the SDK config.
HTTP/2 connection reuse amortises the TLS handshake, reducing
per-request latency 30-100 ms on small objects.

**Verdict:** Repeated GETs using HTTP/1.1 (new TLS per request) ->
FURTHER_OPTIMIZATION_AVAILABLE with `LAYER: HTTP2_CONNECTION`.

### Step 9: PRESIGNED_URL — expiry and refresh pattern

Symptom: Clients report 403 from a previously working URL.

```bash
aws s3 presign s3://<bucket>/<key> --expires-in 3600
```

Moved to [references/s3-performance-reference.md](references/s3-performance-reference.md#step-9-pre-signed-url-expiry-table-moved-from-skillmd) — expiry choice per use case incl. IAM-user vs STS caps.
Load that reference on demand before executing this section.

**Verdict:** Clients re-request URLs frequently because of short expiry
-> FURTHER_OPTIMIZATION_AVAILABLE with `LAYER: PRESIGNED_URL`.

### Step 10: OBJECT_LAMBDA — on-demand transform

Symptom: Multiple clients need the same object in different forms
(filtered, redacted, format-converted).

```bash
aws s3control list-access-points --account-id <id> --output json
aws s3control get-access-point --account-id <id> --name <ap> --output json
```

S3 Object Lambda Access Point sits in front of a standard access point;
a Lambda function transforms the GET response on the fly. It does NOT
cache the transformed output — repeated reads incur repeated Lambda
invocations. Add a CDN or client-side cache for hot objects.

**Verdict:** Multiple clients re-fetching to redact/filter client-side
-> FURTHER_OPTIMIZATION_AVAILABLE with `LAYER: OBJECT_LAMBDA`.

### Step 11: BATCH_OPERATIONS — bulk processing

Symptom: Need to copy, replace-tag, restore, or invoke-Lambda on
millions of objects.

```bash
aws s3control create-job \
  --account-id <id> \
  --operation '{"S3Replicate": {}}' \
  --manifest-location <manifest-s3-uri> \
  --report <report-config> \
  --role-arn <role> \
  --client-request-token <token>
```

S3 Batch Operations uses a manifest (typically from S3 Inventory). Avoid
listing millions of objects via `list-objects-v2`.

Moved to [references/s3-performance-reference.md](references/s3-performance-reference.md#step-11-batch-operations-billing-table-moved-from-skillmd) — per-object billing for copy/tags/restore/Lambda invoke.
Load that reference on demand before executing this section.

**Verdict:** Bulk operation scripted client-side via `list-objects-v2`
+ loop -> FURTHER_OPTIMIZATION_AVAILABLE with
`LAYER: BATCH_OPERATIONS`.

### Step 12: MULTIPART_COPY — large-object relocation

Symptom: Need to copy objects > 5 GB within or across buckets.

`copy-object` is limited to 5 GB. For larger objects, use `s3 cp`
(which auto-uses multipart copy) or the SDK multipart copy API.

```bash
time aws s3 cp s3://<src-bucket>/<key> s3://<dst-bucket>/<key> \
  --expected-size <size> \
  --multipart-chunksize 500MB \
  --max-concurrent-requests 10
```

**Verdict:** Workload uses `copy-object` on objects > 5 GB or serially
copies many large objects -> FURTHER_OPTIMIZATION_AVAILABLE with
`LAYER: MULTIPART_COPY`.

### Step 13: CONTENT_ENCODING — transfer-size reduction

Symptom: Bandwidth-bound on textual payloads (JSON, CSV, logs, HTML).

```bash
aws s3api head-object --bucket <bucket> --key <key> --output json | \
  jq '{ContentLength, ContentEncoding, ContentType}'
```

Pre-compressing textual objects (`Content-Encoding: gzip` or `br`)
reduces S3 GET time proportionally. S3 does not compress on read;
clients must accept the encoding. CloudFront decompresses on the fly
when configured.

Moved to [references/s3-performance-reference.md](references/s3-performance-reference.md#step-13-content-encoding-compression-ratios-moved-from-skillmd) — gzip ratios for textual payloads; no gain for already-compressed.
Load that reference on demand before executing this section.

**Verdict:** Textual payloads stored uncompressed, clients support
gzip/br -> FURTHER_OPTIMIZATION_AVAILABLE with
`LAYER: CONTENT_ENCODING`.

### Step 14: ALREADY_OPTIMIZED — workload meets target

If the workload's stated target (latency, throughput, request rate) is
met by current configuration, emit OPTIMIZED with
`LAYER: ALREADY_OPTIMIZED`. Do NOT recommend additional changes.

## Output format

```text
TARGET: <bucket-name> (region: <region>, workload: <workload-shape>)
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences naming the layer and the optimisation opportunity>
LAYER: <PREFIX_DISTRIBUTION | MULTIPART_UPLOAD | BYTE_RANGE_FETCH |
        S3_SELECT | TRANSFER_ACCELERATION | EXPRESS_ONE_ZONE |
        HTTP2_CONNECTION | PRESIGNED_URL | OBJECT_LAMBDA |
        BATCH_OPERATIONS | MULTIPART_COPY | CONTENT_ENCODING |
        ALREADY_OPTIMIZED | UNKNOWN>
EVIDENCE:
  - <workload description — read/write shape, object size, request rate>
  - <current configuration — bucket features, client config>
  - <probe result — measurement that quantifies the gap>
  - <estimated delta — projected latency / throughput improvement>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the change>
CONFIRM: Before executing any state-changing CLI, emit and await
  operator approval: "CONFIRM: About to <action> on <bucket> in
  <region>. Proceed? (yes/no)"
```

## Anti-Patterns — NEVER

- NEVER recommend prefix sharding for workloads below 10,000 RPS per
  prefix. S3 auto-scales partitions; manual sharding below the cap is
  unnecessary complexity.

- NEVER use `copy-object` for objects > 5 GB. The API caps at 5 GB; use
  multipart copy (`s3 cp` or SDK multipart copy API).

- NEVER enable Transfer Acceleration for same-region traffic. The
  CloudFront edge hop adds latency for in-region clients.

- NEVER migrate to S3 Express One Zone without flagging the single-AZ
  availability trade-off. Express One Zone does not replicate across
  AZs; pair with cross-region replication for critical data.

- NEVER default pre-signed URL expiry to 1 hour without considering the
  workload. Long uploads need 12+ hours; high-security sharing needs
  minutes. The expiry is a latency-vs-security trade-off.

- NEVER rely on S3 Object Lambda without a downstream cache. Each GET
  incurs a Lambda invocation; hot objects amplified across clients
  create runaway Lambda costs.

- NEVER use `list-objects-v2` to enumerate millions of objects for a
  batch job. Use S3 Inventory (daily/weekly manifest) as the batch job
  input.

- NEVER recommend HTTP/2 without verifying SDK support. Many SDKs
  default to HTTP/1.1; opt-in requires SDK configuration.

- NEVER compress already-compressed formats (PNG, JPEG, MP4, gzip
  archives). Re-compression wastes CPU and may increase size slightly.

- NEVER assume S3 Select supports all formats. It covers CSV, JSON,
  and Parquet only; ORC, Avro, and binary formats require Athena.

- NEVER declare OPTIMIZED without comparing the workload's target
  metric against the current metric. "Looks fine" is not OPTIMIZED; a
  measured match is.

## Pre-flight safety checks

- **MANDATORY CONFIRMATION GATE.** Before
  `put-bucket-accelerate-configuration`,
  `put-bucket-metrics-configuration`, `create-job`, `put-object` with
  `Content-Encoding`, or any bucket-level configuration change, emit
  and await operator approval.

- **Read-only first.** Probes (`get-bucket-location`,
  `get-bucket-accelerate-configuration`, `get-metric-statistics`,
  `head-object`, `select-object-content`, `list-objects-v2`) are
  read-only. `select-object-content` is billed per request; use small
  LIMIT clauses for probes.

- **Enabling Transfer Acceleration** is a bucket-level toggle; existing
  clients using the standard endpoint continue to work. The accelerate
  endpoint is opt-in via SDK configuration.

- **Enabling CloudWatch request metrics** adds per-request metric
  cost (~$0.01 per 1,000 metrics in 2026). The EntireBucket filter is
  cheapest; per-prefix filters multiply the cost.

- **S3 Express One Zone migration** requires creating a new directory
  bucket and copying objects in; existing bucket names cannot be
  converted in place.

- **Pre-signed URL regeneration** after changing IAM credentials
  invalidates all previously signed URLs. Coordinate credential
  rotation with active URL issuance.

## Configuration dependency graph

Moved to [references/advanced-patterns.md](references/advanced-patterns.md#configuration-dependency-graph-ascii-flow) — classification -> bucket features -> client features -> verdict flow diagram.
Load that reference on demand before executing this section.

## Expert heuristic

Moved to [references/advanced-patterns.md](references/advanced-patterns.md#expert-heuristic) — multipart parallelism default, byte-range partial GETs, Express One Zone single-digit-ms trade-off.
Load that reference on demand before executing this section.


## References (load on demand)

- [references/s3-performance-reference.md](references/s3-performance-reference.md) — sizing/format/expiry/metric matrices backing each optimisation layer, plus AWS Health event categories.
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — pre-flight workload-state commands and per-layer probe commands.
- [references/worked-examples.md](references/worked-examples.md) — full output-block examples incl. the malformed-input (UNKNOWN) verdict.
- [references/advanced-patterns.md](references/advanced-patterns.md) — philosophy deep dive, Step 0 non-obvious behaviours, configuration dependency graph, expert heuristics.
## Domain

AWS CloudOps / S3 Object Storage Performance, Multipart Upload, S3
Express One Zone, S3 Select, Transfer Acceleration, and Batch Operations.

## AWS documentation

- **S3 performance guidelines** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/optimizing-performance.html
- **Multipart upload** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/mpuoverview.html
- **Byte-range fetches** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/GettingObjectsUsingAPIs.html
- **S3 Select** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/selecting-content-from-objects.html
- **S3 Transfer Acceleration** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/transfer-acceleration.html
- **S3 Express One Zone** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-express-one-zone.html
- **S3 Object Lambda** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/transforming-objects.html
- **S3 Batch Operations** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/batch-ops.html
- **S3 CloudWatch request metrics** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/cloudwatch-monitoring.html
