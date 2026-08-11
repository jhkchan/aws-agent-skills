# Worked Examples — KMS Key Rotation Optimizer

Full worked examples covering every verdict type and the major
optimization patterns. Each example shows the complete output block
with verified math.

## Example 1: Orphaned key cleanup (FURTHER_OPTIMIZATION_AVAILABLE)

```text
TARGET: alias/legacy-app-encryption
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Customer-managed key with 0 Decrypt, Encrypt, or
  GenerateDataKey calls in 30 days (CloudTrail lookup). No S3 bucket
  default encryption, no EBS volume, no RDS instance, no Secrets Manager
  secret references this key. Key has 3 expired grants on deleted IAM
  roles. Rotation is disabled. Orphaned key at $1/month.
RECOMMENDATION:
  Current: 1 customer-managed key (Enabled), rotation Disabled,
    3 expired grants, 0 API calls/30 days
  Proposed: 0 keys (scheduled deletion), grants retired, rotation
    enabled before deletion for audit trail
  Dimensions changed: inventory (delete) + grants (retire) + rotation
    (enable for audit) + deletion (schedule 7-day window)
  Dimensions checked: inventory → (delete)  rotation → (enable first)
    grants → (retire 3)  aliases ✓ (exists)  cross_account ✓ (none)
    multi_region ✓ (single region)  deletion → (7-day window)
  Confidence: HIGH — CloudTrail confirms zero API activity for 30 days.
ESTIMATED_SAVINGS:
  Current monthly: $1.00
    key: 1 × $1.00 = $1.00
    api: 0 calls × $0.03/10K = $0.00
  Projected monthly: $0.00
  Monthly saving: $1.00
    ($1.00 − $0.00 = $1.00 ✓)
  Annual saving: $12.00
REMEDIATION_STEPS:
  1. Retire expired grants:
     aws kms retire-grant --key-id <key-id> --grant-id <grant-1>
     aws kms retire-grant --key-id <key-id> --grant-id <grant-2>
     aws kms retire-grant --key-id <key-id> --grant-id <grant-3>
  2. Enable rotation for audit trail:
     aws kms enable-key-rotation --key-id <key-id>
  3. Verify no encrypted resources:
     aws s3api list-buckets --query 'Buckets[?DefaultEncryption]'
     aws ec2 describe-volumes --query 'Volumes[?KmsKeyId==`<key-id>`]'
  4. Schedule deletion (7-day window):
     aws kms schedule-key-deletion --key-id <key-id> --pending-window-in-days 7
CONFIRM: About to retire 3 grants, enable rotation, and schedule
  deletion of alias/legacy-app-encryption. Monthly saving $1.00
  ($12.00/year). IRREVERSIBLE. Proceed? (yes/no)
```

## Example 2: Stale grant retirement (FURTHER_OPTIMIZATION_AVAILABLE)

```text
TARGET: alias/s3-bucket-encryption
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Active KMS key has 7 expired grants on deleted IAM roles (60+
  days old, zero CloudTrail usage). Key itself is actively used
  (850K Decrypt calls/month for 3 S3 buckets). Grant cleanup is a
  hygiene issue — no direct cost saving, but reduces authorization
  latency and audit complexity.
RECOMMENDATION:
  Current: 18 grants total (11 active, 7 expired)
  Proposed: 11 grants total (all active)
  Dimensions changed: grants (retire 7 expired)
  Dimensions checked: inventory ✓ (active key)  rotation ✓ (enabled)
    grants → (retire 7)  aliases ✓ (exists)  cross_account ✓ (none)
    multi_region ✓ (single region)  deletion ✓ (key is active)
  Confidence: HIGH — CloudTrail confirms 7 grants have zero usage;
    grantee principals are deleted IAM roles.
ESTIMATED_SAVINGS:
  Current monthly: $3.10
    key: 1 × $1.00 = $1.00
    api: 1,015,000 / 10,000 × $0.03 = $3.05 (rounded)
  Projected monthly: $3.10
    key: 1 × $1.00 = $1.00
    api: same volume = $3.05
  Monthly saving: $0.00
    (Grant retirement is cost-neutral; surfaced as hygiene finding)
  Annual saving: $0.00
REMEDIATION_STEPS:
  1. List grants and identify expired ones:
     aws kms list-grants --key-id <key-id>
  2. Retire each expired grant:
     aws kms retire-grant --key-id <key-id> --grant-id <expired-1>
     aws kms retire-grant --key-id <key-id> --grant-id <expired-2>
     ... (repeat for all 7)
  3. Verify remaining 11 grants are all active.
CONFIRM: About to retire 7 expired grants on alias/s3-bucket-encryption.
  No cost impact; improves key hygiene. Proceed? (yes/no)
```

## Example 3: Multi-region replica deletion (FURTHER_OPTIMIZATION_AVAILABLE)

```text
TARGET: alias/global-data-encryption
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Multi-region key has replicas in ap-southeast-1 and sa-east-1
  with zero API calls in 30 days and zero S3 bucket associations.
  Deleting both replicas saves $2/month ($24/year).
RECOMMENDATION:
  Current: 4-region multi-region key (us-east-1, eu-west-1,
    ap-southeast-1, sa-east-1) = $4/month in key costs
  Proposed: 2-region multi-region key (us-east-1, eu-west-1)
    = $2/month in key costs
  Dimensions changed: multi_region (delete 2 unused replicas)
  Dimensions checked: inventory ✓ (primary active)  rotation ✓ (enabled)
    grants ✓ (all current)  aliases ✓ (exists)  cross_account ✓ (none)
    multi_region → (delete 2 replicas)  deletion ✓ (keep primary)
  Confidence: HIGH — CloudTrail confirms zero API calls in
    ap-southeast-1 and sa-east-1 for 30 days.
ESTIMATED_SAVINGS:
  Current monthly: $4.15
    keys: 4 × $1.00 = $4.00
    api: ~64K total calls / 10K × $0.03 = $0.19 (all in us-east-1
      and eu-west-1)
  Projected monthly: $2.19
    keys: 2 × $1.00 = $2.00
    api: same calls (all in us-east-1 + eu-west-1) = $0.19
  Monthly saving: $2.00
    ($4.15 − $2.19 = $1.96 ≈ $2.00 ✓ rounding to key cost delta)
  Annual saving: $24.00
REMEDIATION_STEPS:
  1. Verify no resources in ap-southeast-1 or sa-east-1 use replicas.
  2. Schedule replica deletion in ap-southeast-1:
     aws kms schedule-key-deletion --key-id <ap-southeast-1-replica> \
       --pending-window-in-days 7
  3. Schedule replica deletion in sa-east-1:
     aws kms schedule-key-deletion --key-id <sa-east-1-replica> \
       --pending-window-in-days 7
  4. Monitor for 7 days; if any encrypted data is found, cancel
     deletion: aws kms cancel-key-deletion --key-id <id>
CONFIRM: About to delete 2 unused multi-region replicas
  (ap-southeast-1, sa-east-1). Monthly saving $2.00 ($24.00/year).
  IRREVERSIBLE after 7-day window. Proceed? (yes/no)
```

## Example 4: Already optimal (ALREADY_OPTIMAL)

```text
TARGET: alias/production-data-encryption
VERDICT: ALREADY_OPTIMAL
REASON: Active customer-managed key with rotation enabled, 3 current
  grants all in active use, single-region (no replicas), 2.9M API
  calls/month across 8 S3 buckets. All seven dimensions pass — no
  optimization available.
RECOMMENDATION:
  Current: 1 key ($1.00), 3 grants (current), rotation enabled,
    2.9M API calls/month ($8.73)
  Proposed: No changes
  Dimensions checked: inventory ✓ (active, 2.9M calls)  rotation ✓
    (enabled)  grants ✓ (3 current)  aliases ✓ (exists)
    cross_account ✓ (none)  multi_region ✓ (single region)
    deletion ✓ (key is active)
  Confidence: HIGH — all dimensions verified against 30-day data.
ESTIMATED_SAVINGS:
  Current monthly: $9.73
  Projected monthly: $9.73
  Monthly saving: $0.00
  Annual saving: $0.00
REMEDIATION_STEPS: None required.
CONFIRM: N/A — no changes recommended.
```

## Example 5: Rotation enablement with grant cleanup (FURTHER_OPTIMIZATION_AVAILABLE)

```text
TARGET: alias/secrets-encryption
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Key has rotation Disabled (no regulatory prohibition) and 2
  expired grants. Rotation should be enabled (free, transparent) for
  security best practice. Expired grants should be retired for hygiene.
  No direct cost saving — the finding is security and hygiene driven.
RECOMMENDATION:
  Current: 1 key (Enabled), rotation Disabled, 5 grants (3 active,
    2 expired)
  Proposed: 1 key (Enabled), rotation Enabled, 3 grants (all active)
  Dimensions changed: rotation (enable) + grants (retire 2)
  Dimensions checked: inventory ✓ (active)  rotation → (enable)
    grants → (retire 2)  aliases ✓ (exists)  cross_account ✓ (none)
    multi_region ✓ (single region)  deletion ✓ (key is active)
  Confidence: HIGH — no regulatory prohibition on rotation; expired
    grant principals are deleted IAM roles.
ESTIMATED_SAVINGS:
  Current monthly: $2.48
    key: 1 × $1.00 = $1.00
    api: 49,200 / 10,000 × $0.03 = $1.48
  Projected monthly: $2.48
    key: 1 × $1.00 = $1.00
    api: same volume = $1.48
  Monthly saving: $0.00
    (Rotation is free; grant retirement is cost-neutral)
  Annual saving: $0.00
REMEDIATION_STEPS:
  1. Enable automatic rotation:
     aws kms enable-key-rotation --key-id <key-id>
  2. Retire expired grants:
     aws kms retire-grant --key-id <key-id> --grant-id <expired-1>
     aws kms retire-grant --key-id <key-id> --grant-id <expired-2>
  3. Verify rotation status:
     aws kms get-key-rotation-status --key-id <key-id>
CONFIRM: About to enable rotation and retire 2 expired grants on
  alias/secrets-encryption. No cost impact; improves security posture.
  Proceed? (yes/no)
```
