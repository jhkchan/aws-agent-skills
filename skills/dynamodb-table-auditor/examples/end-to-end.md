# End-to-end usage scenario: dynamodb-table-auditor

A walkthrough showing the skill auditing a DynamoDB table that has BOTH
SSE disabled (UNENCRYPTED) and PITR disabled (NO_PITR), demonstrating
worst-first verdict aggregation, the "UNENCRYPTED does not mean plaintext"
concept, and the ordered classification workflow.

## Input (user prompt)

> Audit this DynamoDB table before we promote it to production. It stores
> user session data and we need it compliant for our SOC2 review.

```yaml
Table name: unencrypted-and-no-pitr-worst-first
Table ARN: arn:aws:dynamodb:us-east-1:111111111111:table/unencrypted-and-no-pitr-worst-first
Table configuration (describe-table):
  TableStatus: ACTIVE
  BillingModeSummary:
    BillingMode: PAY_PER_REQUEST
  SSEDescription:
    Status: DISABLED
    SSEType: AES256
  GlobalSecondaryIndexes: []
  LocalSecondaryIndexes: []
  DeletionProtectionEnabled: false
  StreamSpecification:
    StreamEnabled: false
  TableSizeBytes: 268435456
Continuous backups (describe-continuous-backups):
  ContinuousBackupsStatus: DISABLED
TTL (describe-time-to-live):
  TimeToLiveDescription:
    TimeToLiveStatus: DISABLED
```

## Skill output

```text
TABLE: unencrypted-and-no-pitr-worst-first
VERDICT: UNENCRYPTED
REASON: SSEDescription shows SSEType AES256 with Status DISABLED — the table
uses DynamoDB's default AWS-owned-key encryption with no customer KMS
visibility, no CloudTrail Decrypt logging, and no key policy control (Step 1).
PITR is also disabled, but UNENCRYPTED takes priority as the worst verdict.
FINDINGS:
  - [UNENCRYPTED] SSE disabled (SSEType: AES256, Status: DISABLED) — no
    customer-controlled KMS encryption; zero audit traceability for SOC2
    compliance evidence (Step 1)
  - [NO_PITR] ContinuousBackupsStatus: DISABLED — no 35-day recovery window;
    accidental writes or deletes are unrecoverable (Step 2)
  - [CONFIG_GAP] DeletionProtectionEnabled: false — table can be deleted
    accidentally or by ransomware (Step 4)
  - [CONFIG_GAP] StreamSpecification absent — no CDC pipeline for audit or
    recovery (Step 4)
  - [CONFIG_GAP] TTL disabled — no automatic item expiry; cost and compliance
    risk for session data (Step 4)
  - [OK] BillingMode: PAY_PER_REQUEST — on-demand handles traffic without
    capacity planning (Step 3)
REMEDIATION:
  1. UNENCRYPTED — Enable SSE-KMS with a customer-managed CMK:
     aws dynamodb update-table --table-name unencrypted-and-no-pitr-worst-first \
       --sse-specification Enabled=true,SSEType=KMS,\
KMSMasterKeyId=arn:aws:kms:us-east-1:111111111111:key/<cmk-id>
     Monitor SSEDescription.Status: DISABLED → ENABLING → ENABLED.
  2. NO_PITR — Enable point-in-time recovery:
     aws dynamodb update-continuous-backups \
       --table-name unencrypted-and-no-pitr-worst-first \
       --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true
  3. CONFIG_GAP — Enable deletion protection:
     aws dynamodb update-table --table-name unencrypted-and-no-pitr-worst-first \
       --deletion-protection-enabled
  4. CONFIG_GAP — Enable streams for CDC:
     aws dynamodb update-table --table-name unencrypted-and-no-pitr-worst-first \
       --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES
  5. CONFIG_GAP — Enable TTL on a session-expiry attribute:
     aws dynamodb update-time-to-live \
       --table-name unencrypted-and-no-pitr-worst-first \
       --time-to-live-specification Enabled=true,AttributeName=session_ttl
```

## What the skill caught that a generic assistant misses

1. **"UNENCRYPTED" does not mean plaintext.** A generic assistant says "your
   table is not encrypted." The skill explains that every DynamoDB table IS
   encrypted at rest — the verdict UNENCRYPTED means there is no customer-
   controlled KMS encryption, which means zero CloudTrail Decrypt visibility
   and no key policy. For SOC2 evidence, the distinction is critical: the
   auditor needs to show customer-controlled encryption, not just "encrypted."

2. **PITR and AWS Backup are different.** A generic assistant might say
   "enable backups." The skill is explicit: PITR provides 35-day continuous
   replay; AWS Backup takes scheduled snapshots. They are complementary, not
   substitutive. A table with AWS Backup but no PITR still loses data between
   snapshots.

3. **Worst-first aggregation with full findings list.** The verdict is
   UNENCRYPTED (the worst finding), but the FINDINGS list shows all five
   findings across all dimensions. The operator can triage each finding
   independently — the capacity mode is already OK (on-demand), so the
   remediation plan focuses on encryption, recovery, and config hardening.

4. **The SSE migration is a background operation.** A generic assistant says
   "enable encryption" without noting that DynamoDB re-encrypts all existing
   data asynchronously — the operator should monitor the Status transitions
   (DISABLED → ENABLING → ENABLED) and not panic when the table isn't instantly
   encrypted.

## Slash-command invocation

```
/aws:audit-dynamodb-table
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit this DynamoDB table before production"
```

The orchestrator emits
`[Phase: Audit | Skills routed: dynamodb-table-auditor]` and hands off
to this skill for the VERDICT.

## Live-account follow-up (optional, requires AWS CLI)

After remediating the findings, validate the table posture:

```bash
# Verify SSE-KMS is now ENABLED with the customer CMK
aws dynamodb describe-table \
  --table-name unencrypted-and-no-pitr-worst-first \
  --profile default --output json | jq '.Table.SSEDescription'

# Confirm PITR is active
aws dynamodb describe-continuous-backups \
  --table-name unencrypted-and-no-pitr-worst-first \
  --profile default | jq '.ContinuousBackupsDescription'

# Verify deletion protection is on
aws dynamodb describe-table \
  --table-name unencrypted-and-no-pitr-worst-first \
  --profile default --output json | jq '.Table.DeletionProtectionEnabled'
```

Then monitor CloudTrail for `dynamodb:UpdateTable` events confirming the SSE
migration completed successfully.
