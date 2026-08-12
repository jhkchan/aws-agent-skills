---
name: iam-key-rotation-automator
description: >-
  Designs and implements IAM access key rotation automation pipelines.
  Detects aged access keys via get-access-key-last-used and credential
  reports, wires EventBridge scheduled rules for 90-day rotation,
  deploys Lambda rotation flows (create, verify, deactivate, delete),
  manages graceful overlap windows, sends Slack/SNS pre-rotation
  notifications, handles break-glass exception lists, syncs keys
  cross-account, integrates programmatic access advisor, automates
  credential reports, and migrates permanent keys to STS temporary
  credentials. Emits AUTOMATION_DEPLOYED with IaC template or
  REVIEW_REQUIRED with the specific gap.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). No AWS CLI required for offline workflow design.
  Live deployment uses aws iam list-access-keys, create-access-key,
  update-access-key, delete-access-key, get-access-key-last-used,
  generate-credential-report, aws events put-rule/put-targets, aws
  lambda create-function, aws sns publish, aws sts get-caller-identity.
keywords:
  - IAM access key
  - key rotation
  - credential report
  - get-access-key-last-used
  - EventBridge scheduled rule
  - Lambda rotation
  - access advisor
  - break-glass exception
  - overlap window
  - STS temporary credentials
  - assume role
  - cross-account key sync
tags: [aws-iam, key-rotation, security, access-keys, eventbridge, lambda, automate]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 4
  supports_pipeline: true
  family: Security
  task_type: automate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "AUTOMATION_DEPLOYED | REVIEW_REQUIRED"
  when_to_use: >-
    Building IAM access key rotation automation, wiring EventBridge
    schedules for key rotation, deploying Lambda rotation flows with
    overlap windows, managing break-glass exceptions, integrating
    access advisor, automating credential reports, or migrating
    permanent keys to STS temporary credentials.
  activation_triggers:
    - "automate IAM key rotation"
    - "access key age detection"
    - "credential report automation"
    - "90-day key rotation"
    - "Lambda rotation flow"
    - "overlap window rotation"
    - "break-glass exception list"
    - "access advisor integration"
    - "STS temporary credentials migration"
    - "cross-account key sync"
  invocation_schema: >-
    Input: either (a) a list of IAM users with access key metadata
    (key ID, creation date, last-used date, status), OR (b) a key
    rotation automation requirement. Output: deterministic ROTATION
    block per key — DETECTION/ROTATION_FLOW/OVERLAP/NOTIFICATION/
    EXCEPTIONS/AUDIT/VERDICT.
---

# IAM Key Rotation Automator

## Mindset

**One-line takeaway:** every key rotation pipeline is a five-stage
chain — **detect** (key age via credential report + last-used) →
**notify** (Slack/SNS pre-rotation warning) → **rotate** (create new,
verify, update app) → **deactivate** (overlap window, access advisor
confirms last-used) → **delete** (old key removed after final
verification). A gap in ANY stage produces an app outage (key removed
while still in use) or a security exposure (old key never deleted).

- **The rotation flow MUST include an overlap window.** The
  non-negotiable sequence: create → verify new key → deactivate old →
  verify app works → delete old. Skipping ANY verification step risks
  an outage.
- **Access advisor confirms last-used before deactivation.** Never
  deactivate a key used in the last 24 hours.
- **The long-term goal is key elimination.** Migrate permanent keys
  to STS temporary credentials (assume role). Rotation is a stopgap.

## Quick navigation

| You want to... | Go to |
|---|---|
| Detect aged keys | Step 2 |
| Wire EventBridge schedule | Step 3 |
| Build Lambda rotation flow | Step 4 |
| Design overlap window | Step 5 |
| Send pre-rotation notifications | Step 6 |
| Handle break-glass exceptions | Step 7 |
| Sync keys cross-account | Step 8 |
| Integrate access advisor | Step 9 |
| Automate credential reports | Step 10 |
| Migrate to STS | Step 11 |
| Audit key API calls | Step 12 |

## Critical rules at a glance

1. **The overlap window is non-negotiable.** Create → verify → wait →
   deactivate → verify → wait → delete. NEVER skip a step or combine
   create+delete in one operation.
2. **IAM users can have at most 2 access keys.** The rotation uses
   the second slot. If both are Active, defer rotation until one frees.
3. **Access advisor must confirm last-used before deactivation.**
   `get-access-key-last-used` — if used in the last 24 hours, defer.
4. **Break-glass accounts must be on the exception list.** Never
   auto-rotate emergency access — it can lock out incident responders.
5. **STS temporary credentials are the destination.** The rotation
   pipeline is a stopgap; the end state is assume-role (no keys).

## Pre-flight: data requirements

| Input | Source | Why |
|---|---|---|
| Users + key metadata | `iam list-access-keys` | Rotation targets |
| Key creation date | `AccessKeyMetadata.CreateDate` | Age |
| Key last-used | `iam get-access-key-last-used` | Activity check |
| Credential report | `iam get-credential-report` | Fleet-wide status |
| Exception list | SSM Parameter / DynamoDB | Break-glass accounts |
| App config store | Secrets Manager / SSM | Where keys are consumed |
| CloudTrail trail | `cloudtrail describe-trails` | Audit |

## Process — Rotation pipeline design

### Step 0: Expert knowledge — non-obvious IAM key behaviors

- **IAM allows exactly 2 access keys per user.** The rotation flow uses
  the second slot. If both are Active, the pipeline must first
  determine which can be deactivated — this is the most common blocker.

- **`get-access-key-last-used` is eventually consistent.** `LastUsedDate`
  may lag by up to 4 hours. A key that appears "unused" may have been
  used minutes ago. Always add a 24-hour buffer before deactivation.

- **Deactivating a key does NOT immediately revoke active sessions.**
  An application using the key may continue calling for minutes to
  hours after deactivation. The overlap window accounts for this.

- **Deleting a key is irreversible.** Any app still using it fails
  immediately with `InvalidClientTokenId`. Always verify the new key
  works AND the old key has not been used for N hours before deleting.

- **Credential reports are generated on demand and may be 4 hours
  stale.** For real-time data, use `list-access-keys` +
  `get-access-key-last-used`.

- **STS temporary credentials do NOT need rotation.** When an app
  assumes a role via STS, credentials are temporary (15min-12hr). No
  access key to rotate — this is the target architecture.

- **`create-access-key` returns the secret ONCE.** If lost, the key
  must be deactivated and recreated. Store immediately in Secrets
  Manager. NEVER log the secret.

- **Keys aged > 90 days trigger Security Hub findings.** Check IAM.7
  (key aged > 90 days) and IAM.6 (key never used). Use these as
  secondary detection signals.

### Step 1: Classify the access key

| Key class | Age | Last used | Action |
|---|---|---|---|
| Active, in use | < 90 days | Recent | Schedule at 90 days |
| Active, in use | >= 90 days | Recent (< 24h) | **Rotate now** (overdue) |
| Active, unused | >= 90 days | Never / > 90 days ago | **Deactivate** |
| Inactive, aged | Any | N/A | **Delete** (cleanup) |
| Break-glass | Any | N/A | **Exception** |
| Both slots full | Any | Recent | **Defer** |

### Step 2: Key age detection (credential report + last-used)

```bash
# Generate fresh credential report
aws iam generate-credential-report
aws iam get-credential-report --query 'Content' --output text | base64 -d | column -t -s,

# Per-key detail
aws iam list-access-keys --user-name deployment-user
aws iam get-access-key-last-used --access-key-id AKIAXYZ123
```

```python
import boto3, datetime
iam = boto3.client('iam')

def get_key_ages(user_name):
    keys = iam.list_access_keys(UserName=user_name)['AccessKeyMetadata']
    now = datetime.datetime.now(datetime.timezone.utc)
    for key in keys:
        age_days = (now - key['CreateDate']).days
        last_used = iam.get_access_key_last_used(AccessKeyId=key['AccessKeyId'])
        lu = last_used['AccessKeyLastUsed'].get('LastUsedDate')
        yield {'key_id': key['AccessKeyId'], 'status': key['Status'],
               'age': age_days, 'last_used': lu,
               'days_since_used': (now - lu).days if lu else None}
```

**Risk classification:**

| Risk | Criteria | Action |
|---|---|---|
| CRITICAL | Age > 180 days AND active | Immediate rotation |
| HIGH | Age > 90 days AND active | Rotate within 24 hours |
| MEDIUM | Age > 90 days AND inactive | Deactivate + investigate |
| LOW | Age > 90 days AND never used | Delete (stale) |
| OK | Age < 90 days AND active | No action |

### Step 3: EventBridge scheduled rule for 90-day rotation

```bash
aws events put-rule --name iam-key-rotation-daily \
  --schedule-expression "rate(1 day)" --state ENABLED

aws events put-targets --rule iam-key-rotation-daily \
  --targets '[{"Id":"key-rotation-lambda","Arn":"arn:aws:lambda:us-east-1:111111111111:function:iam-key-rotation","DeadLetterConfig":{"Arn":"arn:aws:sqs:us-east-1:111111111111:key-rotation-dlq"}}]'
```

The Lambda scans all users daily, skips exceptions, and queues keys
past 90 days for rotation with SNS notification.

### Step 4: Lambda rotation flow (create → verify → deactivate → delete)

**Phase 1 — Create:**

```python
def create_new_key(user_name):
    keys = iam.list_access_keys(UserName=user_name)['AccessKeyMetadata']
    active = [k for k in keys if k['Status'] == 'Active']
    if len(active) >= 2:
        return {'error': 'Both key slots in use'}
    new_key = iam.create_access_key(UserName=user_name)
    # Store secret securely immediately
    sm = boto3.client('secretsmanager')
    sm.put_secret_value(SecretId=f'iam-access-key/{user_name}',
        SecretString=json.dumps({
            'access_key_id': new_key['AccessKey']['AccessKeyId'],
            'secret_access_key': new_key['AccessKey']['SecretAccessKey']}))
    return new_key['AccessKey']
```

**Phase 2 — Verify new key works:**

```python
def verify_key(akid, secret):
    sts = boto3.client('sts', aws_access_key_id=akid, aws_secret_access_key=secret)
    try:
        sts.get_caller_identity()
        return True
    except Exception:
        return False
```

**Phase 3 — Deactivate old (after overlap + 24h inactivity):**

```python
def deactivate_old_key(user_name, old_key_id):
    last = iam.get_access_key_last_used(AccessKeyId=old_key_id)
    lu = last['AccessKeyLastUsed'].get('LastUsedDate')
    if lu:
        hours = (datetime.datetime.now(datetime.timezone.utc) - lu).total_seconds()/3600
        if hours < 24:
            return {'deferred': f'Key used {hours:.1f}h ago'}
    iam.update_access_key(UserName=user_name, AccessKeyId=old_key_id, Status='Inactive')
    return {'deactivated': True}
```

**Phase 4 — Delete (after 72h post-deactivation):**

```python
def delete_old_key(user_name, old_key_id):
    for k in iam.list_access_keys(UserName=user_name)['AccessKeyMetadata']:
        if k['AccessKeyId'] == old_key_id and k['Status'] != 'Inactive':
            return {'error': 'Cannot delete Active key'}
    iam.delete_access_key(UserName=user_name, AccessKeyId=old_key_id)
    return {'deleted': True}
```

### Step 5: Overlap window design (graceful rotation)

The period where BOTH keys are active, allowing the app to transition
without downtime.

| Phase | Duration | Action |
|---|---|---|
| Create + verify | Day 0 | New key created, stored, verified via STS |
| App config update | Day 0-1 | App picks up new key from Secrets Manager/SSM |
| Monitor | Day 1-7 | Both keys active; monitor old key usage |
| Deactivate | Day 7 | Old key deactivated (if not used in 24h) |
| Monitor | Day 7-10 | App on new key only; old key Inactive |
| Delete | Day 10 | Old key deleted |

**Key considerations:** Apps reading keys from env vars need redeploy.
Apps using Secrets Manager can hot-reload. Shorten to 24h for non-prod,
extend to 14 days for critical production apps.

### Step 6: Pre-rotation notification (Slack/SNS)

| When | Recipient | Message |
|---|---|---|
| 7 days before | Owner + Slack | "Key X for user Y rotates in 7 days" |
| 1 day before | Owner + Slack | "Key X rotates tomorrow" |
| Create day | Owner + Slack | "New key created. App config updated." |
| Deactivate day | Owner + Slack | "Old key deactivated. Verify app health." |
| Delete day | Owner + Slack | "Old key deleted. Rotation complete." |

```python
def notify(user_name, key_id, age, topic_arn):
    sns.publish(TopicArn=topic_arn,
        Subject=f'IAM Key Rotation: {user_name}',
        Message=f'Key {key_id} is {age} days old. Rotation starting.')
```

### Step 7: Break-glass exception list

```python
def is_break_glass(user_name):
    try:
        exc = json.loads(ssm.get_parameter(Name='/iam-key-rotation/exceptions')['Parameter']['Value'])
        return user_name in exc
    except Exception:
        return False
```

**Exception list (SSM Parameter Store):**

```json
{
  "break-glass-admin": {"reason": "Emergency access", "owner": "security-team"},
  "audit-service": {"reason": "Read-only audit", "owner": "compliance", "review_date": "2026-12-01"}
}
```

Every exception MUST have a `review_date`. The scan flags past-due
exceptions for re-evaluation.

### Step 8: Cross-account key sync

When an app in Account B uses a key from Account A, rotation runs in
Account A but must update Account B:

```python
def sync_cross_account(user_name, new_key_id, target_role_arn):
    assumed = sts.assume_role(RoleArn=target_role_arn, RoleSessionName='key-rotation-sync')
    target_sm = boto3.client('secretsmanager',
        aws_access_key_id=assumed['Credentials']['AccessKeyId'],
        aws_secret_access_key=assumed['Credentials']['SecretAccessKey'],
        aws_session_token=assumed['Credentials']['SessionToken'])
    target_sm.put_secret_value(SecretId=f'iam-access-key/{user_name}',
        SecretString=json.dumps({'access_key_id': new_key_id}))
```

The target KMS key must allow the rotation role to decrypt. Better:
replace cross-account keys with cross-account role assumption (STS).

### Step 9: Access advisor integration

```bash
aws iam generate-service-last-accessed-details --user-name deployment-user
aws iam get-service-last-accessed-details --job-id <id> \
  --query 'ServicesLastAccessed[].{Service:ServiceName,LastAccessed:LastAuthenticated}'
```

| Last used | Action |
|---|---|
| < 1 hour ago | Defer — actively in use |
| < 24 hours ago | Defer — wait for 24h inactivity |
| 1-7 days ago | Proceed with caution — notify owner |
| > 7 days ago | Safe to deactivate |
| Never | Safe to deactivate + delete |

### Step 10: Credential report automation

```bash
# Generate + download weekly
aws events put-rule --name iam-credential-report-weekly \
  --schedule-expression "rate(7 days)" --state ENABLED

aws iam generate-credential-report
aws iam get-credential-report --query 'Content' --output text | base64 -d > report.csv
```

The Lambda parses the CSV and identifies: keys > 90 days old, keys
never used, users with 2 active keys, inactive keys not deleted.

### Step 11: STS temporary credentials migration

The permanent fix: eliminate permanent keys via role assumption.

1. Create an IAM role with the same permissions as the user.
2. Update the app to use `sts:AssumeRole` instead of static keys.
3. The app receives temporary credentials (15min-12hr TTL, auto-refresh).
4. Once verified, deactivate and delete the IAM user's access keys.

**By workload type:**

| Workload | Migration path |
|---|---|
| EC2/ECS/EKS/Lambda | Instance/task/pod/execution role (no key needed) |
| On-premises | STS assume role with long-lived user scoped to `sts:AssumeRole` only |
| Third-party SaaS | IAM role with external trust policy (Web Identity) |

```python
# Before: static key
s3 = boto3.client('s3', aws_access_key_id='AKIAOLD', aws_secret_access_key='old')

# After: STS assume role (auto-refreshing)
sts = boto3.client('sts')
assumed = sts.assume_role(RoleArn='arn:aws:iam::111111111111:role/AppS3Access',
                          RoleSessionName='app-session')
s3 = boto3.client('s3',
    aws_access_key_id=assumed['Credentials']['AccessKeyId'],
    aws_secret_access_key=assumed['Credentials']['SecretAccessKey'],
    aws_session_token=assumed['Credentials']['SessionToken'])
```

For EC2/ECS/EKS: use instance/task/pod roles directly — the SDK
auto-discovers credentials. No code change needed beyond removing the
static keys.

### Step 12: CloudTrail audit

```bash
# IAM key API calls in last 24h
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventSource,AttributeValue=iam.amazonaws.com \
  --start-time $(date -v-1d +%Y-%m-%dT%H:%M:%S) \
  --query 'Events[?EventName==`CreateAccessKey`||EventName==`DeleteAccessKey`||EventName==`UpdateAccessKey`].{Time:EventTime,Name:EventName,User:Username}'

# Anomaly: key creation outside rotation pipeline
aws logs put-metric-filter \
  --log-group-name CloudTrail/DefaultLogGroup --filter-name iam-key-anomaly \
  --filter-pattern '{$.eventSource="iam.amazonaws.com" && $.eventName="CreateAccessKey" && $.userIdentity.sessionContext.sessionIssuer.arn!="arn:aws:iam::111111111111:role/iam-key-rotation-lambda-role"}' \
  --metric-value 1 --metric-namespace SecurityAudit --metric-name KeyCreationAnomaly
```

## Output format

```text
ROTATION: <reference>
USER: <iam-user-name>
KEY: <access-key-id>
CLASSIFICATION:
  - Age: <days>
  - Last used: <date or "never">
  - Status: Active | Inactive
  - Exception: Yes | No
DETECTION:
  - Credential report: <date>
  - Access advisor: <last-used>
  - EventBridge scan: rate(1 day)
ROTATION_FLOW:
  - Create: <lambda>
  - Verify: <sts check>
  - Deactivate: <overlap N days>
  - Delete: <after N days>
OVERLAP:
  - Window: <N days>
NOTIFICATION:
  - SNS: <arn>
  - Slack: <url or N/A>
EXCEPTIONS:
  - Break-glass list: <ssm parameter>
  - User excepted: Yes | No
AUDIT:
  - CloudTrail: iam.amazonaws.com tracking
  - Credential report: weekly
VERDICT: AUTOMATION_DEPLOYED | REVIEW_REQUIRED
GAP: <if REVIEW_REQUIRED>
TEMPLATE: <CLI or YAML>
```

### Worked example — AUTOMATION_DEPLOYED

```text
ROTATION: prod-key-rotation
USER: deployment-user
KEY: AKIAXYZ123
CLASSIFICATION:
  - Age: 91 days
  - Last used: 2 hours ago (S3, CloudFormation)
  - Status: Active
  - Exception: No
DETECTION:
  - Credential report: generated today
  - Access advisor: last used 2 hours ago
  - EventBridge scan: rate(1 day)
ROTATION_FLOW:
  - Create: Lambda creates AKIANEW456, stores in Secrets Manager
  - Verify: Lambda verifies via STS get-caller-identity
  - Deactivate: Old key after 7-day overlap + 24h inactivity
  - Delete: Old key 3 days after deactivation
OVERLAP:
  - Window: 7 days active + 3 days inactive monitoring
NOTIFICATION:
  - SNS topic: arn:aws:sns:us-east-1:111111111111:key-rotation-alerts
  - Slack webhook: configured
EXCEPTIONS:
  - Break-glass list: /iam-key-rotation/exceptions
  - User excepted: No
AUDIT:
  - CloudTrail: iam.amazonaws.com tracking
  - Credential report: weekly generation
VERDICT: AUTOMATION_DEPLOYED
GAP: None
TEMPLATE:
  aws events put-rule --name iam-key-rotation-daily --schedule-expression "rate(1 day)" --state ENABLED
```

### Worked example — REVIEW_REQUIRED

```text
ROTATION: break-glass-key
USER: break-glass-admin
KEY: AKIABREAK789
CLASSIFICATION:
  - Age: 365 days
  - Last used: 45 days ago (during incident)
  - Status: Active
  - Exception: Yes
DETECTION:
  - Credential report: generated today
  - Access advisor: last used 45 days ago (STS, IAM)
  - EventBridge scan: flagged but skipped (exception)
ROTATION_FLOW:
  - N/A — break-glass exception
OVERLAP: N/A
NOTIFICATION:
  - SNS: exception review notice sent to security-team
EXCEPTIONS:
  - Break-glass list: /iam-key-rotation/exceptions
  - User excepted: Yes (Emergency access, owner: security-team)
AUDIT:
  - CloudTrail: iam.amazonaws.com tracking
VERDICT: REVIEW_REQUIRED
GAP: Break-glass account on exception list. Key is 365 days old but exempted. Required: (1) Manual review by security-team; (2) evaluate STS assume-role with MFA instead of permanent key; (3) if permanent key still required, manually rotate and update break-glass procedure; (4) set review date.
TEMPLATE: (manual rotation — break-glass accounts require human approval)
```

## Anti-Patterns — NEVER do these

- NEVER deactivate or delete a key without an overlap window. Create →
  verify → wait → deactivate → verify → wait → delete. Any shortcut
  risks an outage.

- NEVER rotate without checking `get-access-key-last-used`. A key used
  in the last 24 hours may still be active. Always defer deactivation
  until 24 hours of confirmed inactivity.

- NEVER auto-rotate break-glass accounts. Emergency keys must NEVER be
  touched by automation. Maintain and check the exception list.

- NEVER create a new key when both slots are occupied. IAM allows 2
  per user. If both Active, defer and analyze manually.

- NEVER store the secret in plaintext or log it. Store immediately in
  Secrets Manager with KMS encryption. `create-access-key` returns it
  ONCE.

- NEVER rotate all keys in a batch. Rotate one user at a time, verify,
  then proceed. A batch failure leaves multiple apps broken.

- NEVER delete immediately after deactivation. Wait 24-72 hours. Apps
  with cached credentials may still use the deactivated key.

- NEVER omit pre-rotation notifications. Owners must be warned 7 days
  and 1 day before rotation.

- NEVER use permanent keys for EC2/ECS/EKS/Lambda. These support IAM
  roles natively. A permanent key on EC2 is a risk rotation doesn't
  fix — migrate to instance role.

- NEVER forget to update cross-account consumers. A key in Account A
  rotated without syncing Account B causes an outage in B.

- NEVER assume the credential report is real-time. It can lag 4 hours.
  Use `list-access-keys` + `get-access-key-last-used` for live data.

- NEVER omit CloudTrail auditing. `CreateAccessKey`,
  `UpdateAccessKey`, `DeleteAccessKey` outside the pipeline indicate
  unauthorized manipulation.

- NEVER set the overlap below 24 hours for production keys. 7 days is
  the recommended default.

- NEVER leave inactive keys undeleted. Keys > 90 days inactive are a
  Security Hub finding and a security risk.

## Pre-flight safety checks

- **CONFIRMATION GATE:** `CONFIRM: About to <action> for key <key-id>
  of user <user>. Proceed? (yes/no)`
- **Check exception list:** verify user is NOT on the list.
- **Check key slots:** verify a free slot exists.
- **Check access advisor:** verify key not used in last 24h.
- **Back up app config:** save current secret for rollback.

## Appendix A — Key rotation lifecycle matrix

| Key state | Age | Last used | Action | Verdict |
|---|---|---|---|---|
| Active | < 90 days | Recent | No action | OK |
| Active | >= 90 days | Recent (< 24h) | Rotate with overlap | AUTOMATION_DEPLOYED |
| Active | >= 90 days | > 24h ago | Rotate (faster overlap) | AUTOMATION_DEPLOYED |
| Active | >= 90 days | Never | Deactivate + investigate | REVIEW_REQUIRED |
| Active | Any | N/A | Exception list | REVIEW_REQUIRED |
| Inactive | Any | N/A | Delete after 72h | AUTOMATION_DEPLOYED |
| Both slots full | Any | Recent | Defer | REVIEW_REQUIRED |

See **references/iam-key-rotation-flows.md** for detailed CLI references.

## Appendix B — Decision tree

```
On break-glass exception list?
├─ Yes → REVIEW_REQUIRED (manual review)
└─ No → Key >= 90 days old?
        ├─ No → OK
        └─ Yes → Both slots occupied?
                ├─ Yes → REVIEW_REQUIRED (free a slot first)
                └─ No → Used in last 24 hours?
                        ├─ Yes → Defer 24h, then rotate
                        └─ No → AUTOMATION_DEPLOYED
```

## Appendix C — CloudFormation skeleton

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'IAM Access Key Rotation Automation Pipeline'
Resources:
  KeyRotationTopic:
    Type: AWS::SNS::Topic
    Properties: {TopicName: key-rotation-alerts}
  RotationRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement: [{Effect: Allow, Principal: {Service: lambda.amazonaws.com}, Action: sts:AssumeRole}]
      ManagedPolicyArns: [arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole]
      Policies:
        - PolicyName: IAMKeyMgmt
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - {Effect: Allow, Action: [iam:ListAccessKeys, iam:CreateAccessKey, iam:UpdateAccessKey, iam:DeleteAccessKey, iam:GetAccessKeyLastUsed, iam:ListUsers, iam:GetUser], Resource: '*'}
              - {Effect: Allow, Action: [secretsmanager:PutSecretValue, secretsmanager:GetSecretValue], Resource: '*'}
              - {Effect: Allow, Action: [ssm:GetParameter], Resource: '*'}
              - {Effect: Allow, Action: [sns:Publish], Resource: !Ref KeyRotationTopic}
              - {Effect: Allow, Action: sts:GetCallerIdentity, Resource: '*'}
  RotationFunction:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: iam-key-rotation
      Runtime: python3.12
      Handler: index.lambda_handler
      Role: !GetAtt RotationRole.Arn
      Timeout: 300
      Environment: {Variables: {SNS_TOPIC_ARN: !Ref KeyRotationTopic, ROTATION_AGE_DAYS: '90', OVERLAP_DAYS: '7', EXCEPTION_PARAM: '/iam-key-rotation/exceptions'}}
      Code: {ZipFile: 'import boto3,os,json,datetime\niam=boto3.client("iam")\nsns=boto3.client("sns")\nssm=boto3.client("ssm")\ndef lambda_handler(e,c):\n  try:\n    exc=json.loads(ssm.get_parameter(Name=os.environ["EXCEPTION_PARAM"])["Parameter"]["Value"])\n  except: exc={}\n  for u in iam.list_users()["Users"]:\n    if u["UserName"] in exc: continue\n    for k in iam.list_access_keys(UserName=u["UserName"])["AccessKeyMetadata"]:\n      age=(datetime.datetime.now(datetime.timezone.utc)-k["CreateDate"]).days\n      if age>=int(os.environ["ROTATION_AGE_DAYS"]) and k["Status"]=="Active":\n        sns.publish(TopicArn=os.environ["SNS_TOPIC_ARN"],Subject=f"Key rotation: {u[\"UserName\"]}",Message=f"Key {k[\"AccessKeyId\"]} is {age} days old")'}
  DailyRule:
    Type: AWS::Events::Rule
    Properties:
      ScheduleExpression: rate(1 day)
      State: ENABLED
      Targets: [{Id: key-rotation, Arn: !GetAtt RotationFunction.Arn, DeadLetterConfig: {Arn: !GetAtt RotationDLQ.Arn}}]
  RotationDLQ:
    Type: AWS::SQS::Queue
    Properties: {QueueName: key-rotation-dlq}
  InvokePermission:
    Type: AWS::Lambda::Permission
    Properties:
      FunctionName: !Ref RotationFunction
      Action: lambda:InvokeFunction
      Principal: events.amazonaws.com
      SourceArn: !GetAtt DailyRule.Arn
```

## Recent AWS features (2024-2026)

- **Access Analyzer key findings (2024):** Flags external access to IAM
  keys, including third-party service usage. Integrates with rotation
  pipeline to identify exposed keys.
- **Security Hub IAM.7 enhanced (2024-2025):** The "key > 90 days" check
  now includes `LastUsedDate`, distinguishing active-aged from stale.
- **STS session tagging (2024):** Assumed-role sessions carry session
  tags for better attribution when migrating from permanent keys.
- **Credential report format (2025):** Now includes `last_rotated` and
  `last_used_region` columns for richer lifecycle analysis.

## Expert heuristic: the overlap-window principle

The single most important principle: **NEVER remove the old key until
you have verified the new key works in production.**

**The rule:** the pipeline MUST include an overlap window of at least
24 hours (7 days for production) where both keys are active. During
this window: (1) new key deployed, (2) app verified, (3) old key usage
monitored — if still used, app has NOT transitioned, (4) only after 24h
of old-key non-use is it deactivated, (5) only after 72h of successful
operation is it deleted.

**Why:** applications cache credentials. An app that reads the key at
startup won't pick up the new key until restarted. Without overlap,
deletion precedes restart — immediate `InvalidClientTokenId`.

**STS migration is the permanent fix.** The overlap window is correct
for rotation. But eliminating keys entirely via STS is the real fix.

## Domain

AWS CloudOps / Security Automation — IAM credential lifecycle.

## AWS documentation

- **IAM Access Keys** — https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html
- **IAM Credential Reports** — https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_getting-report.html
- **IAM Access Advisor** — https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_access-advisor.html
- **STS Temporary Credentials** — https://docs.aws.amazon.com/STS/latest/APIReference/welcome.html
- **Security Hub IAM Checks** — https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-standards-fsbp-controls.html
