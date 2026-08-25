---
name: iam-key-rotation-automator
description: Designs and implements IAM access key rotation automation pipelines. Detects aged access keys via get-access-key-last-used and credential reports, wires EventBridge scheduled rules for 90-day rotation, deploys Lambda rotation flows (create, verify, deactivate, delete), manages graceful overlap windows, sends Slack/SNS pre-rotation notifications, handles break-glass exception lists, syncs keys cross-account, integrates programmatic access advisor, automates credential reports, and migrates permanent keys to STS temporary credentials. Emits AUTOMATION_DEPLOYED with IaC template or REVIEW_REQUIRED with the specific gap.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline workflow design. Live deployment uses aws iam list-access-keys, create-access-key, update-access-key, delete-access-key, get-access-key-last-used, generate-credential-report, aws events put-rule/put-targets, aws lambda create-function, aws sns publish, aws sts get-caller-identity.
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '4'
  supports_pipeline: 'true'
  family: Security
  task_type: automate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: AUTOMATION_DEPLOYED | REVIEW_REQUIRED
  when_to_use: Building IAM access key rotation automation, wiring EventBridge schedules for key rotation, deploying Lambda rotation flows with overlap windows, managing break-glass exceptions, integrating access advisor, automating credential reports, or migrating permanent keys to STS temporary credentials.
  activation_triggers: automate IAM key rotation, access key age detection, credential report automation, 90-day key rotation, Lambda rotation flow, overlap window rotation, break-glass exception list, access advisor integration, STS temporary credentials migration, cross-account key sync
  invocation_schema: 'Input: either (a) a list of IAM users with access key metadata (key ID, creation date, last-used date, status), OR (b) a key rotation automation requirement. Output: deterministic ROTATION block per key — DETECTION/ROTATION_FLOW/OVERLAP/NOTIFICATION/ EXCEPTIONS/AUDIT/VERDICT.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: IAM access key, key rotation, credential report, get-access-key-last-used, EventBridge scheduled rule, Lambda rotation, access advisor, break-glass exception, overlap window, STS temporary credentials, assume role, cross-account key sync
  tags: aws-iam, key-rotation, security, access-keys, eventbridge, lambda, automate
---
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

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Step 0: Expert knowledge".
> Load when: designing the pipeline — 2-slot limit, last-used eventual consistency, session survival after deactivation, irreversible delete, 4h-stale reports.

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

> **Moved verbatim** → [references/iam-key-rotation-flows.md](references/iam-key-rotation-flows.md) § "Step 2 — key age detection (Python)".
> Load when: computing per-key age and days-since-used in Python instead of the CLI.

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

> **Moved verbatim** → [references/iam-key-rotation-flows.md](references/iam-key-rotation-flows.md) § "Step 4 — Lambda rotation flow code".
> Load when: implementing the four-phase rotation Lambda (create, verify, deactivate, delete).

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

> **Moved verbatim** → [references/sts-migration-patterns.md](references/sts-migration-patterns.md) § "Step 11 — STS migration code".
> Load when: converting static-key boto3 clients to STS assume-role with auto-refreshing sessions.

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

> **Moved verbatim** → [references/worked-examples.md](references/worked-examples.md) § "Worked example — REVIEW_REQUIRED".
> Load when: emitting a REVIEW_REQUIRED verdict for a break-glass exception key.

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

> **Moved verbatim** → [references/worked-examples.md](references/worked-examples.md) § "Appendix C — CloudFormation skeleton".
> Load when: deploying the rotation pipeline as CloudFormation (SNS, role, Lambda, EventBridge rule, DLQ).

## Recent AWS features (2024-2026)

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Recent AWS features".
> Load when: using Access Analyzer key findings, Security Hub IAM.7 enrichment, session tagging, or the new credential-report columns.

## Expert heuristic: the overlap-window principle

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Expert heuristic: the overlap-window principle".
> Load when: sizing the overlap window or deciding when deactivation/deletion is safe; includes why apps break without overlap.

## References (load on demand)

- [references/worked-examples.md](references/worked-examples.md) — REVIEW_REQUIRED worked example (break-glass key) and the Appendix C CloudFormation skeleton
- [references/advanced-patterns.md](references/advanced-patterns.md) — Step 0 non-obvious key behaviors, overlap-window principle, recent AWS features
- [references/iam-key-rotation-flows.md](references/iam-key-rotation-flows.md) — full rotation flow patterns; now also holds the Step 2 age-detection code and Step 4 four-phase Lambda code moved from SKILL.md
- [references/sts-migration-patterns.md](references/sts-migration-patterns.md) — migration patterns by workload; now also holds the Step 11 before/after STS code moved from SKILL.md

## Domain

AWS CloudOps / Security Automation — IAM credential lifecycle.

## AWS documentation

- **IAM Access Keys** — https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html
- **IAM Credential Reports** — https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_getting-report.html
- **IAM Access Advisor** — https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_access-advisor.html
- **STS Temporary Credentials** — https://docs.aws.amazon.com/STS/latest/APIReference/welcome.html
- **Security Hub IAM Checks** — https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-standards-fsbp-controls.html
