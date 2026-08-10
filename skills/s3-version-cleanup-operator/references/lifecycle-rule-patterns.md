# S3 Version Cleanup Lifecycle Rule Patterns Reference

Load this reference when planning or executing any S3 version cleanup
operation. The patterns below are the canonical lifecycle rules and
Batch Operations sequences for each cleanup archetype, with pre-checks,
JSON configuration, post-verification, and rollback notes.

## Decision tree — which cleanup archetype

| Scenario | Use | Why |
|---|---|---|
| Cost optimization, keep recent history | **NewerNoncurrentVersions=3 + Transition to IA/GIR** | Keep 3 recent noncurrent versions; tier mid-aged to cheaper storage |
| Cost optimization, no history needed | **NoncurrentVersionExpiration at 30-90 days** | Hard expire old versions; maximum savings |
| Compliance retention (financial/regulatory) | **Object Lock Compliance mode + Transition to GIR** | Immutable retention; tier past-retention to cheaper storage |
| Litigation hold on specific objects | **Per-object LegalHold ON (no lifecycle delete)** | Hold until released; lifecycle skips held objects |
| Immediate cleanup (not via lifecycle) | **S3 Batch Operations S3DeleteObjectVersion** | Delete millions of versions in minutes-to-hours |
| Orphaned multipart uploads | **AbortIncompleteMultipartUpload at 7 days** | Clean up partial uploads that never completed |
| Unknown access pattern | **S3 Intelligent-Tiering** | Auto-tiering with no manual rules |
| Audit before cleanup | **S3 Storage Lens NoncurrentVersionCount** | Identify top buckets by noncurrent bytes |

## Lifecycle rule JSON anatomy

A single lifecycle rule for version cleanup combines four optional
noncurrent-version actions:

```json
{
  "Rules": [
    {
      "ID": "version-cleanup-prod-logs",
      "Status": "Enabled",
      "Filter": {"Prefix": "logs/"},
      "NoncurrentVersionTransition": [
        {
          "NoncurrentDays": 30,
          "StorageClass": "STANDARD_IA"
        },
        {
          "NoncurrentDays": 90,
          "StorageClass": "GLACIER_IR"
        }
      ],
      "NoncurrentVersionExpiration": {
        "NoncurrentDays": 365,
        "NewerNoncurrentVersions": 3
      }
    }
  ]
}
```

**Field reference:**

- `Filter.Prefix` — scope the rule to a key prefix. `""` matches all
  objects; `logs/` matches only `logs/*`.
- `NoncurrentVersionTransition` — list of transitions; each moves
  noncurrent versions to the specified StorageClass after
  `NoncurrentDays` since becoming noncurrent.
- `NoncurrentVersionExpiration.NoncurrentDays` — expire noncurrent
  versions after N days since becoming noncurrent.
- `NoncurrentVersionExpiration.NewerNoncurrentVersions` — keep only
  the N most recent noncurrent versions; expire the rest. CAN be
  combined with NoncurrentDays — both conditions apply (whichever is
  reached first triggers expiration).
- `AbortIncompleteMultipartUpload.DaysAfterInitiation` — abort
  multipart uploads that haven't completed within N days of initiation.

## Pattern 1: Cost optimization with recent history (recommended default)

**When to use:** versioned buckets where you want to retain a few
recent noncurrent versions for recovery, but want to expire old
versions and tier mid-aged versions.

```json
{
  "Rules": [
    {
      "ID": "version-cleanup-with-history",
      "Status": "Enabled",
      "Filter": {"Prefix": ""},
      "NoncurrentVersionTransition": [
        {"NoncurrentDays": 30, "StorageClass": "STANDARD_IA"},
        {"NoncurrentDays": 90, "StorageClass": "GLACIER_IR"}
      ],
      "NoncurrentVersionExpiration": {
        "NewerNoncurrentVersions": 3
      }
    }
  ]
}
```

**Savings estimate:** ~70-85% of noncurrent storage cost. The 3 kept
versions stay in Standard for ~30 days, then transition to IA (50%
cheaper), then GIR (83% cheaper). Versions beyond the top 3 are
expired immediately upon becoming noncurrent+1.

## Pattern 2: Hard expiration (no history)

**When to use:** ephemeral buckets (staging, scratch, dev) where old
versions have no recovery value.

```json
{
  "Rules": [
    {
      "ID": "version-hard-expire-30d",
      "Status": "Enabled",
      "Filter": {"Prefix": ""},
      "NoncurrentVersionExpiration": {
        "NoncurrentDays": 30
      }
    }
  ]
}
```

**Savings estimate:** ~95-100% of noncurrent storage cost (versions
expire 30 days after becoming noncurrent).

## Pattern 3: Compliance retention via Object Lock

**When to use:** financial, healthcare, or regulatory workloads that
require immutable retention.

```bash
# Enable Object Lock on a NEW bucket (cannot be enabled on existing)
aws s3api create-bucket \
  --bucket compliance-archive \
  --object-lock-enabled-for-bucket

# Configure default retention
aws s3api put-object-lock-configuration \
  --bucket compliance-archive \
  --object-lock-configuration '{
    "ObjectLockEnabled": "Enabled",
    "Rule": {
      "DefaultRetention": {
        "Mode": "COMPLIANCE",
        "Years": 5
      }
    }
  }'

# Lifecycle: transition versions PAST retention to GIR
aws s3api put-bucket-lifecycle-configuration \
  --bucket compliance-archive \
  --lifecycle-configuration '{
    "Rules": [{
      "ID": "compliance-tier-after-retention",
      "Status": "Enabled",
      "Filter": {"Prefix": ""},
      "NoncurrentVersionTransition": [
        {"NoncurrentDays": 1825, "StorageClass": "GLACIER_IR"}
      ]
    }]
  }'
```

**Savings estimate:** ~80% of post-retention storage cost. In-retention
versions remain in Standard (cannot be deleted or transitioned until
retention expires).

## Pattern 4: Immediate cleanup via S3 Batch Operations

**When to use:** clean up versions already accumulated, BEFORE the
lifecycle rule takes effect, or as a one-time cleanup.

**Prerequisite:** S3 Inventory configured on the bucket (daily or
weekly CSV report). The inventory manifest is the input to Batch
Operations.

```bash
# 1. Configure S3 Inventory (one-time per bucket)
aws s3api put-bucket-inventory-configuration \
  --bucket staging-uploads \
  --id inventory-config \
  --inventory-configuration '{
    "Destination": {
      "S3BucketDestination": {
        "Bucket": "arn:aws:s3:::manifest-bucket",
        "Prefix": "staging-uploads-inventory/",
        "Format": "CSV"
      }
    },
    "IsEnabled": true,
    "Id": "inventory-config",
    "IncludedObjectVersions": "All",
    "Schedule": {"Frequency": "Daily"}
  }'

# 2. Wait for the inventory to publish (next day)

# 3. Create the Batch Operations job
aws s3control create-job \
  --account-id 111111111111 \
  --operation '{"S3DeleteObjectVersion": {}}' \
  --manifest '{
    "Spec": {
      "Format": "S3InventoryReports",
      "Bucket": "arn:aws:s3:::manifest-bucket",
      "Prefix": "staging-uploads-inventory/2026-08-08/"
    },
    "Location": {
      "ObjectArn": "arn:aws:s3:::manifest-bucket/staging-uploads-inventory/2026-08-08/manifest.json"
    }
  }' \
  --report '{
    "Bucket": "arn:aws:s3:::batch-ops-reports",
    "Prefix": "staging-uploads-cleanup-2026-08-09/",
    "Format": "Report_CSV_20180820",
    "Enabled": true,
    "ReportScope": "AllTasks"
  }' \
  --priority 50 \
  --role-arn arn:aws:iam::111111111111:role/S3BatchOperationsDeleteRole \
  --client-request-token $(uuidgen)

# 4. Poll for completion
aws s3control describe-job \
  --account-id 111111111111 \
  --job-id <returned-id>
# Status transitions Active -> Complete | Failed | Cancelled
```

**Cost:** ~$1.00 per million objects processed + S3 GET/PUT for
inventory. A 10-million-version cleanup is ~$10.

## Pattern 5: Abort multipart uploads

**When to use:** every versioned bucket should have this rule. Orphaned
multipart uploads bill at Standard rate indefinitely.

```json
{
  "Rules": [
    {
      "ID": "abort-multipart-7d",
      "Status": "Enabled",
      "Filter": {"Prefix": ""},
      "AbortIncompleteMultipartUpload": {
        "DaysAfterInitiation": 7
      }
    }
  ]
}
```

**Savings estimate:** variable — typically 5-20% of multipart-upload-
heavy buckets. Often the largest single cleanup win for upload-heavy
workloads.

## Pattern 6: Intelligent-Tiering (alternative)

**When to use:** buckets where the access pattern is unknown or
unpredictable. Intelligent-Tiering auto-moves noncurrent versions
between tiers based on access.

**Caveat:** per-object monitoring fee (~$0.0025 per 1,000 objects/
month). For small objects (<128 KB), this fee can exceed savings.

```bash
aws s3api put-bucket-lifecycle-configuration \
  --bucket unknown-pattern-bucket \
  --lifecycle-configuration '{
    "Rules": [{
      "ID": "intelligent-tiering-noncurrent",
      "Status": "Enabled",
      "Filter": {"Prefix": ""},
      "NoncurrentVersionTransition": [
        {"NoncurrentDays": 0, "StorageClass": "INTELLIGENT_TIERING"}
      ]
    }]
  }'
```

## Merging new rules into existing configuration

**CRITICAL:** `put-bucket-lifecycle-configuration` REPLACES the entire
configuration. Always read first, merge, then PUT.

```bash
# 1. Read existing rules
aws s3api get-bucket-lifecycle-configuration \
  --bucket prod-logs-bucket \
  --output json > /tmp/prod-logs-bucket-existing.json

# 2. Merge new rules into the JSON (manually or via jq)
# Example: append a new NoncurrentVersionExpiration rule
jq '.Rules += [{
  "ID": "version-cleanup-new",
  "Status": "Enabled",
  "Filter": {"Prefix": ""},
  "NoncurrentVersionExpiration": {
    "NewerNoncurrentVersions": 3
  }
}]' /tmp/prod-logs-bucket-existing.json \
  > /tmp/prod-logs-bucket-merged.json

# 3. Validate the merged JSON
python3 -c "import json; json.load(open('/tmp/prod-logs-bucket-merged.json'))"

# 4. PUT the merged config
aws s3api put-bucket-lifecycle-configuration \
  --bucket prod-logs-bucket \
  --lifecycle-configuration file:///tmp/prod-logs-bucket-merged.json

# 5. Verify
aws s3api get-bucket-lifecycle-configuration \
  --bucket prod-logs-bucket --output json
```

## Cost/savings estimation formulas

**Monthly cost of noncurrent versions (before cleanup):**
```
NoncurrentVersionStorageBytes × Standard_rate
```
Example: 13.5 TB × $0.023/GB = $312/month.

**Monthly cost after Pattern 1 (3-rule cleanup):**
```
(3_versions × avg_size × Standard_30d_rate) +
(versions_30_to_90d × IA_rate) +
(versions_past_90d × GIR_rate) + 0 for expired
```
Example: ~$95/month for the same 13.5 TB post-cleanup. Net savings
~$217/month (~70%).

**Monthly cost after Pattern 2 (hard expire 30d):**
```
versions_0_to_30d × Standard_rate
```
Example: ~$50/month for 13.5 TB post-cleanup. Net savings ~$262/month
(~84%).

**Batch Operations one-time cost:**
```
(noncurrent_version_count / 1_000_000) × $1.00
```
Example: 2.5M versions = $2.50.

## Post-apply verification checklist

After applying lifecycle rules or completing a Batch Operations job:

- [ ] `get-bucket-lifecycle-configuration` shows the new rules + preserved existing rules
- [ ] No conflicting rules (same prefix, overlapping NoncurrentDays)
- [ ] For Batch Operations: `describe-job` shows `Status: Complete`
- [ ] Job report CSV reviewed (per-object success/failure)
- [ ] Object Lock Compliance-mode versions respected (none deleted in retention)
- [ ] No legal-hold ON objects deleted
- [ ] S3 Storage Lens (after 24-48 hours): NoncurrentVersionCount and NoncurrentVersionStorageBytes dropping
- [ ] AWS Cost Explorer (after 1-3 days): S3 cost trending down for the bucket
- [ ] Replica bucket (if CRR/SRR): same lifecycle rules applied

## Common failure modes

- **`put-bucket-lifecycle-configuration` silently replaces.** Always
  read first, merge, then PUT. The API does not warn.
- **Compliance-mode versions in Batch Operations manifest.** Job
  continues but reports per-object failures. Filter the manifest by
  Object Lock retention status before submitting.
- **`LegalHold: ON` objects in Batch Operations manifest.** Same
  per-object failure pattern. Pre-filter the manifest.
- **Multipart uploads not covered by NoncurrentVersionExpiration.**
  Use `AbortIncompleteMultipartUpload` — different rule action.
- **Replica bucket not cleaned.** CRR replicates versions but
  lifecycle rules are independent per bucket. Apply the same rules
  to the replica.
- **Lifecycle rule prefix too broad/narrow.** Verify the prefix
  matches intent — `prefix: ""` affects all objects; `prefix: logs/`
  affects only `logs/*`.

---

## Expert heuristic: NoncurrentVersionExpiration vs NewerNoncurrentVersions

These two lifecycle rule actions are NOT interchangeable — confusing
them is the #1 S3 version cleanup mistake. They answer DIFFERENT
questions:

| Rule action | Question it answers | Behavior |
|---|---|---|
| `NoncurrentVersionExpiration` with `NoncurrentDays: N` | "How OLD should a noncurrent version be before it's deleted?" | Deletes ALL noncurrent versions older than N days from when they BECAME noncurrent. Keeps every version newer than N days — could be 1, could be 1,000. |
| `NewerNoncurrentVersions` with `N: M` | "How many recent noncurrent versions should I keep?" | Keeps only the M most recent noncurrent versions. Deletes the rest regardless of age. |

**Why you should use BOTH (defense in depth):**
- `NewerNoncurrentVersions: 3` keeps the 3 most recent versions
  regardless of age — useful for "undo" but allows unlimited growth
  if versions become noncurrent slowly.
- `NoncurrentVersionExpiration: 90` deletes versions older than 90
  days regardless of count — useful for "compliance retention window"
  but allows 1,000 versions in the first 90 days.
- COMBINED: keep the 3 most recent versions, AND expire anything
  older than 90 days. Whichever condition triggers first wins. This
  caps cost AND preserves recent history.

**Worked example — log bucket with hourly overwrites:**

```json
{
  "ID": "version-cleanup-defense-in-depth",
  "Status": "Enabled",
  "Filter": { "Prefix": "logs/" },
  "NoncurrentVersionExpiration": { "NoncurrentDays": 90 },
  "NoncurrentVersionTransition": [
    { "NoncurrentDays": 30, "StorageClass": "STANDARD_IA" },
    { "NoncurrentDays": 60, "StorageClass": "GLACIER_INSTANT_RETRIEVAL" }
  ],
  "NewerNoncurrentVersions": 3
}
```

**Common mistake:** operators add `NewerNoncurrentVersions: 3` thinking
it "expires" old versions. It does NOT — it keeps the 3 NEWEST, but
versions outside the top 3 are NOT deleted unless a separate
`NoncurrentVersionExpiration` rule also matches. The bucket continues
to bill for all older versions until `NoncurrentVersionExpiration`
fires.

**Common mistake (inverse):** operators add `NoncurrentVersionExpiration:
90` thinking it "keeps only the last 90 days." It does — but for a
high-frequency overwrite pattern, 90 days can mean thousands of
versions. Add `NewerNoncurrentVersions: N` to cap the absolute count.

## S3 Batch Operations DeleteObjectVersion is NOT free

S3 Batch Operations charges **~$1.00 per million objects processed**,
regardless of operation type. A version-cleanup Batch Operations job
that deletes 1 billion noncurrent versions costs **$1,000** —
sometimes more than the storage savings from the cleanup itself.

**Cost-comparison table (2026 us-east-1):**

| Cleanup scenario | Object count | Batch Operations cost | Storage saved (monthly) | Payback period |
|---|---|---|---|---|
| Small cleanup | 1M versions | $1.00 | $23 (1 TB Standard) | 1.3 months |
| Medium cleanup | 100M versions | $100 | $230 (10 TB Standard) | 13 days |
| Large cleanup | 1B versions | $1,000 | $2,300 (100 TB Standard) | 13 days |
| Very large cleanup | 10B versions | $10,000 | $23,000 (1 PB Standard) | 13 days |

**Hidden costs beyond the per-million fee:**
1. **Manifest generation:** paginating `list-object-versions` for a
   billion-version bucket takes hours of API calls. Prefer S3 Inventory
   (daily or weekly CSV snapshots, free with S3).
2. **Partial-failure handling:** Batch Operations reports per-object
   failures in a CSV report. Object Lock Compliance-mode and
   legal-hold ON objects fail per-object — the job continues but does
   NOT delete those versions. Plan a second pass for failures.
3. **Re-runs:** if the job fails partway, the partial deletes are
   NOT refunded. Budget for at least one re-run.

**Decision rule:**
- If lifecycle rules can achieve the same outcome within an acceptable
  timeframe (24-48 hours of processing lag), use lifecycle rules
  (free).
- Reserve Batch Operations for: (a) immediate one-time cleanup that
  cannot wait for lifecycle processing, (b) selective deletes matching
  a manifest that lifecycle rules cannot express.
- ALWAYS compute the per-million cost before launching a Batch
  Operations job. Surface the cost in the operation plan as
  `ESTIMATED_BATCH_COST`.
