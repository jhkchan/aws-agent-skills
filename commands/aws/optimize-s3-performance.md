---
description: Optimise Amazon S3 performance across eleven dimensions — prefix distribution, multipart upload, byte-range fetch, S3 Select, Transfer Acceleration, Express One Zone, HTTP/2, pre-signed URL, Object Lambda, Batch Operations, multipart copy, content encoding — and emit OPTIMIZED or FURTHER_OPTIMIZATION_AVAILABLE per workload with estimated latency/throughput delta.
nl_triggers:
  - "S3 performance"
  - "S3 latency"
  - "S3 throughput"
  - "S3 Slow Down 429"
  - "S3 503 throttling"
  - "S3 multipart upload"
  - "S3 Transfer Acceleration"
  - "S3 byte-range"
  - "S3 Select"
  - "S3 Express One Zone"
  - "S3 prefix distribution"
  - "S3 partition"
  - "S3 Object Lambda"
  - "S3 Batch Operations"
  - "S3 pre-signed URL"
  - "optimize S3 performance"
  - "speed up S3 upload"
  - "S3 GET slow"
routes_to: s3-performance-optimizer
---

# /aws:optimize-s3-performance

Activate the `s3-performance-optimizer` skill and optimise an S3-backed
workload across eleven performance dimensions.

## What it does

Reads a workload description (bucket, prefix, object size profile,
request rate, client geography, target latency/throughput) plus
CloudWatch S3 request metrics and Storage Lens excerpts, then walks
the workload-driven optimisation tree to identify the highest-impact
change:

1. **Pre-flight** — bucket location, accelerate configuration,
   versioning, CloudWatch request metrics (must be enabled), Storage
   Lens configuration, S3 Select probe, byte-range fetch probe.
2. **Workload classification** — latency-bound (use Express One Zone
   or connection reuse), throughput-bound (use multipart + Transfer
   Acceleration), request-rate-bound (use prefix distribution),
   partial-read (use byte-range), filter-pushdown (use S3 Select), or
   bulk-processing (use Batch Operations).
3. **Layer-specific probes** —
   - Prefix distribution: CloudWatch `4xxErrors`, `5xxErrors`;
     Storage Lens `RequestRate`; verify per-prefix request rate vs
     ~10,000 RPS threshold.
   - Multipart upload: current upload method (`put-object` vs `cp`);
     client-side timing; part-size matrix.
   - Byte-range fetch: full GET vs `Range` GET timing; access pattern
     (head/tail vs full-body).
   - S3 Select: `select-object-content` prototype with small LIMIT;
     format support (CSV/JSON/Parquet); compression.
   - Transfer Acceleration: bucket accelerate config; client
     geography; same-region vs cross-region.
   - Express One Zone: latency target < 10 ms; bucket AZ requirements;
     availability trade-off.
   - HTTP/2: `curl --http2` probe; SDK HTTP version config.
   - Pre-signed URL: expiry vs current timestamp; IAM-user vs STS
     credential cap.
   - Object Lambda: transform-on-read need; downstream cache presence.
   - Batch Operations: manifest source (S3 Inventory vs
     `list-objects-v2`); per-object cost.
   - Multipart copy: object size > 5 GB; `copy-object` vs `s3 cp`.
   - Content encoding: textual vs already-compressed; client
     `Accept-Encoding` support.
4. **Verdict** — OPTIMIZED (target met) or FURTHER_OPTIMIZATION_AVAILABLE
   (named layer + specific fix + estimated delta).

Emits a deterministic optimisation block per target:

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
  - <workload description>
  - <current configuration>
  - <probe result>
  - <estimated delta>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the change>
```

## When to invoke

Paste a workload description and ask any of:

- "S3 upload is slow"
- "S3 GET latency is too high"
- "S3 returns 503 SlowDown"
- "speed up S3 multipart upload"
- "S3 Express One Zone vs Standard"
- "S3 Select vs client-side filter"
- "byte-range fetch for log trailer"
- "S3 prefix sharding for high request rate"
- "S3 Transfer Acceleration for cross-region"
- "S3 Batch Operations for bulk copy"
- "S3 pre-signed URL expiry tuning"
- "S3 Object Lambda for on-demand redaction"

A bare bucket name + any performance verb ("S3 slow", "uploads
failing", "throttled") also routes here via the orchestrator.

## Inputs

- Workload description: PUT-heavy / GET-heavy / mixed, object size
  profile, request rate, client geography (region, EC2 / on-prem /
  mobile), target latency or throughput.
- Bucket configuration: BucketName, region, Transfer Acceleration
  status, versioning, storage class distribution, CloudWatch request
  metrics on/off, S3 Inventory on/off, Object Lambda / Batch
  Operations setup.
- For live-account optimisation: CloudWatch S3 request metrics
  (`FirstByteLatency`, `TotalRequestLatency`, `4xxErrors`, `5xxErrors`,
  `BytesDownloaded`, `BytesUploaded`), Storage Lens excerpts, S3 Select
  probe results, byte-range fetch timing.

## Outputs

- One optimisation block per target bucket / workload.
- Layer-specific LAYER value from the enumerated set.
- Evidence section with the workload shape, current config, the probe
  result that quantifies the gap, and the estimated latency /
  throughput delta after the fix.
- Specific remediation: prefix sharding, multipart upload sizing,
  byte-range fetch rewrite, S3 Select rewrite, Transfer Acceleration
  toggle, Express One Zone migration (with availability caveat), HTTP/2
  SDK config, pre-signed URL expiry tune, Object Lambda access point
  setup, Batch Operations job, multipart copy, or content-encoding
  pre-compression.

## Related

- `/aws:audit-s3-bucket-policy` for access posture audits (not
  performance).
- `/aws:optimize-s3-storage-class` for cost-only storage class /
  lifecycle tuning.
- `/aws:troubleshoot-s3-access` for AccessDenied / 403 issues that may
  look like performance problems.
- `/aws:optimize-cloudfront-cache` for CDN-side caching that reduces
  S3 GET load.
