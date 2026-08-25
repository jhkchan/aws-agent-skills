# Worked Examples — s3-lifecycle-optimizer

Moved verbatim from SKILL.md (progressive disclosure; load on demand). Sections keep their original headings.

### Worked example — already optimal compliance bucket


```text
BUCKET: compliance-archive-7yr
VERDICT: ALREADY_OPTIMAL
REASON: Bucket already transitions objects to Glacier Deep Archive at 90 days,
has Object Lock in COMPLIANCE mode with 2555-day retention, and no incomplete
multipart uploads.
RECOMMENDATION: No changes required.
SAVINGS:
  CURRENT_MONTHLY: $19.80  (20,000 GB × $0.00099 Deep Archive)
  PROJECTED_MONTHLY: $19.80
  MONTHLY_SAVING: $0.00
  ANNUAL_SAVING: $0.00
  CAVEATS: Glacier Deep Archive retrieval is $2-10/TB Standard, 12h latency.
IMPLEMENTATION: None required. Posture is correct for the workload archetype.
```

---

### Worked example — Intelligent-Tiering trap (small objects, proposed plan rejected)


This example demonstrates the **zero-savings rule**: when the proposed
transition would cost MORE than the current tier, the verdict is
`ALREADY_OPTIMAL` for the transition dimension — never
`OPPORTUNITY_FOUND` with $0 or negative savings.

```text
BUCKET: app-config-state
VERDICT: ALREADY_OPTIMAL
REASON: Proposed Intelligent-Tiering transition on 8.2M objects averaging
  4.2 KB each is MORE expensive than Standard. The monitoring fee alone
  ($20.50/month) exceeds total current cost. The 128 KB minimum billable
  size on the Infrequent tier makes tiering even more costly if objects
  drop. The proposed plan is rejected (Step 3 Archetype C threshold check
  fails: average object size < 128 KB).
RECOMMENDATION: No storage-class transition. Standard is already the cheapest
  tier for this object-size profile. Optionally add AbortIncompleteMultipartUpload
  hygiene rule (zero-cost, preventive).
SAVINGS:
  CURRENT_MONTHLY: $10.09
    - Storage: 32.0 GiB × $0.023 = $0.74
    - GETs: 8.2M × 3/month × $0.00038/1K = $9.35
    - PUTs: negligible (write-once workload)
  PROJECTED_MONTHLY (Intelligent-Tiering, best case — all in Frequent tier):
    - Monitoring fee: 8,200,000 / 1,000 × $0.0025 = $20.50
    - Storage: 32.0 GiB × $0.023 = $0.74
    - GETs: 8.2M × 3/month × $0.00038/1K = $9.35 (unchanged)
    - Total projected: $30.59
  MONTHLY_SAVING: -$20.50  (NEGATIVE — monitoring fee alone exceeds saving)
  ANNUAL_SAVING: -$246.00
  CAVEATS: The proposed plan INCREASES cost by $20.50/month (the monitoring
    fee). If objects auto-tier to Infrequent Access, cost rises further
    due to the 128 KB minimum billable size (8.2M × 128 KB = 1,025 GiB
    billable vs 32 GiB actual — a 32x storage inflation). The verdict is
    ALREADY_OPTIMAL because Standard is already the cheapest applicable
    tier. The operator should NOT proceed with Intelligent-Tiering.
IMPLEMENTATION:
  1. Do NOT apply the proposed Intelligent-Tiering transition.
  2. Optional hygiene rule (zero-cost):
     {
       "Rules": [{
         "ID": "abort-incomplete-multipart-uploads",
         "Status": "Enabled",
         "Filter": {},
         "AbortIncompleteMultipartUpload": { "DaysAfterInitiation": 7 }
       }]
     }
  3. Re-evaluate if average object size grows > 128 KB in the future.
```

**Why this verdict is ALREADY_OPTIMAL, not OPPORTUNITY_FOUND:** the
proposed plan was a transition to Intelligent-Tiering, but the math
shows it costs MORE than Standard for this object profile. There is
no saving to capture — the cheapest applicable tier is already in
place. Emitting `OPPORTUNITY_FOUND` with `$0.00` or negative savings
is a hard error per the Verdict consistency rules above.

---

## Worked example: end-to-end audit of a 5 TB mixed-workload bucket


This example walks a realistic audit from pre-flight through applied policy
with actual CLI commands and observed output. It exercises **all four
opportunity dimensions** in a single bucket: a versioned workload with
current objects in Standard, 1,420 GiB of noncurrent versions, three stale
multipart uploads, and mixed access patterns across two prefixes.

### Pre-flight (capture baseline state)

```bash
# 1. Confirm versioning status (gates the noncurrent dimension)
aws s3api get-bucket-versioning --bucket app-data-prod
# {"Status": "Enabled"}   → run noncurrent dimension

# 2. Snapshot current lifecycle for rollback (lifecycle is not versioned)
aws s3api get-bucket-lifecycle-configuration --bucket app-data-prod \
  --output json > /tmp/app-data-prod-lifecycle-backup-$(date +%s).json
# An error occurred (NoSuchLifecycleConfiguration) — bucket has no policy.
# This is NORMAL; proceed with the full recommendation (do NOT treat as error).

# 3. Detect stale multipart uploads (Step 2 dimension)
aws s3api list-multipart-uploads --bucket app-data-prod \
  --query 'Uploads[?Initiated<=`2026-07-22`]' --output table
# |     Initiated     |      Key                  | UploadId ...
# | 2026-07-15 03:14  | logs/audit-2026-07-15.log | a1b2c3...   (leak — 26 days old)
# | 2026-07-18 11:02  | backup/db-snapshot.parquet| d4e5f6...   (leak — 23 days old)
# | 2026-07-22 09:47  | tmp/export.csv            | g7h8i9...   (leak — 19 days old)
# → 3 uploads > 7 days → OPPORTUNITY_FOUND on multipart dimension

# 4. Pull Storage Lens (access-pattern evidence for transition math)
aws s3control get-storage-lens-configuration --config-id default \
  --account-id 111111111111 --output json | jq '.StorageLensConfiguration'
# Key fields used in the recommendation:
#   StorageClassDistribution: { Standard: "92%", Intelligent-Tiering: "8%" }
#   ObjectSizeDistribution:   { "128KB-1MB": "61%", "1MB-128MB": "34%", "<128KB": "5%" }
#   NoncurrentStorageBytes:   "1.42 TB" (28% of total 5.07 TB)
#   AverageObjectAge:         "147 days"
# → 92% in Standard at 147 days avg → OPPORTUNITY_FOUND on storage-class dimension
# → 1.42 TB noncurrent (28%)        → OPPORTUNITY_FOUND on noncurrent dimension

# 5. Check Object Lock (gates Expiration rule safety)
aws s3api get-object-lock-configuration --bucket app-data-prod
# An error occurred (ObjectLockConfigurationNotFoundError) — no Object Lock.
# Safe to expire logs at 365 days without retention conflict.
```

### Classify the dimensions

| Step | Dimension | Finding |
|---|---|---|
| Step 1 | Noncurrent cleanup | 1.42 TB noncurrent, no `NoncurrentVersionExpiration` → OPPORTUNITY_FOUND |
| Step 2 | Multipart cleanup | 3 uploads > 7 days → OPPORTUNITY_FOUND |
| Step 3 | Storage-class transition | 92% of 3.65 TB current in Standard at 147 days avg age → OPPORTUNITY_FOUND on `logs/` and `archive/` prefixes; `app/hot/` (small, frequently accessed) stays on Standard |
| Step 4 | Expiration | `logs/` prefix has no expiration → OPPORTUNITY_FOUND |
| Step 5 | Object Lock | Not enabled — finding only (compliance recommendation, not a verdict change) |

### Compute savings (arithmetic shown for verification)

```
Current monthly (5,070 GiB all Standard):
  5,070 GiB × $0.023 = $116.61

Projected monthly (post-lifecycle, by tier):
  CURRENT versions (3,650 GiB):
    app/hot/   800 GiB × Standard         × $0.023   = $18.40
    logs/    1,400 GiB @ Standard-IA 30-90d × $0.0125 = $17.50
    logs/      900 GiB @ Glacier IR 90-180d × $0.004  = $ 3.60
    logs/      300 GiB @ Glacier 180-365d  × $0.0036 = $ 1.08
    logs/      250 GiB expired at 365d              = $ 0.00
  NONCURRENT versions (1,420 GiB):
    600 GiB @ Standard-IA 30-90d × $0.0125          = $ 7.50
    500 GiB @ Glacier IR 90-180d × $0.004           = $ 2.00
    320 GiB expired (>180d)                          = $ 0.00
  Multipart abort (prevents future leak)             = $ 0.00
  ─────────────────────────────────────────────────────────────
  Projected total:                                   = $50.08
  Arithmetic check: 18.40 + 17.50 + 3.60 + 1.08 + 0 + 7.50 + 2.00 + 0 + 0
                   = $50.08 ✓

MONTHLY_SAVING: $116.61 − $50.08 = $66.53
ANNUAL_SAVING:  $66.53 × 12      = $798.36
```

### Emit the recommendation block

```text
BUCKET: app-data-prod
VERDICT: OPPORTUNITY_FOUND
REASON: Versioned bucket (5.07 TB) with 1.42 TB noncurrent (28%), 3 stale
  multipart uploads (19-26 days old), and 92% of current data in Standard
  at avg age 147 days. All four dimensions active (Steps 1, 2, 3, 4).
RECOMMENDATION:
  {
    "Rules": [
      {
        "ID": "logs-tiered-lifecycle",
        "Status": "Enabled",
        "Filter": { "Prefix": "logs/" },
        "Transitions": [
          { "Days": 30,  "StorageClass": "STANDARD_IA" },
          { "Days": 90,  "StorageClass": "GLACIER_IR" },
          { "Days": 180, "StorageClass": "GLACIER" }
        ],
        "Expiration": { "Days": 365 }
      },
      {
        "ID": "noncurrent-version-cleanup",
        "Status": "Enabled",
        "Filter": {},
        "NoncurrentVersionTransitions": [
          { "NoncurrentDays": 30, "NewNoncurrentStorageClass": "STANDARD_IA" },
          { "NoncurrentDays": 90, "NewNoncurrentStorageClass": "GLACIER_IR" }
        ],
        "NoncurrentVersionExpiration": { "NoncurrentDays": 180 }
      },
      {
        "ID": "abort-incomplete-multipart-uploads",
        "Status": "Enabled",
        "Filter": {},
        "AbortIncompleteMultipartUpload": { "DaysAfterInitiation": 7 }
      }
    ]
  }
SAVINGS:
  CURRENT_MONTHLY: $116.61
  PROJECTED_MONTHLY: $50.08
  MONTHLY_SAVING: $66.53
  ANNUAL_SAVING: $798.36
  CAVEATS:
    - Standard-IA 30-day minimum-duration charge on early delete (logs/).
    - Glacier IR 90-day minimum + $0.03/GB retrieval if queried.
    - app/hot/ prefix intentionally left on Standard (frequent access).
    - Backfill required for existing objects (lifecycle applies forward-only).
IMPLEMENTATION:
  1. CONFIRM: About to put-bucket-lifecycle-configuration on bucket
     app-data-prod in account 111111111111 region us-east-1. This enables 3
     rules (logs-tiered-lifecycle, noncurrent-version-cleanup, multipart-abort).
     Estimated first-cycle effect: ~1.5 TB transitions over 24-48h. Proceed? (yes/no)
  2. aws s3api put-bucket-lifecycle-configuration --bucket app-data-prod \
       --lifecycle-configuration file://lifecycle.json
  3. Verify (within 24h):
     aws s3api get-bucket-lifecycle-configuration --bucket app-data-prod
  4. Backfill the 3 stale multipart uploads immediately (lifecycle won't
     abort uploads that initiated before the rule was added):
     for uid in a1b2c3 d4e5f6 g7h8i9; do
       aws s3api abort-multipart-upload --bucket app-data-prod \
         --key <matched-key> --upload-id $uid
     done
  5. Backfill existing objects > 30 days old via S3 Batch Operations
     (lifecycle only transitions objects reaching the Days threshold AFTER
     the rule is created):
     aws s3control create-job --account-id 111111111111 \
       --operation '{"S3CopyObject": {"TargetStorageClass": "STANDARD_IA"}}' \
       --manifest-location s3://audit-manifests/app-data-prod-older-than-30d.csv \
       --report-spec '{"ReportFormat":"Report_20170828","Bucket":"arn:aws:s3:::audit-reports","Enabled":true,"ReportScope":"AllTasks"}' \
       --role-arn arn:aws:iam::111111111111:role/S3BatchOperationsRole \
       --client-request-token $(uuidgen)
```

### Apply and verify

```bash
# Apply (after operator confirms yes)
aws s3api put-bucket-lifecycle-configuration --bucket app-data-prod \
  --lifecycle-configuration file://lifecycle.json

# Verify the policy is set (immediate — no eventual consistency here)
aws s3api get-bucket-lifecycle-configuration --bucket app-data-prod \
  --output json | jq '.Rules[].ID'
# ["logs-tiered-lifecycle", "noncurrent-version-cleanup", "abort-incomplete-multipart-uploads"]

# Verify transitions ran (24-48h later — lifecycle is asynchronously processed)
aws s3control get-storage-lens-configuration --config-id default \
  --account-id 111111111111 --output json \
  | jq '.StorageLensConfiguration.StorageClassDistribution'
# Expected post-run: {"Standard": "28%", "Standard-IA": "51%", "Glacier IR": "21%"}
# If the distribution is unchanged after 48h, see Error handling →
# put-bucket-lifecycle-configuration failure modes.
```

### Worked example — compliance archive with no lifecycle (OPPORTUNITY_FOUND with correct math)

This example demonstrates the **positive-savings rule**: when a
compliance archive has no lifecycle and objects sit in Standard at
120+ days old, transitioning to Deep Archive captures real savings.
The verdict is `OPPORTUNITY_FOUND` because the math shows positive
monthly savings.

```text
BUCKET: compliance-archive-7yr
VERDICT: OPPORTUNITY_FOUND
REASON: Compliance archive with 5,000 GiB in Standard at 120 days average
  age, no lifecycle, accessed < 1x/year. Transitioning to Glacier Deep
  Archive at 90 days captures 95.7% storage saving. Versioning is Enabled
  with 0 noncurrent bytes (write-once workload). Object Lock not configured
  — surface as a parallel compliance finding (Step 5).
RECOMMENDATION:
  {
    "Rules": [
      {
        "ID": "compliance-archive-deep-archive",
        "Status": "Enabled",
        "Filter": { "Prefix": "" },
        "Transitions": [
          { "Days": 90, "StorageClass": "GLACIER_DEEP_ARCHIVE" }
        ]
      },
      {
        "ID": "abort-incomplete-multipart-uploads",
        "Status": "Enabled",
        "Filter": {},
        "AbortIncompleteMultipartUpload": { "DaysAfterInitiation": 7 }
      }
    ]
  }
SAVINGS:
  CURRENT_MONTHLY: $115.00  (5,000 GiB × $0.023 Standard)
  PROJECTED_MONTHLY: $4.95  (5,000 GiB × $0.00099 Deep Archive)
  MONTHLY_SAVING: $110.05
  ANNUAL_SAVING: $1,320.60
  CAVEATS:
    - Deep Archive 180-day minimum duration: objects deleted before day 180
      still bill. Workload is write-once with 7-year retention — no conflict.
    - Retrieval is $2-10/TB Standard (12h), $2.50/TB Bulk (48h). Budget
      separately if regulatory retrieval is likely.
    - Object Lock is NOT configured. For a compliance archive, recommend
      enabling Object Lock in COMPLIANCE mode with 2555-day retention
      (Step 5 finding — not a verdict change).
IMPLEMENTATION:
  1. CONFIRM: About to put-bucket-lifecycle-configuration on bucket
     compliance-archive-7yr. This enables Deep Archive transition at 90d
     and multipart abort. Proceed? (yes/no)
  2. aws s3api put-bucket-lifecycle-configuration \
       --bucket compliance-archive-7yr \
       --lifecycle-configuration file://lifecycle.json
  3. Verify: aws s3api get-bucket-lifecycle-configuration \
       --bucket compliance-archive-7yr
  4. Backfill existing objects > 90 days old via S3 Batch Operations
     (lifecycle only applies to objects reaching 90 days AFTER the rule
     is created):
     aws s3control create-job --account-id <acct> \
       --operation '{"S3CopyObject": {"TargetStorageClass": "GLACIER_DEEP_ARCHIVE"}}' \
       --manifest-location s3://<manifest-bucket>/manifest.csv \
       --report-spec '<report-config>' \
       --role-arn arn:aws:iam::<acct>:role/<batch-role>
```
