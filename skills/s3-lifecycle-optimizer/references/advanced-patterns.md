# Advanced Patterns — s3-lifecycle-optimizer

Moved verbatim from SKILL.md (progressive disclosure; load on demand). Sections keep their original headings.

## Mindset


**One-line takeaway:** the verdict is the **largest net-positive saving** after
accounting for minimum-duration charges and retrieval fees — driven by four
S3 realities:

- **Lifecycle transitions are free to set but cost-prohibitive to undo.** A
  premature Glacier transition on objects that turn out to be accessed weekly
  incurs retrieval fees that wipe out months of savings. Always ground the
  recommendation in observed access patterns (Storage Lens, CloudTrail
  `GetObject`, or tags) before tiering.
- **Minimum-duration charges dominate for short-lived objects.** Moving a
  5-day-old object to Standard-IA bills the full 30-day IA charge even if it
  is deleted on day 6. For logs that roll over weekly, IA is the wrong tier.
- **Noncurrent versions are the silent S3 bill.** A versioned bucket with no
  `NoncurrentVersionExpiration` rule accumulates every prior version of every
  object indefinitely — 100 TB of "current" data routinely hides 400 TB of
  noncurrent bytes that nobody looks at.
- **Multipart uploads that never complete bill forever.** `AbortMultipartUpload`
  is a one-line lifecycle rule that stops indefinite accumulation of orphaned
  parts; almost every bucket operated >1 year has leaked parts.

---

### Step 0: Expert knowledge — non-obvious S3 lifecycle behaviors


These behaviors are easy to misjudge without operational S3 experience.
Each changes a recommendation if ignored:

- **Transition `Days` counts from object creation, not from policy creation.**
  A rule that says "transition to Standard-IA after 30 days" applies to objects
  that are already 60 days old the moment the rule is added — they transition
  immediately. This is usually what you want, but surprises operators.

- **Minimum-duration charges bill regardless of when the object is deleted.**
  Standard-IA bills 30 days minimum, Glacier tiers bill 90/180 days minimum.
  If the workload deletes objects sooner, the storage class is more expensive
  than Standard. Always model minimum-duration cost vs Standard before
  recommending a transition.

- **Small-object surcharge on IA tiers.** Standard-IA and One-Zone-IA have a
  minimum billable size of 128 KB. Objects smaller than 128 KB are billed as
  if they were 128 KB — for buckets of small JSON/config files, IA is often
  MORE expensive than Standard.

- **Intelligent-Tiering has a monitoring fee of $0.0025 per 1,000 objects.**
  For buckets of millions of small objects, the monitoring fee can exceed the
  transition savings. Threshold: Intelligent-Tiering wins when average object
  size > 128 KB and access pattern is genuinely mixed.

- **Glacier retrieval is not free.** Standard retrieval from Glacier Flexible
  is $2.50-10 per TB (5-12 hours), Expedited is $10-30 per TB (1-5 min). Glacier
  Deep Archive Standard is $2-10 per TB (12 hours), Bulk is $2.50/TB (48h).
  Always warn that the saving is a storage saving; retrieval is à la carte.

- **Lifecycle rules are eventually applied.** S3 processes lifecycle transitions
  asynchronously, typically once per day. A rule added at 09:00 may not execute
  until the next lifecycle run. Do not alarm on a 24-hour lag.

- **A lifecycle rule with a filter that matches no objects is silently a no-op.**
  `Filter: { Prefix: "logs/2024/" }` on a bucket where logs are under
  `2025/logs/` matches nothing. Always cross-check the prefix against the actual
  key layout before declaring ALREADY_OPTIMAL.

- **`ExpirationInDays` deletes the current version. `NoncurrentVersionExpiration`
  deletes prior versions.** Conflating them produces data loss: setting
  `ExpirationInDays: 30` on a versioned bucket with no noncurrent rule deletes
  the current version (creating a new noncurrent version) but leaves all prior
  noncurrent versions intact — increasing storage instead of reducing it.

- **S3 Batch Operations complements lifecycle for one-time migrations.**
  Lifecycle applies to future objects going forward, but existing objects only
  transition when their `Days` threshold is reached. To immediately move
  existing Standard objects to Glacier, use `create-job` with
  `S3CopyObject` and the target storage class — lifecycle handles the
  forward path, Batch handles the backfill.

- **Intelligent-Tiering Archive configurations are tunable.** The default
  Archive tier moves objects after 90 consecutive days of no access; Deep
  Archive moves after 180. Both are configurable via
  `Tierings[{AccessTier: ARCHIVE_ACCESS, Days: N}]` — for known-cold data,
  shorter windows capture savings faster.

- **S3 Object Lock retention is enforced before lifecycle expiration.** If
  an object has a `COMPLIANCE` mode retention period ending in 2030, a
  lifecycle rule with `ExpirationInDays: 365` will NOT delete it until 2030.
  The rule is a no-op for the locked object; surface this so the operator
  understands the lifecycle does not bypass compliance.

- **Cross-Region Replication (CRR) preserves storage class by default.**
  Replicating a Standard object to a destination bucket copies it as Standard
  unless the replication rule specifies a different storage class. Destination
  lifecycle rules apply independently — design them in tandem.

- **S3 Tables (managed Apache Iceberg) have their own lifecycle.** Do not
  propose `Expiration` rules on table data prefixes; Iceberg compaction and
  snapshot expiration are managed via table APIs. Surface as a finding only.

- **Directory buckets (S3 Express One Zone) do not support lifecycle, Object
  Lock, or Glacier tiers.** They are designed for single-AZ, ms-latency ML/AI
  workloads at $0.16/GB. Verdict for a directory bucket is ALREADY_OPTIMAL
  for its intended use case; surface the cost-per-GB as a finding.

---

### Step 1: Noncurrent version cleanup (versioned buckets)


- **Pull noncurrent byte % from Storage Lens.** A bucket with >20% noncurrent
  bytes is a high-confidence opportunity. >50% is severe.
- **Recommended default rule:**
  - Transition noncurrent versions to Standard-IA after 30 days.
  - Transition to Glacier Instant Retrieval after 90 days.
  - Expire noncurrent versions after 90-180 days (tune by workload).
- **Pattern — versioning cleanup:**
  ```json
  {
    "ID": "noncurrent-version-cleanup",
    "Status": "Enabled",
    "Filter": {},
    "NoncurrentVersionTransitions": [
      { "NoncurrentDays": 30, "NewNoncurrentStorageClass": "STANDARD_IA" },
      { "NoncurrentDays": 90, "NewNoncurrentStorageClass": "GLACIER_IR" }
    ],
    "NoncurrentVersionExpiration": { "NoncurrentDays": 180 }
  }
  ```
- **Savings estimate:** `noncurrent_bytes_GB × (Standard_rate - IA_rate)` for
  the first 30 days, then taper. Most versioned buckets save 40-70% on the
  noncurrent dimension alone.
---

### Step 2: Multipart upload cleanup

- **Recommended rule (always include, even on buckets without known leaks):**
  ```json
  {
    "ID": "abort-incomplete-multipart-uploads",
    "Status": "Enabled",
    "Filter": {},
    "AbortIncompleteMultipartUpload": { "DaysAfterInitiation": 7 }
  }
  ```
- **Savings estimate:** pending parts bill at Standard rate. A 100 GB
  half-uploaded file costs $2.30/month indefinitely. The rule pays for itself
  in zero cost.
---

### Step 3: Storage-class transition design (current objects)

```json
{
  "ID": "logs-lifecycle",
  "Status": "Enabled",
  "Filter": { "Prefix": "logs/" },
  "Transitions": [
    { "Days": 30, "StorageClass": "STANDARD_IA" },
    { "Days": 90, "StorageClass": "GLACIER_IR" },
    { "Days": 180, "StorageClass": "GLACIER" }
  ],
  "Expiration": { "Days": 365 }
}
```
```json
{
  "ID": "compliance-archive",
  "Status": "Enabled",
  "Filter": { "Prefix": "archive/" },
  "Transitions": [
    { "Days": 90, "StorageClass": "GLACIER_DEEP_ARCHIVE" }
  ]
}
```
```json
{
  "ID": "app-data-intelligent-tiering",
  "Status": "Enabled",
  "Filter": { "Prefix": "app/" },
  "Transitions": [
    { "Days": 0, "StorageClass": "INTELLIGENT_TIERING" }
  ]
}
```
```json
{
  "ID": "backup-tier",
  "Status": "Enabled",
  "Filter": { "Prefix": "backup/" },
  "Transitions": [
    { "Days": 30, "StorageClass": "GLACIER_IR" },
    { "Days": 90, "StorageClass": "GLACIER" }
  ]
}
```
---

## Cross-region cost variance detail


The Quick reference pricing table is us-east-1 baseline. S3 pricing
varies materially by region; a recommendation that saves money in
us-east-1 may save MORE or LESS in another region:

| Region | Standard $/GB-mo | Standard-IA $/GB-mo | Deep Archive $/GB-mo | Notes |
|---|---|---|---|---|
| us-east-1, us-west-2 | 0.023 | 0.0125 | 0.00099 | Baseline |
| eu-west-1 (Ireland) | 0.024 | 0.013 | 0.001 | ~4% premium |
| eu-central-1 (Frankfurt) | 0.0245 | 0.013 | 0.001 | ~7% premium; high egress |
| ap-southeast-1 (Singapore) | 0.025 | 0.0141 | 0.001 | ~9% premium |
| ap-southeast-2 (Sydney) | 0.025 | 0.014 | 0.0011 | ~9% premium |
| ap-northeast-1 (Tokyo) | 0.025 | 0.0138 | 0.0011 | ~9% premium |
| ap-south-1 (Mumbai) | 0.0259 | 0.0144 | 0.00114 | ~13% premium |
| sa-east-1 (São Paulo) | 0.0309 | 0.01688 | 0.00153 | ~35% premium; egress highest |
| af-south-1 (Cape Town) | 0.0304 | 0.0166 | 0.00153 | ~32% premium |

**Decision impact:**

- **High-premium regions (sa-east-1, af-south-1):** lifecycle
  transitions capture MORE savings because the gap between Standard
  and Glacier is wider. Recommend AGGRESSIVE transitions (earlier
  `Days` thresholds) — the math favours moving to Glacier IR or
  Flexible sooner.
- **Low-premium regions (us-east-1, us-east-2):** the savings delta
  is smaller; the Intelligent-Tiering monitoring fee and minimum-
  duration charges eat a larger share of the saving. Be more
  conservative on small-object buckets.
- **Always re-state the regional rate** in the SAVINGS block when the
  bucket is not in us-east-1. Pull the rate from the AWS Pricing API
  (`aws pricing get-products --service-code AmazonS3 --filters ...`)
  rather than estimating from the multiplier.

---

## Edge-case handling


These are buckets where the standard archetype patterns (Step 3) produce
wrong recommendations without explicit handling.

### Objects < 128 KB (IA small-object surcharge)

Standard-IA, One-Zone-IA, and the Intelligent-Tiering Infrequent tier carry
a **128 KB minimum billable size**. A 4 KB object is billed as 128 KB — a
**32x storage-cost inflation**. For buckets of small JSON/config files, IA
tiers are often MORE expensive than Standard despite the lower $/GB rate.

**Detection:** pull `ObjectSizeDistribution` from Storage Lens. If the
`<128KB` bucket is more than 20% of objects by count, the IA tiers are
likely net-negative on savings.

**Fix:** keep small-object buckets on Standard. If a bucket has a mix of
small and large objects, scope the IA transition rule with a tag so small
objects stay on Standard while large objects tier down:

```json
{
  "ID": "large-object-ia-only",
  "Status": "Enabled",
  "Filter": { "Tag": { "Key": "archive_eligible", "Value": "true" } },
  "Transitions": [
    { "Days": 30, "StorageClass": "STANDARD_IA" }
  ]
}
```

Apply the `archive_eligible=true` tag via a tag-based lifecycle rule or a
Bucket Policy condition at PUT time so publishers self-classify.

### Versioned bucket with 1,000+ noncurrent versions per object

A heavily-overwritten versioned bucket (e.g., a state file written every
minute, or a config map re-written on every deploy) can accumulate tens of
thousands of noncurrent versions per object. A bare
`NoncurrentVersionExpiration: { NoncurrentDays: 180 }` does NOT cap the
count — it only expires versions older than 180 days. The bucket can still
hold ~260,000 versions per object (one per minute × 180 days).

**Detection:**
```bash
aws s3api list-object-versions --bucket <name> --prefix <key> \
  --query 'Versions | length(@)'
# Returns > 1,000 for a single key → high-churn pattern
```

**Fix:** add `NewerNoncurrentVersions` to cap the count regardless of age
(requires the S3 Lifecycle filtering model introduced Aug 2023):

```json
{
  "ID": "cap-noncurrent-count",
  "Status": "Enabled",
  "Filter": {},
  "NoncurrentVersionExpiration": {
    "NoncurrentDays": 30,
    "NewerNoncurrentVersions": 10
  }
}
```

This keeps the 10 most recent noncurrent versions and expires the rest after
30 days. The two limits interact as a logical OR — whichever triggers first
expires the version.

**Savings impact:** a state bucket with 50,000 versions per object across
100 objects routinely holds 20+ TB of noncurrent bytes. Capping at 10
versions plus 30-day expiry typically reduces noncurrent storage by 90%+.
Always surface this in the savings projection when the high-churn pattern
is detected — `NoncurrentDays` alone undercounts the saving.

### Bucket with Object Lock in COMPLIANCE mode

A COMPLIANCE-mode Object Lock retention period is **immutable** — even
root cannot shorten or bypass it. A lifecycle `ExpirationInDays` shorter
than the retention period is silently a no-op on locked objects: the rule
is stored, the operator sees it applied, but locked objects survive past
the expiry date because lifecycle honors the retention lock.

**Detection:**
```bash
aws s3api get-object-lock-configuration --bucket <name>
# {"ObjectLockConfiguration": {"Rule": {"DefaultRetention":
#   {"Mode": "COMPLIANCE", "Days": 2555}}}}
```

**Fix:** set `ExpirationInDays` to AT LEAST the retention period, and
surface the interaction in the output block:

```text
CAVEATS:
  - Object Lock COMPLIANCE mode with 2555-day retention. ExpirationInDays
    set to 2555 to match — objects are NOT deletable before retention ends,
    even by root. Lifecycle will not accelerate deletion; it only takes
    effect on objects whose retention has expired.
  - Per-object legal holds override lifecycle ENTIRELY. An object under
    legal hold is never expired, regardless of ExpirationInDays or the
    retention period. Detect with `aws s3api get-object-legal-hold` and
    surface as a finding — there is no lifecycle fix for legal hold.
  - GOVERNANCE mode (if applicable) can be bypassed by principals with
    s3:BypassGovernanceRetention — surface as a parallel compliance finding
    and recommend COMPLIANCE mode for true regulatory workloads.
```

If `ExpirationInDays < retention period`, downgrade the dimension to a
CONFIG finding — do not emit OPPORTUNITY_FOUND on the Expiration dimension,
because the saving cannot be captured until retention expires.

---

## Recent AWS features (2024-2026)


- **S3 Intelligent-Tiering Archive configurations (2024-2025):** Intelligent-
  Tiering now supports configurable Archive Access and Deep Archive Access
  tiers (`Tierings[{AccessTier: ARCHIVE_ACCESS, Days: N}]`). Default is 90/180
  days; tunable for known-cold data to capture savings faster. No retrieval fee
  on the tier transition itself; standard Glacier retrieval fees apply on read.

- **S3 Storage Lens (general availability, expanded 2024-2026):** Organization-
  wide dashboards with 29+ metrics including noncurrent-byte %, storage-class
  distribution, object-age histogram, and prefix-level drill-down. Always pull
  Storage Lens before recommending a transition — it provides the access-pattern
  evidence the recommendation needs.

- **S3 Tables (managed Apache Iceberg, 2025):** Tabular data stored in S3 with
  Iceberg table format, supporting ACID transactions, schema evolution, and
  time travel. Tables have their own lifecycle (snapshot expiration,
  compaction) — do NOT propose S3 lifecycle rules on table data prefixes.

- **S3 Express One Zone (directory buckets, 2023-2025):** Single-AZ directory
  buckets with ms-latency HEAD/GET, designed for ML/AI training and high-
  performance analytics. $0.16/GB, no lifecycle support, no Object Lock.
  Use for the active training set; tier to general-access buckets after.

- **Glacier Instant Retrieval (GA):** Millisecond-latency retrieval at $0.004/GB
  with 90-day minimum. The right tier for quarterly-accessed data that still
  needs ms reads (analytics, compliance lookups).

- **S3 Batch Operations (expanded):** Supports `S3CopyObject` with
  `TargetStorageClass` for one-time backfill migrations of existing objects
  (lifecycle only transitions new objects going forward). Pair with lifecycle
  for the complete migration path.

- **S3 Object Lock expanded retention options:** `COMPLIANCE` mode now supports
  per-object legal hold alongside retention period. Use legal hold for
  indefinite holds (litigation, investigation); use retention period for
  regulatory horizons.

---

## AWS documentation


- **Amazon S3 User Guide** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html
- **Managing your storage lifecycle** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html
- **Amazon S3 Storage Classes** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage-class-intro.html
- **S3 Intelligent-Tiering** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage-class-intro.html#sc-d behavior-data-retrieval
- **S3 Storage Lens** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage_lens_basics_metrics.html
- **S3 Object Lock** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html
- **S3 Batch Operations** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/batch-ops.html
- **AWS CLI Command Reference: s3api** — https://docs.aws.amazon.com/cli/latest/reference/s3api/
- **S3 Express One Zone** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-express-one-zone.html
- **S3 Tables** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/tables.html
