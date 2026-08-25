# S3 Version Cleanup Operator — Advanced Patterns

Step-0 non-obvious versioning behaviors and recent AWS features, moved verbatim from SKILL.md for progressive disclosure.

## Step 0: Expert knowledge — non-obvious S3 versioning behaviors

These behaviors are easy to misjudge without operational S3 experience.
Each changes a plan if ignored. See `references/lifecycle-rule-patterns.md`
for full lifecycle JSON anatomy and the
NoncurrentVersionExpiration-vs-NewerNoncurrentVersions heuristic. Summary:

- **Noncurrent versions bill at Standard rate by default** — they are
  NOT auto-tiered; version cleanup is the #1 S3 cost optimization.
- **`put-bucket-lifecycle-configuration` REPLACES, not merges** — the
  single most common lifecycle mistake. Always read-merge-write.
- **`NoncurrentVersionExpiration` deletes permanently** — no recovery,
  no Glacier archive. Use `NoncurrentVersionTransition` first for a
  softer path. Default is "no expiration" (indefinite billing).
- **`NewerNoncurrentVersions` keeps only N recent noncurrent versions**
  — pair with `NoncurrentVersionTransition` for full savings. Combine
  with `NoncurrentVersionExpiration` for defense in depth (caps count
  AND age).
- **`AbortIncompleteMultipartUpload` cleans orphaned uploads** —
  orphans bill at Standard rate indefinitely; 7-day abort window is
  standard.
- **`NoncurrentDays` counts from when the version BECAME noncurrent**,
  not from object creation.
- **Lifecycle rules apply asynchronously within 24 hours** of
  eligibility, not in real time.
- **Batch Operations for immediate cleanup** — ~$1.00/million objects;
  see `references/lifecycle-rule-patterns.md` for cost-comparison table.
- **Object Lock Compliance mode is irrevocable** — no one (including
  root) can delete in-retention versions. Governance mode allows bypass
  with `s3:BypassGovernanceRetention`.
- **Legal hold is per-object, not bucket-wide** — bulk cleanup must
  check each object or use a manifest-based Batch Operations job.
- **Versioning `Suspended` ≠ never enabled** — suspended buckets have
  pre-suspension versions (preserved) and null-version-id objects;
  re-enable versioning before cleanup.
- **Delete markers are themselves versions** — deleting a versioned
  object creates a delete marker but does NOT remove prior versions.
- **Storage Lens is the canonical impact estimator** — use
  `NoncurrentVersionCount` and `NoncurrentVersionStorageBytes`.
- **GIR vs Glacier Flexible Retrieval** — GIR (~$0.004/GB, ms latency)
  for quarterly access; Flexible (~$0.0036/GB, 1-5 min restore) for
  annual. Choose by access pattern, not just cost.
- **Bucket Key reduces KMS cost ~99%** — always recommend enabling on
  SSE-KMS buckets alongside lifecycle changes.
- **CRR/SRR preserves versions independently** — apply lifecycle rules
  to BOTH source and replica; cleaning source does NOT clean replica.
- **Intelligent-Tiering auto-archives noncurrent versions at 90 days**
  — alternative to manual rules for unknown access patterns.
- **`put-bucket-lifecycle-configuration` validates XML, not business
  logic** — does not warn about rule conflicts or impossible
  transitions; verify via `get-bucket-lifecycle-configuration` after PUT.
- **`Expiration` (current) ≠ `NoncurrentVersionExpiration`** —
  `Expiration` creates a delete marker on versioned buckets and does
  NOT remove old versions.

## Recent AWS features (2024-2026)

- **S3 Intelligent-Tiering Archive Access default (2024-2025):** New
  buckets with Intelligent-Tiering now default to moving noncurrent
  versions to Archive Access after 90 days automatically. Operators
  should verify whether Intelligent-Tiering is in use before adding
  manual lifecycle rules — duplicate rules can conflict.

- **S3 Glacier Instant Retrieval lifecycle rule GA (2024):**
  NoncurrentVersionTransition to GIR is fully supported as a lifecycle
  target. GIR provides ms-latency GETs at ~$0.004/GB-month — the
  recommended first transition for noncurrent versions.

- **S3 Batch Operations expanded operations (2024-2025):** Batch
  Operations now supports `S3DeleteObjectVersion` natively (previously
  required a custom Lambda). Cost remains ~$1.00 per million objects.

- **S3 Object Lock Governance mode enhancements (2024):** Governance
  mode now logs bypass attempts to CloudTrail by default. Operators
  should verify CloudTrail S3 data event logging is enabled for audit.

- **S3 Storage Lens dashboard improvements (2024-2025):** Storage Lens
  now includes `NoncurrentVersionCount` and
  `NoncurrentVersionStorageBytes` as top-level dimensions. Operators
  should enable Storage Lens at the account level (free tier) before
  planning version cleanup.

- **Bucket Key default for new SSE-KMS buckets (2024-2025):** New
  SSE-KMS buckets default to `BucketKeyEnabled: true`. Older buckets
  may still have it disabled — verify and enable to reduce KMS
  request charges ~99%.

- **S3 Lifecycle rule priority warnings (2025):** The S3 console now
  warns about conflicting lifecycle rules (same prefix, overlapping
  NoncurrentDays). The CLI/API still does not warn — verify rules
  manually after PUT.

