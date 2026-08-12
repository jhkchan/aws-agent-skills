# End-to-end usage scenario: iam-key-rotation-automator

A walkthrough showing the skill designing rotation pipelines for two
IAM users in the same account: an AUTOMATION_DEPLOYED standard 90-day
rotation with overlap window and a REVIEW_REQUIRED break-glass account
that refuses auto-rotation.

## Input (user prompt)

> Design key rotation automation for our IAM users. We have a
> deployment user with a key at 91 days and a break-glass admin
> account with a key at 365 days. We want both rotated automatically.

```
Design reference: prod-key-rotation-rollout
Account: 111111111111
Region: us-east-1

User 1: deployment-user
  Key: AKIAXYZ123 (Active)
  Created: 91 days ago
  Last used: 2 hours ago (S3, CloudFormation)
  Slots: 1 of 2 used
  Exception: No

User 2: break-glass-admin
  Key: AKIABREAK789 (Active)
  Created: 365 days ago
  Last used: 45 days ago (during Sev-1 incident)
  Exception: Yes (break-glass, owner: security-team)

SNS topic: arn:aws:sns:us-east-1:111111111111:key-rotation-alerts
```

## Skill output

```text
ROTATION: prod-key-rotation-rollout
USER: deployment-user
KEY: AKIAXYZ123
CLASSIFICATION:
  - Age: 91 days
  - Last used: 2 hours ago (S3, CloudFormation per access advisor)
  - Status: Active
  - Exception: No
DETECTION:
  - Credential report: generated today
  - Access advisor: last used 2 hours ago
  - EventBridge scan: rate(1 day) — flagged for rotation
ROTATION_FLOW:
  - Create: Lambda creates new key in slot 2, stores in Secrets Manager
  - Verify: Lambda verifies via STS get-caller-identity
  - Deactivate: Old key after 7-day overlap + 24h confirmed inactivity
  - Delete: Old key 3 days after deactivation (Day 10)
OVERLAP:
  - Window: 7 days active overlap + 3 days inactive monitoring (10 days total)
  - Day 0: new key created, app config updated via Secrets Manager
  - Day 1-7: both keys active, daily access advisor monitoring
  - Day 7: old key deactivated (if not used in 24h)
  - Day 10: old key deleted
NOTIFICATION:
  - SNS topic: arn:aws:sns:us-east-1:111111111111:key-rotation-alerts
  - Timeline: 7-day-warning, 1-day-warning, create, deactivate, delete
EXCEPTIONS:
  - Break-glass list: /iam-key-rotation/exceptions
  - User excepted: No
AUDIT:
  - CloudTrail: iam.amazonaws.com CreateAccessKey, UpdateAccessKey, DeleteAccessKey tracking
  - Credential report: weekly generation
VERDICT: AUTOMATION_DEPLOYED
GAP: None
TEMPLATE:
  aws events put-rule --name iam-key-rotation-daily --schedule-expression "rate(1 day)" --state ENABLED

ROTATION: prod-key-rotation-rollout
USER: break-glass-admin
KEY: AKIABREAK789
CLASSIFICATION:
  - Age: 365 days
  - Last used: 45 days ago (STS, IAM during Sev-1 incident)
  - Status: Active
  - Exception: Yes (Emergency access, owner: security-team)
DETECTION:
  - Credential report: generated today
  - Access advisor: last used 45 days ago
  - EventBridge scan: flagged but SKIPPED (exception list)
ROTATION_FLOW:
  - N/A — break-glass exception. Auto-rotation refused.
OVERLAP: N/A
NOTIFICATION:
  - SNS topic: exception review notice sent to security-team
  - Message: "break-glass-admin key is 365 days old. Manual review required."
EXCEPTIONS:
  - Break-glass list: /iam-key-rotation/exceptions
  - User excepted: Yes (reason: Emergency access, owner: security-team, review_date: 2026-11-01)
AUDIT:
  - CloudTrail: iam.amazonaws.com event tracking
VERDICT: REVIEW_REQUIRED
GAP: Break-glass account on exception list. Auto-rotation refused. Required: (1) Manual review by security-team; (2) evaluate whether break-glass access can use STS assume-role with MFA enforcement instead of a permanent key; (3) if permanent key is still required, manually rotate and update the break-glass procedure documentation; (4) distribute new key via KMS-encrypted SSM Parameter Store; (5) set review date for re-evaluation. The key was last used 45 days ago during a Sev-1 incident — do NOT rotate without confirming the incident is resolved and no active response is using this key.
TEMPLATE: (manual rotation — break-glass accounts require human approval from security-team)
```

**Account-level aggregate verdict: AUTOMATION_DEPLOYED for
deployment-user + REVIEW_REQUIRED for break-glass-admin.** The
deployment-user rotation can proceed immediately via the automated
pipeline. The break-glass-admin key requires manual review and
security-team approval.

## What the skill caught that a generic assistant misses

1. **The break-glass refusal.** A generic assistant rotates both keys
   the same way. The skill refuses to auto-rotate the break-glass key,
   citing the exception list and requiring manual review. Rotating a
   break-glass key during an active incident could lock out the
   responder.

2. **The overlap window design.** A generic assistant says "create
   new, delete old." The skill specifies a 10-day rotation lifecycle:
   7 days active overlap, 24h inactivity check, then deactivation, 3
   more days of monitoring, then deletion. Each phase has explicit
   verification gates.

3. **The access advisor integration.** A generic assistant does not
   check last-used before deactivation. The skill requires 24 hours of
   confirmed inactivity (via `get-access-key-last-used`) before
   deactivating the old key.

4. **The STS migration recommendation.** A generic assistant does not
   suggest eliminating the key. The skill recommends evaluating STS
   assume-role with MFA for the break-glass account — a permanent fix
   that eliminates the rotation burden entirely.

5. **The exception review date.** A generic assistant does not track
   exception lifecycles. The skill flags the review_date and ensures
   exceptions are re-evaluated periodically.

## Slash-command invocation

```
/aws:automate-iam-key-rotation
```

## CLI routing

```bash
node cli/bin/cli.js route "automate IAM key rotation"
# [Phase: Automate | Skills routed: iam-key-rotation-automator]
```

## Live-account invocation (requires AWS CLI)

```bash
# List all IAM users
aws iam list-users --query 'Users[].UserName' --output text \
  --region us-east-1 --profile default

# List access keys for each user with age and last-used
for user in $(aws iam list-users --query 'Users[].UserName' --output text --region us-east-1); do
  echo "=== $user ==="
  for key in $(aws iam list-access-keys --user-name "$user" --query 'AccessKeyMetadata[].AccessKeyId' --output text 2>/dev/null); do
    created=$(aws iam list-access-keys --user-name "$user" --query "AccessKeyMetadata[?AccessKeyId=='$key'].CreateDate" --output text)
    status=$(aws iam list-access-keys --user-name "$user" --query "AccessKeyMetadata[?AccessKeyId=='$key'].Status" --output text)
    last_used=$(aws iam get-access-key-last-used --access-key-id "$key" --query 'AccessKeyLastUsed.LastUsedDate' --output text 2>/dev/null)
    echo "  Key: $key | Status: $status | Created: $created | LastUsed: $last_used"
  done
done

# Check exception list
aws ssm get-parameter --name /iam-key-rotation/exceptions \
  --query 'Parameter.Value' --output text --region us-east-1 --profile default

# Generate fresh credential report
aws iam generate-credential-report --profile default
aws iam get-credential-report --query 'Content' --output text --profile default | base64 -d | column -t -s,

# CloudTrail audit of key API calls
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventSource,AttributeValue=iam.amazonaws.com \
  --start-time $(date -v-1d +%Y-%m-%dT%H:%M:%S) \
  --query 'Events[?EventName==`CreateAccessKey`||EventName==`DeleteAccessKey`||EventName==`UpdateAccessKey`].{Time:EventTime,Name:EventName,User:Username}' \
  --region us-east-1 --profile default
```

Then paste the output into the skill for rotation pipeline design.
