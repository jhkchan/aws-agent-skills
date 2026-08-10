# End-to-end usage scenario: s3-version-cleanup-operator

A walkthrough showing the skill planning a 3-rule version cleanup
(NoncurrentVersionTransition + NoncurrentVersionExpiration with
NewerNoncurrentVersions) for a versioned production logs bucket that
already has 3 lifecycle rules. The pre-checks pass on versioning state,
Object Lock absence, Bucket Key, and the existing rules are MERGED into
the new config (not replaced), producing a READY plan with the exact
CLI/JSON sequence, the CONFIRM gate, and the estimated savings — and
contrasted with the BLOCKED case where Object Lock Compliance mode
blocks immediate Batch Operations deletion.

## Input (user prompt)

> We're paying too much for prod-logs-bucket — 13.5 TB of noncurrent
> versions at $312/month. We want to keep the 3 most recent versions,
> tier mid-aged versions to IA and Glacier IR, and expire the rest.
> The bucket already has lifecycle rules for current-version tiering
> and abort-multipart.

```json
{
  "Operation": "configure-lifecycle",
  "Bucket": "prod-logs-bucket",
  "Region": "us-east-1",
  "Account": "111111111111",
  "New rule intent": "keep 3 most recent noncurrent versions; expire the rest; transition kept versions to STANDARD_IA at 30d and GLACIER_IR at 90d",
  "BucketVersioning": {
    "Status": "Enabled",
    "MFADelete": "Disabled"
  },
  "ObjectLockConfiguration": null,
  "BucketEncryption": {
    "ServerSideEncryptionConfiguration": {
      "Rules": [
        {
          "ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "aws:kms"},
          "BucketKeyEnabled": true
        }
      ]
    }
  },
  "ExistingLifecycle": {
    "Rules": [
      {
        "ID": "current-version-tier-to-ia",
        "Status": "Enabled",
        "Filter": {"Prefix": ""},
        "Transitions": [{"Days": 30, "StorageClass": "STANDARD_IA"}]
      },
      {
        "ID": "current-version-expire-365d",
        "Status": "Enabled",
        "Filter": {"Prefix": "temp/"},
        "Expiration": {"Days": 365}
      },
      {
        "ID": "abort-multipart-7d",
        "Status": "Enabled",
        "Filter": {"Prefix": ""},
        "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 7}
      }
    ]
  },
  "StorageLensSample": {
    "NoncurrentVersionCount": 540000,
    "NoncurrentVersionStorageBytes": 13500000000000
  },
  "IamPermissions": "Caller has s3:GetLifecycleConfiguration + s3:PutLifecycleConfiguration on the bucket"
}
```

## Skill output

```text
OPERATION: configure-lifecycle
VERDICT: READY
TARGET: s3://prod-logs-bucket
PRE_CHECKS:
  - [PASS] Bucket exists in us-east-1 account 111111111111
  - [PASS] Versioning Status: Enabled
  - [PASS] MFADelete: Disabled (no MFA required)
  - [PASS] ObjectLockEnabled: Disabled (no Compliance/Governance retention)
  - [PASS] Existing lifecycle rules captured (3 rules: current-version-
    tier-to-ia, current-version-expire-365d on temp/, abort-multipart-7d)
  - [PASS] New rules will be MERGED into existing config (read-merge-PUT
    pattern; never PUT-only)
  - [PASS] BucketKeyEnabled: true (no KMS optimization gap)
  - [PASS] Caller has s3:GetLifecycleConfiguration + s3:PutLifecycleConfiguration
STEPS:
  1. CONFIRM: About to put-bucket-lifecycle-configuration on
     s3://prod-logs-bucket in account 111111111111 region us-east-1.
     This will ADD a NoncurrentVersionExpiration (keep 3, expire rest)
     and NoncurrentVersionTransition (STANDARD_IA at 30d, GLACIER_IR
     at 90d) rule to the existing 3 rules. Existing rules PRESERVED.
     Estimated monthly savings: $312 -> $95/month (~70% reduction).
     Proceed? (yes/no)
  2. aws s3api put-bucket-lifecycle-configuration \
       --bucket prod-logs-bucket \
       --lifecycle-configuration file:///tmp/prod-logs-bucket-merged-lifecycle.json
  3. aws s3api get-bucket-lifecycle-configuration \
       --bucket prod-logs-bucket --output json
POST_VERIFY:
  - (pending execution)
ESTIMATED_SAVINGS: $312/month -> $95/month (Net savings: $217/month, ~70%)
  - 13.5 TB noncurrent versions × $0.023/GB-month = $312/month current
  - After cleanup: 3 kept versions × avg_size × Standard_30d
    + mid-aged × IA $0.0125 + old × GIR $0.004 + expired = ~$95/month
NOTES:
  - Lifecycle rules apply within 24 hours of eligibility. Allow 24-48
    hours for the first noncurrent versions to transition/expire.
  - The existing 3 rules (current-version-tier-to-ia,
    current-version-expire-365d, abort-multipart-7d) are PRESERVED in
    the merged config — verified by reading the post-PUT lifecycle
    configuration.
  - S3 Storage Lens will show NoncurrentVersionCount and
    NoncurrentVersionStorageBytes dropping over 1-2 weeks.
  - For immediate cleanup of versions already older than 90d, use
    S3 Batch Operations (separate operation, ~$0.54 for 540,000
    versions at $1.00/million).
  - The Bucket Key is already enabled — no KMS request cost reduction
    needed.
```

The merged lifecycle JSON (new rule appended to existing):

```json
{
  "Rules": [
    {
      "ID": "current-version-tier-to-ia",
      "Status": "Enabled",
      "Filter": {"Prefix": ""},
      "Transitions": [{"Days": 30, "StorageClass": "STANDARD_IA"}]
    },
    {
      "ID": "current-version-expire-365d",
      "Status": "Enabled",
      "Filter": {"Prefix": "temp/"},
      "Expiration": {"Days": 365}
    },
    {
      "ID": "abort-multipart-7d",
      "Status": "Enabled",
      "Filter": {"Prefix": ""},
      "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 7}
    },
    {
      "ID": "version-cleanup-3-rule",
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

## Contrast — BLOCKED case (Object Lock Compliance mode)

If the operator wanted to immediately delete 10,000 noncurrent versions
via Batch Operations on a Compliance-mode bucket, the pre-check gate
would fire and no CLI would execute:

```text
OPERATION: batch-delete-versions
VERDICT: BLOCKED
TARGET: s3://compliance-archive-bucket
PRE_CHECKS:
  - [PASS] Bucket exists in us-east-1 account 111111111111
  - [PASS] Versioning Status: Enabled
  - [PASS] Manifest generated (10,000 noncurrent versions from S3
    Inventory snapshot 2026-08-08)
  - [FAIL] ObjectLockEnabled: Enabled, DefaultRetention: Mode=COMPLIANCE,
    Years=5. The manifest contains 4,287 versions within the 5-year
    retention window. Compliance mode is irrevocable — NO ONE (including
    root, including AWS support) can delete these versions until
    2031-08-09.
  - [SKIP] Legal hold check skipped (Compliance retention already
    blocks deletion)
STEPS: (none — pre-checks failed)
POST_VERIFY: (none)
ESTIMATED_SAVINGS: $0 (Compliance retention overrides cleanup)
NOTES:
  - Compliance mode is irrevocable. No one can delete the in-retention
    versions until 2031-08-09.
  - Options:
    (a) Wait for retention to expire, then re-run Batch Operations.
    (b) Apply NoncurrentVersionTransition lifecycle rules — versions
        PAST retention will transition to IA/Glacier automatically.
        In-retention versions remain in Standard until retention
        expires, then transition.
    (c) For Governance-mode buckets (not this case), delete with
        s3:BypassGovernanceRetention permission.
  - Recommend: lifecycle NoncurrentVersionTransition (IA at 30d past
    retention, GIR at 90d past retention) as the only viable cleanup
    path for Compliance-mode buckets.
```

## What the skill caught that a generic assistant misses

1. **Read-merge-PUT pattern.** A generic assistant puts only the new
   rule, silently deleting the 3 existing rules. The skill captures
   existing rules first and merges the new rule into the config.

2. **Object Lock Compliance mode detection.** A generic assistant
   submits the Batch Operations job — which fails per-object on 4,287
   in-retention versions. The skill catches Compliance mode in pre-
   checks and BLOCKS with the lifecycle transition alternative.

3. **Per-object legal hold check.** A generic assistant skips the
   legal-hold sample. The skill samples the manifest and surfaces
   held objects before submission.

4. **Estimated savings with breakdown.** A generic assistant omits the
   savings calculation. The skill computes
   `NoncurrentVersionStorageBytes × Standard_rate` and the post-cleanup
   cost with IA/GIR transitions.

5. **Bucket Key recommendation.** A generic assistant omits the KMS
   cost optimization. The skill verifies `BucketKeyEnabled: true` and
   flags it as a finding if false.

6. **Glacier IR vs Flexible Retrieval choice.** A generic assistant
   picks the cheapest (Glacier Deep Archive). The skill recommends GIR
   for ms-latency GETs on noncurrent versions — the access pattern
   matters more than the absolute cheapest.

7. **Batch Operations cost transparency.** A generic assistant omits
   the per-million-object cost (~$1.00). The skill surfaces the cost
   ($0.54 for 540K versions, $2.50 for 2.5M versions) and contrasts
   with the monthly savings.

8. **CONFIRM gate.** A generic assistant auto-executes. The skill
   emits `CONFIRM:` and waits — lifecycle PUTs silently replace
   existing rules, Batch Operations deletes data irreversibly.

## Slash-command invocation

```
/aws:operate-s3-version-cleanup
```

Or via the orchestrator:

```
/aws:pipeline
You: "clean up noncurrent versions on prod-logs-bucket"
```

The orchestrator emits
`[Phase: Operate | Skills routed: s3-version-cleanup-operator]` and
hands off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "clean up S3 noncurrent versions on prod-logs-bucket"
# [Phase: Operate | Skills routed: s3-version-cleanup-operator]
```

## Live-account follow-up (optional, requires AWS CLI)

After applying the lifecycle config:

```bash
# Capture pre-state for rollback
aws s3api get-bucket-lifecycle-configuration --bucket prod-logs-bucket \
  --profile default --output json \
  > /tmp/prod-logs-bucket-lifecycle-pre-$(date +%s).json

# Merge the new rule into the existing config (manually or via jq)
# (see the skill output above for the merged JSON)
# Save as /tmp/prod-logs-bucket-merged-lifecycle.json

# PUT the merged config
aws s3api put-bucket-lifecycle-configuration \
  --bucket prod-logs-bucket \
  --lifecycle-configuration file:///tmp/prod-logs-bucket-merged-lifecycle.json \
  --profile default

# Verify the merged config (existing rules preserved + new rule added)
aws s3api get-bucket-lifecycle-configuration \
  --bucket prod-logs-bucket --profile default \
  --query 'Rules[].ID' --output table
# Expected: current-version-tier-to-ia
#           current-version-expire-365d
#           abort-multipart-7d
#           version-cleanup-3-rule

# Check Storage Lens after 48 hours
aws s3control get-storage-lens-group --account-id 111111111111 \
  --group-name default --profile default \
  --query 'StorageLensConfiguration.SelectionCriteria'

# Optional: immediate cleanup of versions already older than 90d via
# S3 Batch Operations (skip if lifecycle is sufficient)
aws s3control create-job \
  --account-id 111111111111 \
  --operation '{"S3DeleteObjectVersion": {}}' \
  --manifest '{"Spec": {"Format": "S3InventoryReports", "Bucket": "arn:aws:s3:::manifest-bucket", "Prefix": "prod-logs-inventory/2026-08-08/"}, "Location": {"ObjectArn": "arn:aws:s3:::manifest-bucket/prod-logs-inventory/2026-08-08/manifest.json"}}' \
  --report '{"Bucket":"arn:aws:s3:::batch-ops-reports","Prefix":"prod-logs-cleanup-2026-08-09/","Format":"Report_CSV_20180820","Enabled":true,"ReportScope":"AllTasks"}' \
  --priority 50 \
  --role-arn arn:aws:iam::111111111111:role/S3BatchOperationsDeleteRole \
  --client-request-token $(uuidgen) \
  --profile default
```
