# Example usage: kms-key-rotation-optimizer

A walkthrough showing the skill auditing an orphaned KMS key,
demonstrating the CloudTrail API call analysis, the resource association
verification, the IRREVERSIBLE deletion warning, and the grant cleanup
sequencing.

## Input (user prompt)

> Review our KMS keys before our Q3 FinOps review. We have a key from
> a legacy app that was decommissioned. Help me optimize the KMS cost.

```text
KeyId: arn:aws:kms:us-east-1:123456789012:key/legacy-data-key
Alias: alias/legacy-data-encryption
KeyState: Enabled
KeyManager: CUSTOMER
KeySpec: SYMMETRIC_DEFAULT
RotationStatus: Disabled
Grants: 3 active (all expired, grantee principals deleted)
MultiRegion: False
Region: us-east-1

CloudTrail (last 30 days):
  - Decrypt: 0 calls
  - Encrypt: 0 calls
  - GenerateDataKey: 0 calls

Resource associations:
  - S3 bucket default encryption: None referencing this key
  - EBS volumes: None referencing this key
  - RDS instances: None referencing this key
  - Secrets Manager: None referencing this key
```

## Skill output

```text
TARGET: alias/legacy-data-encryption
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Customer-managed key with 0 Decrypt, Encrypt, or
  GenerateDataKey calls in 30 days (CloudTrail lookup). No S3 bucket
  default encryption, no EBS volume, no RDS instance, no Secrets
  Manager secret references this key. 3 expired grants on deleted IAM
  roles. Rotation disabled. Orphaned key at $1/month with no active
  workload.
RECOMMENDATION:
  Current: 1 customer-managed key (Enabled), rotation Disabled,
    3 expired grants, 0 API calls/30 days
  Proposed: 0 keys (scheduled deletion), grants retired, rotation
    enabled before deletion for compliance audit trail
  Dimensions changed: inventory (delete) + grants (retire) + rotation
    (enable for audit trail) + deletion (schedule 7-day window)
  Dimensions checked: inventory → (delete)  rotation → (enable first)
    grants → (retire 3)  aliases ✓ (exists)  cross_account ✓ (none)
    multi_region ✓ (single region)  deletion → (7-day window)
  Confidence: HIGH — CloudTrail confirms zero API activity for 30 days;
    resource association audit found no encrypted resources.
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
  2. Enable rotation for audit trail completeness:
     aws kms enable-key-rotation --key-id <key-id>
  3. Verify no encrypted resources depend on this key:
     aws s3api list-buckets --query 'Buckets[?DefaultEncryption]'
     aws ec2 describe-volumes --query 'Volumes[?KmsKeyId==`<key-id>`]'
  4. Schedule key deletion (7-day window):
     aws kms schedule-key-deletion --key-id <key-id> --pending-window-in-days 7
  5. Document deletion in change management system.
CONFIRM: About to retire 3 grants, enable rotation, and schedule
  deletion of alias/legacy-data-encryption (7-day window). Monthly
  saving $1.00 ($12.00/year). Key deletion is IRREVERSIBLE — data
  encrypted under this key will be permanently unrecoverable.
  Proceed? (yes/no)
```

## What the skill caught that a generic assistant misses

1. **IRREVERSIBLE deletion warning.** A generic assistant says "just
   delete it." The skill emphasizes that KMS key deletion is
   IRREVERSIBLE and that data encrypted under the key is permanently
   lost — the most dangerous operation in KMS optimization.

2. **Resource association verification.** The skill checks S3, EBS,
   RDS, Secrets Manager, and Lambda encryption configs before
   recommending deletion. A generic assistant skips this verification.

3. **Grant retirement before deletion.** The skill retires expired
   grants FIRST, then schedules deletion. A generic assistant goes
   straight to `schedule-key-deletion` without cleaning up grants.

4. **Rotation enablement for audit trail.** The skill enables rotation
   before scheduling deletion so the compliance audit trail shows the
   key was in a compliant state at time of deletion. A generic assistant
   skips this step.

5. **7-day minimum deletion window.** The skill uses the 7-day minimum
   window (not the 30-day default) to minimize billing during the
   pending deletion period. A generic assistant uses the default.

6. **Seven-dimension check.** The skill explicitly checks all seven
   dimensions (inventory, rotation, grants, aliases, cross-account,
   multi-region, deletion) and marks each as checked or finding. A
   generic assistant focuses only on the key itself.

## Slash-command invocation

```
/aws:optimize-kms-key-rotation
```

Or via the orchestrator:

```
/aws:pipeline
You: "optimize our KMS keys for the Q3 FinOps review"
```

The orchestrator emits
`[Phase: Optimize | Skills routed: kms-key-rotation-optimizer]` and hands
off to this skill for the optimization block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate that the key entered PendingDeletion:

```bash
aws kms describe-key --key-id <key-id> --query 'KeyMetadata.[KeyState,DeletionDate]'
```

If any encrypted resource is discovered during the 7-day window, cancel
deletion immediately:

```bash
aws kms cancel-key-deletion --key-id <key-id>
```

## Fleet-wide extension

For a fleet of N KMS keys, run the skill in batch mode:

1. Pull all keys with `aws kms list-keys`.
2. Filter to customer-managed keys (`KeyManager == CUSTOMER`).
3. For each key, CloudTrail lookup-events for Decrypt, Encrypt,
   GenerateDataKey (30 days).
4. Filter to keys with 0 API calls (orphaned key candidates).
5. For each candidate, check S3, EBS, RDS, Secrets Manager, Lambda
   encryption configs.
6. Sort by total monthly cost (key + API calls + replicas).
7. Slice into batches of 5 keys.
8. For each batch: emit per-key REMEDIATION_STEPS, then a single
   CONFIRM for the batch.
9. Verify each batch before proceeding to the next.
