# S3 Transfer Acceleration Operator — Advanced Patterns

Step-0 expert heuristics and recent AWS features, moved verbatim from SKILL.md for progressive disclosure.
Load when a plan hinges on non-obvious service behavior.

## Step 0: Expert heuristic — non-obvious S3 acceleration behaviors

These behaviors are easy to misjudge without operational experience.
Each changes a plan if ignored:

- **The accelerate endpoint is a different DNS name.** When
  acceleration is enabled, you MUST use
  `<bucket>.s3-accelerate.amazonaws.com` (or
  `<bucket>.s3-accelerate.dualstack.amazonaws.com` for IPv6).
  Using the standard endpoint (`<bucket>.s3.<region>.amazonaws.com`)
  bypasses acceleration entirely — you pay for the feature but get
  no benefit. The SDK auto-detects acceleration when configured with
  `use_accelerate_endpoint: true`.

- **Enabling acceleration does not change the standard endpoint.**
  The bucket remains accessible via the standard S3 endpoint after
  acceleration is enabled. Acceleration is an ADDITIONAL endpoint,
  not a replacement. Existing applications using the standard
  endpoint continue to work unchanged.

- **Directory buckets (S3 Express One Zone) do not support
  acceleration.** S3 Express One Zone (directory buckets with
  `--xaz-` suffix) have their own low-latency architecture and do
  not support Transfer Acceleration. `put-bucket-accelerate-
  configuration` returns an error for directory buckets.

- **Acceleration cost is per-GB data IN, not per-request.** You are
  charged for the data volume transferred through the accelerate
  endpoint, not the number of requests. A 1 GB file uploaded as 1
  part costs the same as a 1 GB file uploaded as 128 parts — the
  acceleration fee is for 1 GB either way. Request costs (PUT
  requests) are billed separately at standard S3 rates.

- **The speed comparison tool is non-destructive.** The S3 Transfer
  Acceleration speed comparison tool uploads and downloads small
  test files through both the accelerated and direct endpoints,
  measuring latency and throughput. It does not affect your data
  or bucket configuration. Always run it before enabling acceleration
  for production workloads.

- **Checksums protect against accelerated transfer corruption.**
  Accelerated uploads traverse the edge network and backbone. While
  TCP provides integrity per-hop, specifying a checksum
  (`x-amz-sdk-checksum-algorithm: CRC32C`) on the upload ensures
  end-to-end verification. S3 validates the checksum on the
  complete object and returns it in the response. For multipart
  uploads, each part has its own checksum; the complete-multipart-
  upload call aggregates them.

- **Disabling acceleration mid-multipart-upload causes failures.**
  If multipart uploads are in-flight via the accelerate endpoint and
  you disable acceleration, subsequent `upload-part` calls to the
  accelerate endpoint will fail. Always complete or abort in-flight
  multipart uploads before disabling acceleration.

- **Direct Connect and Transfer Acceleration serve different use
  cases.** Direct Connect is a dedicated network connection from
  your data center to AWS (fixed port cost + per-GB data transfer).
  Transfer Acceleration uses the public internet to reach the
  nearest edge, then the AWS backbone. Direct Connect is cheaper
  for sustained high-volume transfers from a fixed location
  (>50 TB/month). Transfer Acceleration is better for distributed
  uploaders (many locations uploading to one bucket) or one-time
  migrations.

- **Dual-stack (IPv6) accelerate endpoints are available.** Use
  `<bucket>.s3-accelerate.dualstack.amazonaws.com` for IPv6 support.
  This is transparent to the application — the endpoint resolves to
  both IPv4 and IPv6 addresses. Required for IPv6-only networks
  (some mobile carriers and enterprise networks).

- **Acceleration does not support Amazon S3 Object Lambda.** S3
  Object Lambda Access Points do not work with the accelerate
  endpoint. If your bucket has Object Lambda transformations, they
  are not applied to accelerated uploads.

- **KMS-encrypted buckets work with acceleration.** SSE-KMS
  encryption is transparent to Transfer Acceleration — the edge
  location receives the already-encrypted object and forwards it.
  No additional KMS configuration is needed. However, KMS API
  calls (GenerateDataKey) are NOT accelerated — they go directly
  to KMS in the bucket's region.

## Recent AWS features (2024-2026)

- **S3 Express One Zone (2024 GA):** Single-AZ, ultra-low-latency
  storage class with directory buckets. Does NOT support Transfer
  Acceleration. Designed for ML training data, analytics
  workloads, and local caching — not for long-distance transfers.

- **S3 checksums with multipart upload (2024-2025):** CRC32C
  checksum support for individual parts and aggregated object-level
  checksums on complete-multipart-upload. The `x-amz-checksum-crc32c`
  header is verified by S3 on upload completion. CRC32C is faster
  than CRC32 or SHA-256 for hardware-accelerated computation.

- **S3 multipart copy between accelerated buckets (2024-2025):**
  Server-side copy between S3 buckets using multipart upload
  (`create-multipart-upload` + `upload-part-copy`). When both
  buckets have acceleration enabled, the copy is routed through
  the edge network. Useful for cross-region data migration.

- **S3 Transfer Acceleration dual-stack IPv6 (2024):** The
  accelerate endpoint supports IPv6 via
  `<bucket>.s3-accelerate.dualstack.amazonaws.com`. Required for
  IPv6-only networks and some mobile carriers.

- **AWS Direct Connect + S3 integration (2024-2026):** Direct
  Connect now supports S3 VPC gateway endpoints over private VIFs.
  This provides a private, dedicated path to S3 without traversing
  the public internet. For sustained high-volume transfers from a
  fixed data center, Direct Connect is cheaper and more reliable
  than Transfer Acceleration.

- **S3 Batch Operations with acceleration (2025):** S3 Batch
  Operations now supports copy operations through the accelerate
  endpoint for cross-region batch transfers. Useful for large-scale
  data migration jobs.

- **CloudWatch S3 metrics enhancement (2025):** CloudWatch now
  provides per-endpoint S3 metrics (accelerate vs standard). The
  `BytesUploaded` metric can be filtered by endpoint type to
  monitor acceleration usage and cost.

