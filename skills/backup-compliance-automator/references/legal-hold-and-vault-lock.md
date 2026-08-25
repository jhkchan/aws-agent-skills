# Legal Hold and Vault Lock — Reference

This reference details the two Backup immutability mechanisms (BackupLegalHold
and Backup Vault Lock), their differences, and end-to-end automation patterns
for litigation hold workflows. Use alongside the Backup Compliance Automator
SKILL.md.

## Mechanism comparison

| Dimension | BackupLegalHold | Vault Lock (GOVERNANCE) | Vault Lock (LOCK_MODE) |
|---|---|---|---|
| Scope | Specific recovery points | All recovery points in vault | All recovery points in vault |
| Duration | Until hold released | Forever (until policy removed) | Forever (irreversible) |
| Override | No (cannot override hold) | Yes (root + `s3:PutBucketObjectLock`) | No (no one can override) |
| Use case | Litigation-driven freeze | Policy immutability (team guardrail) | Compliance immutability (HIPAA, SOC2) |
| Reversible | Yes (status -> INACTIVE) | Yes (within cool-down) | No |

## BackupLegalHold lifecycle

```bash
# 1. Create a hold
HOLD_ARN=$(aws backup create-legal-hold \
  --title "Acme v. Example - Case #2026-CV-1234" \
  --description "Litigation hold on EBS volumes" \
  --legal-hold-status ACTIVE \
  --recovery-point-selection '{
    "ResourceIdentifiers":["arn:aws:ec2:us-east-1::volume/vol-0abc"],
    "DateRange":{"FromDate":"2026-08-01","ToDate":"2026-08-05"}
  }' --query 'LegalHold.LegalHoldArn' --output text)

# 2. Verify held recovery points
aws backup list-recovery-points-by-legal-hold \
  --legal-hold-id <hold-id>

# 3. Release (when litigation closes)
aws backup delete-legal-hold \
  --legal-hold-id <hold-id> \
  --cancel-description "Case settled 2026-09-15"
```

**Lifecycle rules:**
- Held recovery points do NOT age out per the vault lifecycle.
- Release does NOT delete the recovery point — it returns to lifecycle
  control and ages out naturally.
- The cancel description is part of the audit trail; include the case ID
  and closure date.

## Vault Lock modes

### GOVERNANCE mode
- Root user with `s3:PutBucketObjectLock` privilege can override.
- Useful for preventing accidental deletion by team members while keeping
  a break-glass override.

### COMPLIANCE mode (LOCK_MODE)
- No one — including root — can override once the `changeable-for-days`
  cool-down passes.
- Required for HIPAA, SOC2, PCI, FedRAMP.

```bash
# Configure LOCK_MODE (compliance mode) on a vault
aws backup put-backup-vault-lock-configuration \
  --backup-vault-name production-vault \
  --min-retention-days 7 \
  --max-retention-days 365 \
  --changeable-for-days 3 \
  --mode LOCK_MODE
```

**The `changeable-for-days` cool-down:** During this window, the lock
configuration can still be modified or removed. After the cool-down,
LOCK_MODE is irreversible. Use this window to verify the configuration
before committing.

## End-to-end litigation hold workflow

### Step 1: Trigger from the legal team

The legal team sends a custom event (via API Gateway, custom SaaS, or
manual CLI):

```bash
aws events put-events --entries '[
  {
    "Source":"custom.legal",
    "DetailType":"Litigation Hold Request",
    "Detail":"{\"caseName\":\"Acme v. Example #2026-CV-1234\",\"caseDescription\":\"Patent dispute\",\"resourceArns\":[\"arn:aws:ec2:us-east-1::volume/vol-0abc\"],\"incidentDateStart\":\"2026-08-01\",\"incidentDateEnd\":\"2026-08-05\"}"
  }
]'
```

### Step 2: EventBridge rule routes to Lambda

```bash
aws events put-rule --name trigger-litigation-hold \
  --event-pattern '{"source":["custom.legal"],"detail-type":["Litigation Hold Request"]}' \
  --state ENABLED

aws events put-targets --rule trigger-litigation-hold \
  --targets '[{"Id":"HoldResponder","Arn":"arn:aws:lambda:us-east-1:111111111111:function:create-legal-hold","DeadLetterConfig":{"Arn":"arn:aws:sqs:us-east-1:111111111111:legal-hold-dlq"}}]'
```

### Step 3: Lambda creates the hold

```python
import boto3, json
backup = boto3.client('backup')

def lambda_handler(event, context):
    detail = json.loads(event['detail'])
    response = backup.create_legal_hold(
        Title=detail['caseName'],
        Description=detail['caseDescription'],
        LegalHoldStatus='ACTIVE',
        RecoveryPointSelection={
            'ResourceIdentifiers': detail['resourceArns'],
            'DateRange': {
                'FromDate': detail['incidentDateStart'],
                'ToDate': detail['incidentDateEnd']
            }
        }
    )
    # Notify the legal team (SNS email or Slack)
    sns = boto3.client('sns')
    sns.publish(
        TopicArn='arn:aws:sns:us-east-1:111111111111:legal-hold-notifications',
        Subject=f"Legal hold created: {detail['caseName']}",
        Message=json.dumps({
            'case': detail['caseName'],
            'hold_arn': response['LegalHold']['LegalHoldArn'],
            'resources': detail['resourceArns']
        }, indent=2)
    )
    return {'statusCode': 200, 'hold_arn': response['LegalHold']['LegalHoldArn']}
```

### Step 4: Test the workflow quarterly

```bash
# Create a test hold on a non-production recovery point
TEST_HOLD_ARN=$(aws backup create-legal-hold \
  --title "TEST - Legal hold workflow - $(date +%Y%m%d)" \
  --description "Quarterly test of litigation hold automation" \
  --legal-hold-status ACTIVE \
  --recovery-point-selection '{"ResourceIdentifiers":["arn:aws:ec2:us-east-1::volume/vol-test"]}' \
  --query 'LegalHold.LegalHoldArn' --output text)

# Verify the recovery point is now held
aws backup get-legal-hold --legal-hold-id <hold-id>

# Release
aws backup delete-legal-hold \
  --legal-hold-id <hold-id> \
  --cancel-description "Test completed - restoring normal lifecycle"
```

## eDiscovery with Backup Search

For eDiscovery, use Backup Search to find matching recovery points, then
apply legal hold:

```bash
# Search across backups for content matching the case
SEARCH_ID=$(aws backup search start-search-job \
  --search-scope '{
    "BackupVaultNames":["production-vault"],
    "ResourceTypes":["S3","DynamoDB"]
  }' \
  --search-term "acme-patent-dispute" \
  --query 'SearchJobId' --output text)

# Wait for search to complete, then iterate results and create holds
aws backup search describe-search-job --search-job-id $SEARCH_ID
```

Then iterate the search results (exported to S3), batch-create legal holds
on each matching recovery point.

## Common pitfalls

- **GOVERNANCE mode is not compliance-grade.** A regulator will ask "can
  root override retention?" — GOVERNANCE yes, LOCK_MODE no. Match the mode
  to the framework requirement.
- **Held recovery points accumulate cost.** A long-running litigation may
  hold many recovery points past their normal lifecycle — budget for the
  over-retention.
- **The cancel description is the audit trail.** Vague descriptions
  ("closed") fail audit. Always include the case ID and closure reason.
- **Legal hold conflicts with Vault Lock max-retention.** A vault with
  max-retention 365 days cannot hold a recovery point older than 365 days
  via Vault Lock alone — use BackupLegalHold for older points.
- **Search scope determines eDiscovery cost.** A broad search across years
  of backups is expensive. Scope tightly per the case.

## EventBridge-triggered litigation hold

```bash
# Trigger legal hold on a custom event (e.g., from the legal team)
aws events put-rule --name trigger-litigation-hold \
  --event-pattern '{"source":["custom.legal"],"detail-type":["Litigation Hold Request"]}' \
  --state ENABLED

aws events put-targets --rule trigger-litigation-hold \
  --targets '[{"Id":"HoldResponder","Arn":"arn:aws:lambda:us-east-1:111111111111:function:create-legal-hold"}]'
```

**Lambda responder (excerpt):**

```python
import boto3, os
backup = boto3.client('backup')

def lambda_handler(event, context):
    detail = event['detail']
    backup.create_legal_hold(
        Title=detail['caseName'],
        Description=detail['caseDescription'],
        LegalHoldStatus='ACTIVE',
        RecoveryPointSelection={
            'ResourceIdentifiers': detail['resourceArns'],
            'DateRange': {
                'FromDate': detail['incidentDateStart'],
                'ToDate': detail['incidentDateEnd']
            }
        }
    )
    return {'statusCode': 200, 'hold': 'created'}
```

**Gotchas:** Legal holds cannot be bypassed — even the root account
cannot delete a held recovery point. Always include the case ID in the
hold title for traceability. Test release (status -> INACTIVE) before
needing it under court deadline pressure.
