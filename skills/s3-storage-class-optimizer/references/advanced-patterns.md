# Advanced Patterns — s3-storage-class-optimizer

Moved verbatim from SKILL.md (progressive disclosure; load on demand). Sections keep their original headings.

## Mindset

S3 cost optimization is a data-placement decision, not a throughput
exercise. The goal is the storage-class distribution that minimizes
total cost while preserving retrieval SLAs — not the absolute cheapest
tier regardless of access needs.

Four principles guide every recommendation:

- **Object age is the primary signal.** S3 access patterns are
  overwhelmingly write-once-read-rarely. The age of an object is the
  strongest predictor of future access. Lifecycle policies formalize
  this.
- **Retrieval cost can negate storage savings.** Moving 10 TB to Deep
  Archive saves $220/month in storage but a single full-restore costs
  $25 (bulk). If the business does monthly full restores, the retrieval
  cost ($300/year) may approach the storage savings ($2,640/year) —
  still net positive, but the operator must know.
- **Versioning multiplies cost invisibly.** Every PUT creates a new
  version in a versioned bucket. Without lifecycle rules on noncurrent
  versions, storage grows unbounded. Noncurrent transitions and
  expirations are the fix.
- **Intelligent-Tiering vs lifecycle is not either/or.** Use lifecycle
  for predictable patterns (logs, backups) and Intelligent-Tiering for
  unpredictable ones (user uploads, shared documents). Mixing is valid.

---

## Configuration dependency graph (diagram)

```
                    ┌──────────────────────┐
                    │  Storage Lens (data) │
                    │  Cost Explorer ($$)  │
                    └──────────┬───────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
    ┌─────────────────┐ ┌────────────┐ ┌──────────────┐
    │ Lifecycle Policy│ │ Intelligent│ │ Versioning   │
    │ (Step 1)        │ │ -Tiering   │ │ Lifecycle    │
    │                 │ │ (Step 2)   │ │ (Step 4)     │
    └───────┬─────────┘ └─────┬──────┘ └──────┬───────┘
            │                 │               │
            ▼                 ▼               ▼
    ┌──────────────────────────────────────────────┐
    │          Retrieval-Pattern Gate (Step 5)      │
    │  Verify archive retrieval won't exceed budget │
    └──────────────────────┬───────────────────────┘
                           │
                           ▼
    ┌──────────────────────────────────────────────┐
    │       S3 Batch Operations (Step 6)            │
    │       Bulk class migration execution          │
    └──────────────────────┬───────────────────────┘
                           │
                           ▼
    ┌──────────────────────────────────────────────┐
    │          Impact Estimation (Step 7)           │
    │          Verdict + savings block               │
    └──────────────────────────────────────────────┘
```

---

### Step 0: Non-obvious behaviours that change the recommendation

These operational gotchas route a recommendation away from the obvious
choice:

- **Minimum-days constraints are mandatory.** Standard→Standard-IA
  requires objects to be at least 30 days old. Standard-IA→Glacier
  Instant Retrieval requires 30 days in IA first. You cannot create
  a lifecycle rule that transitions to IA at 1 day.
- **Transition costs money.** Each lifecycle transition charges a
  per-request fee ($0.01/1,000 requests for Standard→IA). For buckets
  with millions of tiny objects, the transition request cost can
  exceed the first month's storage savings.
- **Intelligent-Tiering monitoring fee is flat.** $2.50/TB-month
  regardless of how many objects. For buckets < 1 TB, the monitoring
  fee may exceed the savings. Break-even: Intelligent-Tiering pays off
  when the storage savings from auto-tiering exceed $2.50/TB-month.
- **Glacier Instant Retrieval is NOT the same as Standard-IA.** GIR
  costs $4/TB-month (vs IA's $12.50) and provides millisecond access.
  It is ideal for long-lived data accessed once a quarter. Standard-IA
  costs $12.50/TB-month with a per-GB retrieval fee.
- **Deep Archive minimum storage duration is 180 days.** Moving an
  object to Deep Archive and deleting it before 180 days incurs an
  early-delete charge equal to the remaining storage cost.
- **Versioning creates invisible storage.** Every overwrite in a
  versioned bucket retains the prior version. Without noncurrent-
  version lifecycle rules, storage grows linearly with writes.
- **Delete markers count as objects.** In a versioned bucket, a DELETE
  operation creates a delete marker (0-byte). Millions of delete
  markers have negligible storage cost but bloat LIST operations.
- **MFA Delete blocks lifecycle expirations.** If MFA Delete is enabled
  on a versioned bucket, lifecycle expiration of current versions
  requires MFA approval. Plan accordingly.
- **S3 Batch Operations COPY changes class.** To migrate existing
  objects to a new storage class without waiting for lifecycle timing,
  use Batch Operations with a COPY job and `StorageClass` override.
- **One-zone IA is 20% cheaper but has no redundancy.** One Zone-IA
  costs $10.10/TB-month (vs Standard-IA $12.50). Data loss risk if
  the AZ fails. Use only for reproducible data.

---

## Step 1 — lifecycle template and minimum-days matrix

**Standard lifecycle template (data-lake / log archive pattern):**

```json
{
  "Rules": [
    {
      "ID": "data-lake-tiering",
      "Status": "Enabled",
      "Filter": { "Prefix": "" },
      "Transitions": [
        { "Days": 30,  "StorageClass": "STANDARD_IA" },
        { "Days": 90,  "StorageClass": "GLACIER_IR" },
        { "Days": 180, "StorageClass": "GLACIER" },
        { "Days": 365, "StorageClass": "DEEP_ARCHIVE" }
      ],
      "Expiration": { "Days": 2555 }
    }
  ]
}
```

**Transition timing — minimum-days matrix:**

| Transition | Min days in current tier | Min days in Standard (cumulative) | Storage rate delta |
|---|---|---|---|
| Standard → Standard-IA | 30 | 30 | $23 → $12.50 (saves $10.50/TB-mo) |
| Standard → One Zone-IA | 30 | 30 | $23 → $10.10 (saves $12.90/TB-mo) |
| Standard → Glacier IR | 0 | 0 | $23 → $4.00 (saves $19.00/TB-mo) |
| Standard-IA → Glacier IR | 30 | 60 | $12.50 → $4.00 (saves $8.50/TB-mo) |
| Standard-IA → Glacier Flexible | 30 | 60 | $12.50 → $3.60 (saves $8.90/TB-mo) |
| Glacier IR → Glacier Flexible | 0 | 90 | $4.00 → $3.60 (saves $0.40/TB-mo) |
| Standard → Glacier Flexible | 1 | 1 | $23 → $3.60 (saves $19.40/TB-mo) |
| Standard → Deep Archive | 1 | 1 | $23 → $0.99 (saves $22.01/TB-mo) |
| Glacier Flexible → Deep Archive | 90 | 90 | $3.60 → $0.99 (saves $2.61/TB-mo) |

---

## Step 1 — per-TB savings calculation

**Per-TB savings calculation:**
```
savings_per_TB = affected_TB × (current_rate − new_rate)
transition_cost = (affected_TB / avg_object_size_GB) × $0.01/1000
net_monthly_savings = savings_per_TB − (transition_cost / months_to_amortize)
```

---

## Step 2 — Intelligent-Tiering configuration and cost comparison

**Intelligent-Tiering tier configuration:**

```bash
aws s3api put-bucket-intelligent-tiering-configuration \
  --bucket my-bucket \
  --id ConfigID \
  --intelligent-tiering-configuration '{
    "Status": "Enabled",
    "Tierings": [
      {"Days": 90, "AccessTier": "ARCHIVE_ACCESS"},
      {"Days": 180, "AccessTier": "DEEP_ARCHIVE_ACCESS"}
    ]
  }'
```

**Cost comparison: Intelligent-Tiering vs lifecycle for 50 TB:**
```
Intelligent-Tiering: $125/mo monitoring + $483.25 storage = $608.25/mo
Lifecycle:           $0 monitoring + $429.85 storage = $429.85/mo
Lifecycle is $178.40/mo cheaper for predictable patterns.
But IT avoids misclassification risk for unpredictable access.
```

---

## Step 3 — prefix-based grouping example

**Prefix-based grouping for cost allocation:**
```
Bucket: data-lake-prod
  /raw/logs/          — 20 TB, 95% >180d, <0.1% retrieval → DA at 180d (saves $380/mo)
  /raw/events/        — 10 TB, 60% >90d, <1% retrieval → GIR at 90d (saves $114/mo)
  /curated/reports/   — 8 TB, 80% <30d, 15% retrieval → keep Standard
  /archive/snapshots/ — 7 TB, 100% >365d, 0% retrieval → Batch Ops to DA (saves $154/mo)
```

---

## Step 4 — noncurrent-version lifecycle template

**Noncurrent-version lifecycle template:**
```json
{
  "ID": "noncurrent-version-tiering",
  "Status": "Enabled",
  "NoncurrentVersionTransitions": [
    { "NoncurrentDays": 30,  "NewerNoncurrentVersions": 3, "NewStorageClass": "STANDARD_IA" },
    { "NoncurrentDays": 90,  "NewerNoncurrentVersions": 3, "NewStorageClass": "GLACIER_IR" },
    { "NoncurrentDays": 180, "NewerNoncurrentVersions": 3, "NewStorageClass": "DEEP_ARCHIVE" }
  ],
  "NoncurrentVersionExpiration": { "NoncurrentDays": 365, "NewerNoncurrentVersions": 3 }
}
```

---

## Step 4 — delete marker cleanup command

**Delete marker cleanup:**
```bash
# Schedule a Batch Operations job to remove delete markers
# on objects where the delete marker is the only version
aws s3control create-job \
  --account-id <acct> \
  --operation '{"S3DeleteObjectTagging": {}}' \
  --manifest '{"Spec": {"Format": "S3BatchOperations_CSV_20180820",
               "Location": {"Bucket": "...","Key": "..."}}}'
```

---

## Step 5 — retrieval cost surprise prevention

**Retrieval cost surprise prevention:**
```
monthly_retrieval_cost = retrieved_GB × retrieval_rate

Example: 5 TB retrieved from Glacier Flexible per month (standard):
  5,120 GB × $0.03 = $153.60/month retrieval
  vs storage savings: 5 TB × ($12.50 - $3.60) = $44.50/month saved

  NET: the retrieval cost EXCEEDS the storage savings.
  This bucket should use Standard-IA, not Glacier Flexible.
```

---

## Step 6 — Batch Operations COPY with class override

**Batch Operations COPY with class override:**
```bash
# Generate manifest of Standard-class objects
aws s3api list-objects-v2 --bucket my-bucket \
  --query 'Contents[?StorageClass==`STANDARD`].[Key]' \
  --output text | awk '{print "my-bucket,"$1}' > manifest.csv
aws s3 cp manifest.csv s3://manifest-bucket/manifest.csv

# Create Batch Operations job
aws s3control create-job --account-id <acct> \
  --operation '{"S3ReplicateObject": {}}' \
  --report '{"Bucket":"s3://report-bucket","Enabled":true}' \
  --manifest '{"Spec":{"Format":"S3BatchOperations_CSV_20180820","Location":{"Bucket":"manifest-bucket","Key":"manifest.csv"}}}' \
  --role-arn arn:aws:iam::<acct>:role/S3BatchOperationsRole
```

---

## Step 7 — impact estimation formulas

```
current_monthly_cost =
  standard_TB × $23 + standard_ia_TB × $12.50 + one_zone_ia_TB × $10.10 +
  glacier_ir_TB × $4.00 + glacier_TB × $3.60 + deep_archive_TB × $0.99

projected_monthly_cost =
  projected_standard_TB × $23 + projected_ia_TB × $12.50 +
  projected_gir_TB × $4.00 + projected_glacier_TB × $3.60 +
  projected_deep_archive_TB × $0.99 + intelligent_tiering_monitoring_fee

monthly_saving = current_monthly_cost - projected_monthly_cost
```

---

## Recent AWS features (2024-2026)

- **S3 Intelligent-Tiering Archive Access (2024-2025):** Configurable
  Archive Access at 90 days and Deep Archive Access at 180 days. No
  retrieval fees for moving between tiers within IT.
- **S3 Glacier Instant Retrieval (GIR) maturity:** Millisecond-latency
  archive at $4/TB-month. Increasingly the default choice for quarterly-
  access data that needs fast retrieval.
- **S3 Storage Lens prefix-level metrics (2024):** Object-age and
  activity breakdown by prefix. Requires Storage Lens Advanced (paid).
  Free tier provides bucket-level only.
- **S3 Batch Operations COPY with storage class (2024):** COPY job can
  override the storage class, enabling immediate bulk migration without
  waiting for lifecycle timing.
- **S3 Object Lambda cost (2024-2025):** Not directly a storage-class
  concern but affects total S3 bill. Flag if Object Lambda is in use.
- **Directory Buckets (S3 Express One Zone, 2024-2025):** Ultra-low-
  latency bucket type for ML/AI training data. Different pricing model
  ($0.16/GB-month + request fees). Out of scope for this skill but
  flag if detected.
- **S3 Tables (2025):** Managed Apache Iceberg tables on S3. Separate
  pricing from standard storage. Flag if detected.
