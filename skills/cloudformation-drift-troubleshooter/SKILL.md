---
name: cloudformation-drift-troubleshooter
description: 'Diagnoses AWS CloudFormation stack drift — resources whose actual configuration diverged from the template because they were changed, deleted, or added outside CloudFormation. Walks detect-stack-drift, describe-stack-drift-detection-status, and describe-stack-resource-drifts to classify each drift as MODIFIED (property changed outside CFN), DELETED (resource deleted outside CFN), or ADDITION (new resource not in stack). Maps drift impact on stack updates and recommends a resolution strategy: import existing resources (import-resources), drift reset (update to match drift), or revert the resource to match template. Covers drift prevention via IAM policy with aws:CalledViaFirst, CloudFormation Hooks, and Conformance Packs. Handles nested stack drift and CDK drift. Emits ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE. Use when a stack reports DRIFTED, an UPDATE_FAILED cites drift as the cause, an operator needs to import out-of-band resources, or a compliance pack flags stack drift.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline diagnosis works on supplied describe-stack-resource-drifts JSON. Live-account diagnosis uses aws cloudformation detect-stack-drift, describe-stack-drift-detection-status, describe-stack-resource-drifts, describe-stack-resources, describe-change-set, aws iam simulate-principal-policy, and aws configservice get-resource-config-history for forensic property-level timeline (AWS CLI v2, SSO or key-based...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: DevTools
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
  when_to_use: Diagnosing why a stack reports StackDriftStatus DRIFTED, why an UPDATE_FAILED cites drift as the cause, why a resource was modified or deleted outside CloudFormation, how to classify per-resource drift (MODIFIED / DELETED / ADDITION), how to resolve drift via import / reset / revert, how to prevent recurrence via IAM policy or CloudFormation Hooks, or how to walk nested-stack drift and CDK drift.
  when_not_to_use: Stack lifecycle failures unrelated to drift (use cloudformation-stack-troubleshooter for CREATE_FAILED, UPDATE_FAILED with Replacement, DELETE_FAILED, ROLLBACK_COMPLETE, UPDATE_ROLLBACK_FAILED). IaC generation from existing resources (use the IaC Generator skill). Pure CloudFormation Hooks authoring (use the Hooks authoring reference). CDK errors that are not drift-related (use the CDK troubleshooter).
  activation_triggers: CloudFormation drift, stack drift, StackDriftStatus DRIFTED, ResourceDriftStatus MODIFIED, ResourceDriftStatus DELETED, ResourceDriftStatus ADDITION, describe-stack-resource-drifts, detect-stack-drift, resource modified outside CloudFormation, resource deleted outside CloudFormation, import existing resources into stack, drift reset, CloudFormation Hooks, CDK drift, nested stack drift, Conformance Pack drift
  invocation_schema: 'Input: either (a) a symptom description (stack name or ARN, region, observed StackDriftStatus, the list of StackResourceDrifts with their ResourceDriftStatus and PropertyDifferences), OR (b) a live-account scenario where the agent runs aws cloudformation detect-stack-drift / describe-stack-drift-detection-status / describe-stack-resource-drifts and aws configservice get-resource-config-history to gather evidence. Output: a deterministic INCIDENT / VERDICT / ROOT_CAUSE / EVIDENCE / ROOT_CAUSE_CATALOG / REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_FOUND, NEED_MORE_INFO, ESCALATE} and ROOT_CAUSE names the drift type (MODIFIED / DELETED / ADDITION) and the offending resource(s), with a resolution strategy chosen from {IMPORT, RESET_TO_DRIFT, REVERT_TO_TEMPLATE, ESCALATE_TO_OWNER}.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: CloudFormation, drift, detect-stack-drift, describe-stack-resource-drifts, StackDriftStatus, DRIFTED, MODIFIED, DELETED, ADDITION, resource import, import-resources, drift reset, out-of-band change, CloudFormation Hooks, Conformance Pack, nested stack drift, CDK drift, UPDATE_FAILED
  tags: cloudformation, devtools, troubleshoot, drift, resource-import, guardrails
---

# CloudFormation Drift Troubleshooter

## Activation

Activate this skill when the user reports CloudFormation drift. Trigger
phrases: "CloudFormation drift", "stack drift",
"StackDriftStatus DRIFTED", "ResourceDriftStatus MODIFIED",
"ResourceDriftStatus DELETED", "ResourceDriftStatus ADDITION",
"describe-stack-resource-drifts", "detect-stack-drift", "resource
modified outside CloudFormation", "resource deleted outside
CloudFormation", "import existing resources into stack", "drift reset",
"CloudFormation Hooks", "CDK drift", "nested stack drift".

## Mindset

**One-line takeaway:** CloudFormation drift is the gap between the
template-of-record and the actual resource state. The diagnostic surface
is `describe-stack-resource-drifts`, which classifies each resource as
`MODIFIED`, `DELETED`, `ADDITION`, or `IN_SYNC`. The job of this skill
is to (1) confirm drift exists, (2) classify each drift by type and
severity, (3) identify the out-of-band actor and trigger, (4) choose a
resolution strategy (import, reset to drift, revert to template), and
(5) prevent recurrence.

Three facts make drift troubleshooting different from generic stack
failure triage:

- **Drift is not an error — it is a state.** `StackDriftStatus: DRIFTED`
  does not block the stack from being read; it warns that the next
  update may not behave as the operator expects. Many stacks run DRIFTED
  for months without incident. The actionable question is "which
  property diverged, who changed it, and what happens if I update now?"

- **Each drift type has a different resolution.** A `MODIFIED` drift
  can be reset by accepting the out-of-band value into the template
  (drift reset) or by reverting the resource to match the template.
  A `DELETED` drift usually means the resource was removed manually
  and must be recreated or imported-as-gone. An `ADDITION` drift
  requires the operator to decide whether to bring the new resource
  under stack management (import) or delete the out-of-band resource.

- **Drift on immutable properties is the dangerous case.** If a drifted
  property is one CloudFormation treats as requiring Replacement (e.g.,
  an RDS DBInstanceIdentifier, a DynamoDB KeySchema, an S3 bucket's
  BucketName), the next update will trigger resource replacement —
  often the opposite of what the operator wants. Always cross-reference
  each `PropertyDifference` against the resource's immutable-property
  list before recommending `update-stack`.

## Quick reference — drift type to resolution

| Drift type | What it means | Resolution options | Risk |
|---|---|---|---|
| `MODIFIED` (property changed outside CFN) | A property on an existing stack resource was edited via console / SDK / CLI, not via stack update | (a) Drift reset — update template to match actual, then `update-stack`; (b) Revert — manually set resource back to template value; (c) Import-as-truth — `import-resources` with the new template | If the drifted property is immutable, `update-stack` triggers Replacement |
| `DELETED` (resource deleted outside CFN) | The physical resource backing a stack resource was deleted via console / SDK / CLI | (a) Recreate — `update-stack` will recreate the missing resource; (b) Remove from template if the resource is no longer needed; (c) Mark as `DeletionPolicy: Retain` if intentional | Stack update will attempt to recreate — may fail if dependencies are gone |
| `ADDITION` (new resource not in stack) | A new physical resource exists in the account but is not managed by the stack (visible via resource-level import scan or Config) | (a) Import — `import-resources` to bring under stack management; (b) Delete the out-of-band resource; (c) Ignore if intentionally unmanaged | Out-of-band resources are invisible to stack delete — they persist silently |
| `NOT_CHECKED` | Drift detection has not run for this resource (e.g., a resource type that does not support drift detection) | Run `detect-stack-drift`; for unsupported types, use AWS Config rules for posture | Hidden drift — the stack reports `IN_SYNC` but the resource may have diverged |
| Drift on `DeletionPolicy: Retain` resource | The retained resource drifts but CloudFormation does not reconcile it on stack delete | Track separately; consider `UpdateReplacePolicy: Delete` if drift resets are desired | Resource persists after stack delete regardless of drift |

## Quick navigation

- **Step 0** — Capture the drift signal (stack name/ARN, region,
  StackDriftStatus, time of last detection, trigger source).
- **Step 1** — Run / refresh drift detection
  (`detect-stack-drift` then poll
  `describe-stack-drift-detection-status`).
- **Step 2** — Read `describe-stack-resource-drifts` and classify each
  drift (MODIFIED / DELETED / ADDITION).
- **Step 3** — Forensic walk: who changed it and when? (CloudTrail,
  Config timeline).
- **Step 4** — Assess update impact: for each `PropertyDifference`,
  determine if the property is immutable (Replacement required).
- **Step 5** — Choose resolution: IMPORT, RESET_TO_DRIFT,
  REVERT_TO_TEMPLATE, REMOVE_FROM_TEMPLATE.
- **Step 6** — Validate via ChangeSet (or `create-change-set` for
  resource import) before applying.
- **Step 7** — Decide VERDICT (ROOT_CAUSE_FOUND / NEED_MORE_INFO /
  ESCALATE).
- **Step 8** — Prevent recurrence (IAM policy, CloudFormation Hooks,
  Conformance Pack).

## STRICT output contract

Every response MUST begin with this block — no preamble, no
conversational opening:

```text
INCIDENT: <stack name or ARN> in <region> — StackDriftStatus <status>, <N> drifted resource(s)
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
ROOT_CAUSE: <MODIFIED | DELETED | ADDITION> on <LogicalResourceId (PhysicalResourceId)> — <one-sentence identifying the out-of-band actor and trigger, or "actor unknown — CloudTrail event not found">
EVIDENCE:
  - describe-stacks: <quoted StackStatus, StackDriftStatus, LastDriftDetectionDateTime>
  - describe-stack-resource-drifts: <quoted StackResourceDrift per drifted resource: ResourceDriftStatus, PropertyDifferences>
  - CloudTrail: <quoted eventName, eventSource, eventTime, userIdentityarn for the out-of-band change, if found>
  - Config timeline: <quoted configurationItem captureTime and diff for the drifted property, if available>
  - describe-change-set (for the proposed fix): <quoted Action + Replacement for the resource being reset/imported>
ROOT_CAUSE_CATALOG: #<N>
RESOLUTION: <IMPORT | RESET_TO_DRIFT | REVERT_TO_TEMPLATE | REMOVE_FROM_TEMPLATE | ESCALATE_TO_OWNER>
REMEDIATION:
  1. <exact CLI sequence — detect-stack-drift, import-resources, update-stack, or manual revert>
  2. <verification command — describe-stack-resource-drifts until StackResourceDriftStatus: IN_SYNC>
  3. <prevention step — IAM policy, CloudFormation Hook, or Conformance Pack rule>
```

### FORBIDDEN output patterns

- NEVER start with "Let me analyze…" or "I'll investigate…" — the
  INCIDENT line is the FIRST line, always. No conversational preamble.
- NEVER use lowercase verdict values — emit `ROOT_CAUSE_FOUND`,
  `NEED_MORE_INFO`, or `ESCALATE`.
- NEVER omit the per-resource `ResourceDriftStatus` from EVIDENCE.
  "The stack is drifted" is the symptom; the per-resource drift
  classification is the diagnosis.
- NEVER recommend `update-stack` to reset drift on a resource whose
  drifted property is in the immutable-property list without
  explicitly warning that the update will trigger Replacement.
- NEVER declare `ROOT_CAUSE_FOUND` without naming the out-of-band
  actor (or stating that the CloudTrail event was not found and the
  actor is unknown).

## Process — Diagnostic decision tree (apply in order)

### Step 0: Capture the drift signal

Gather these six pieces. Each downstream step branches on which is
present.

| Signal | Source | Why required |
|---|---|---|
| **Stack name or ARN + region** | User-provided or `aws cloudformation list-stacks` | All describe calls need this |
| **StackDriftStatus + LastDriftDetectionDateTime** | `aws cloudformation describe-stacks --stack-name <name>` (or `describe-stack-resource-drifts`) | Confirms drift exists; stale detection time means a re-run is needed |
| **StackResourceDrift list** | `describe-stack-resource-drifts --stack-name <name>` | The primary diagnostic surface — per-resource drift classification and PropertyDifferences |
| **CloudTrail events for the drifted resources** | `aws cloudtrail lookup-events --lookup-attributes AttributeKey=ResourceName,AttributeValue=<PhysicalResourceId>` | Identifies who changed the resource and when |
| **AWS Config configurationItems for the resource** | `aws configservice get-resource-config-history --resource-type <type> --resource-id <id>` | Forensic timeline of property-level changes |
| **Recent ChangeSets and stack events** | `describe-change-set`, `describe-stack-events` | Determines whether the divergence is drift or a failed update |

If the user has not provided the stack name or region, emit
`VERDICT: NEED_MORE_INFO` with the `list-stacks` discovery command and
the list of missing inputs (stack name/ARN, region, StackDriftStatus,
StackResourceDrift output).

### Step 1: Run / refresh drift detection

Drift detection is asynchronous and may be stale. Always run a fresh
detection before diagnosing:

```bash
# Start a new drift detection run:
DETECTION_ID=$(aws cloudformation detect-stack-drift --stack-name <name> \
  --query 'StackDriftDetectionId' --output text)

# Poll until complete:
aws cloudformation describe-stack-drift-detection-status \
  --stack-drift-detection-id $DETECTION_ID \
  --query '{status:DetectionStatus, drift:StackDriftStatus, detected:Timestamp}'
```

`DetectionStatus` transitions: `DETECTION_IN_PROGRESS` →
`DETECTION_COMPLETE` (or `DETECTION_FAILED`). A `DETECTION_FAILED`
status usually means one or more resource types do not support drift
detection — proceed with the resources that were checked and flag the
unsupported ones as `NOT_CHECKED`.

For **nested stacks**, drift detection now recurses into child stacks
(2024-2025 enhancement). Each child stack's drift must be examined
independently via `describe-stack-resource-drifts --stack-name
<child-stack-arn>`.

For **CDK stacks**, run `cdk drift <stack-name>` (CDK v2.180+, 2025),
which compares the synthesized template to the deployed stack and
reports drift at the construct level.

### Step 2: Classify each drift

```bash
aws cloudformation describe-stack-resource-drifts --stack-name <name> \
  --query 'StackResourceDrifts[?ResourceDriftStatus!=`IN_SYNC`].{logical:LogicalResourceId,physical:PhysicalResourceId,type:ResourceType,status:ResourceDriftStatus,diffs:PropertyDifferences}' \
  --output table
```

Map each non-`IN_SYNC` resource to a category:

| `ResourceDriftStatus` | Category | Diagnostic step |
|---|---|---|
| `MODIFIED` | **A. MODIFIED** | Step 3 — identify the changed property and actor |
| `DELETED` | **B. DELETED** | Step 3 — identify when the resource was deleted and whether dependencies remain |
| `ADDITION` | **C. ADDITION** (only visible via resource-level import scan or Config) | Step 3 — identify whether the resource should be imported or deleted |
| `NOT_CHECKED` | **D. NOT_CHECKED** | Flag as hidden drift; recommend AWS Config rule for ongoing posture |
| `IN_SYNC` | Not drift | Skip |

**Precedence rule.** When multiple resources are drifted, prioritise
the drift on resources whose properties are immutable (Step 4) — those
drifts will trigger Replacement on the next update, which is the most
dangerous outcome. Read-only drifts (e.g., tags) are lower priority.

### Step 3: Forensic walk — who changed it and when?

For each drifted resource, identify the out-of-band actor and the
change time. This drives the resolution choice (intentional vs
accidental drift).

```bash
# CloudTrail lookup for the specific physical resource:
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue=<PhysicalResourceId> \
  --start-time <LastDriftDetectionDateTime minus 30 days> \
  --end-time <LastDriftDetectionDateTime> \
  --query 'Events[?EventName!=`Describe*'].{event:EventName,source:EventSource,time:EventTime,user:Username,ip:CloudTrailEvent' \
  --output table

# Config timeline for property-level forensic diff:
aws configservice get-resource-config-history \
  --resource-type <ResourceType e.g. AWS::S3::Bucket> \
  --resource-id <PhysicalResourceId> \
  --limit 10 \
  --query 'configurationItems[].{capture:captureTime,version:configurationStateId,arn:arn}'
```

If the CloudTrail event is found, the actor and intent are known. If
the event is older than the trail retention (default 90 days), the
actor is unknown and the operator must decide based on whether the
drifted value is desirable.

### Step 4: Assess update impact — is the drifted property immutable?

For each `PropertyDifference`, determine whether the changed property
is one CloudFormation treats as immutable (requires Replacement):

| Resource | Common immutable properties | Drift impact on update |
|---|---|---|
| `AWS::S3::Bucket` | `BucketName` | Update triggers Replacement — the bucket is recreated with a new name |
| `AWS::DynamoDB::Table` | `TableName`, `KeySchema`, `AttributeDefinitions` (for keys) | Update triggers Replacement |
| `AWS::RDS::DBInstance` | `DBInstanceIdentifier`, `AllocatedStorage` (downgrade), `Engine` | Update triggers Replacement or fails |
| `AWS::IAM::Role` | `RoleName` | Update triggers Replacement |
| `AWS::EC2::Instance` | `InstanceType` (depends), `ImageId`, `KeyName` | Update triggers Replacement |
| `AWS::Lambda::Function` | `FunctionName`, `Runtime` (some), `PackageType` | Update triggers Replacement |
| `AWS::SQS::Queue` | `QueueName` | Update triggers Replacement |
| `AWS::Logs::LogGroup` | `LogGroupName` | Update triggers Replacement |

The authoritative test is the ChangeSet: create a no-op ChangeSet on
the stack with `describe-change-set` and inspect the `Replacement`
field for the drifted resource.

```bash
aws cloudformation create-change-set --stack-name <name> \
  --change-set-name drift-impact-probe \
  --change-set-type UPDATE \
  --template-body file://current-template.yaml \
  --capabilities CAPABILITY_IAM

aws cloudformation describe-change-set \
  --stack-name <name> --change-set-name drift-impact-probe \
  --query 'Changes[?ResourceChange.LogicalResourceId==`<drifted-logical-id>`].ResourceChange.{action:Action,replacement:Replacement,scope:Scope}'
```

If `Replacement: True` and the operator does not want the resource
replaced, the only safe resolution is `REVERT_TO_TEMPLATE` (manually
restore the original property value on the physical resource before
any `update-stack`).

### Step 5: Choose resolution strategy

| Goal | Resolution | How |
|---|---|---|
| Accept the out-of-band change as the new template truth | `RESET_TO_DRIFT` | Update the template property to match the actual value, then `create-change-set` + `execute-change-set`. Next drift detection reports `IN_SYNC`. |
| Restore the resource to match the template (drift is wrong) | `REVERT_TO_TEMPLATE` | Manually edit the physical resource (console / CLI) to restore the template value. No stack update is required; drift detection next run reports `IN_SYNC`. |
| Bring an out-of-band resource under stack management | `IMPORT` | `create-change-set` with `--change-set-type IMPORT` and `--resources-to-import` JSON; the template declares the resource; CloudFormation maps the existing physical resource to the logical id without recreating it. |
| The drifted resource is no longer needed | `REMOVE_FROM_TEMPLATE` | Delete the resource from the template and `update-stack`. For physical resources that should persist, set `DeletionPolicy: Retain`. |
| The drift is owned by another team or requires approval | `ESCALATE_TO_OWNER` | Surface the CloudTrail actor and Config timeline; route to the resource owner. Do not self-serve a reset. |

**Resource import flow (high-level):**

```bash
# 1. Generate the resources-to-import JSON:
cat > resources-to-import.json <<EOF
[
  {
    "ResourceType": "AWS::S3::Bucket",
    "LogicalResourceId": "MyBucket",
    "ResourceIdentifier": { "BucketName": "my-existing-bucket" }
  }
]
EOF

# 2. Create an IMPORT change set:
aws cloudformation create-change-set \
  --stack-name <name> \
  --change-set-name import-bucket \
  --change-set-type IMPORT \
  --resources-to-import file://resources-to-import.json \
  --template-body file://template-with-bucket.yaml \
  --capabilities CAPABILITY_IAM

# 3. Review and execute:
aws cloudformation describe-change-set --stack-name <name> --change-set-name import-bucket
aws cloudformation execute-change-set --stack-name <name> --change-set-name import-bucket
```

### Step 6: Validate via ChangeSet before applying any fix

Before applying any resolution that touches the stack, validate with a
ChangeSet:

1. **For `RESET_TO_DRIFT`:** run `create-change-set --change-set-type
   UPDATE` with the updated template. Confirm the drifted resource
   shows `Action: Modify`, `Replacement: False` (or explicitly True if
   accepted).
2. **For `IMPORT`:** run `create-change-set --change-set-type IMPORT`
   with the `--resources-to-import` payload. Confirm the imported
   resource shows `Action: Import` and no other resources change.
3. **For `REVERT_TO_TEMPLATE`:** no stack update is needed — the
   physical resource is reverted manually; drift detection next run
   confirms `IN_SYNC`.
4. **Execute** the ChangeSet only after it matches expectations.

### Step 7: Decide — ROOT_CAUSE_FOUND vs NEED_MORE_INFO vs ESCALATE

- **ROOT_CAUSE_FOUND.** The walk identified a specific drift type
  (MODIFIED / DELETED / ADDITION), the offending resource(s), and a
  resolution strategy with the exact CLI sequence. Output REMEDIATION.
- **NEED_MORE_INFO.** The walk reached a step where the operator
  cannot supply evidence (e.g., CloudTrail lookup requires elevated
  read access, the stack name is unknown, or the physical resource
  cannot be identified). Output the list of missing inputs.
- **ESCALATE.** The walk identifies drift owned by another team
  (different AWS account, separate IAM owner), drift that requires
  security or compliance approval (e.g., a bucket policy weakened
  out-of-band), or drift on a resource type that CloudFormation
  cannot import. Output the escalation target and the specific
  request.

### Step 8: Prevent recurrence

| Prevention mechanism | Scope | How |
|---|---|---|
| **IAM policy to restrict direct changes** | Per principal | Attach a deny policy on the underlying service API (e.g., `s3:PutBucketPolicy` for a bucket managed by CFN) for all principals except the CloudFormation execution role. Use a `Condition` keyed to `aws:CalledViaFirst: cloudformation.amazonaws.com` to allow the change only when made via CloudFormation. |
| **Service Control Policy (org-level)** | Account / OU | SCP that denies direct resource mutations on CFN-managed resource types except via CloudFormation. |
| **CloudFormation Hooks** | Stack-level, pre-deployment | Author a Hook that validates resource configuration at `CREATE_PRE_DEPLOYMENT` / `UPDATE_PRE_DEPLOYMENT`. Hooks do not prevent out-of-band drift directly, but they enforce compliance on the next stack update. |
| **AWS Config Conformance Pack** | Account / org | Deploy a conformance pack with `cloudformation-stack-drift-detection-check` and custom rules that alert on `StackDriftStatus: DRIFTED`. Combine with an SNS topic and Lambda remediation for auto-detection. |
| **CloudTrail alarm on direct mutations** | Per resource | CloudWatch metric filter on CloudTrail for direct API calls on CFN-managed resources, alarming on out-of-band changes within minutes. |

The IAM `aws:CalledViaFirst` condition is the canonical pattern for
"only CloudFormation may touch this resource":

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyDirectMutationOnCfnManagedResources",
      "Effect": "Deny",
      "NotAction": [
        "s3:Get*",
        "s3:List*"
      ],
      "Resource": "arn:aws:s3:::my-cfn-managed-bucket",
      "Condition": {
        "StringNotEquals": {
          "aws:CalledViaFirst": "cloudformation.amazonaws.com"
        }
      }
    }
  ]
}
```

## Output format

```text
INCIDENT: <stack name or ARN> in <region> — StackDriftStatus <status>, <N> drifted resource(s)
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
ROOT_CAUSE: <MODIFIED | DELETED | ADDITION> on <LogicalResourceId (PhysicalResourceId)> — <actor and trigger>
EVIDENCE:
  - describe-stacks: <StackStatus, StackDriftStatus, LastDriftDetectionDateTime>
  - describe-stack-resource-drifts: <ResourceDriftStatus + PropertyDifferences per resource>
  - CloudTrail: <eventName, eventSource, eventTime, userIdentityarn>
  - Config timeline: <configurationItem captureTime + diff>
  - describe-change-set: <Action + Replacement for the proposed fix>
ROOT_CAUSE_CATALOG: #<N>
RESOLUTION: <IMPORT | RESET_TO_DRIFT | REVERT_TO_TEMPLATE | REMOVE_FROM_TEMPLATE | ESCALATE_TO_OWNER>
REMEDIATION:
  1. <exact CLI sequence>
  2. <verification — describe-stack-resource-drifts until IN_SYNC>
  3. <prevention — IAM policy, CloudFormation Hook, or Conformance Pack>
```

### Worked example — MODIFIED drift on S3 bucket policy (RESET_TO_DRIFT)

```text
INCIDENT: logging-stack in us-east-1 — StackDriftStatus DRIFTED, 1
drifted resource (LogsBucket)
VERDICT: ROOT_CAUSE_FOUND
ROOT_CAUSE: MODIFIED on LogsBucket (logging-stack-logsbucket-abc) —
the bucket policy was edited out-of-band on 2026-08-04 by an
operator adding a cross-account PutObject grant from account
111122223333, diverging from the template policy
EVIDENCE:
  - describe-stacks: StackStatus CREATE_COMPLETE, StackDriftStatus
    DRIFTED, LastDriftDetectionDateTime 2026-08-05T09:14:22Z
  - describe-stack-resource-drifts: LogsBucket
    ResourceDriftStatus MODIFIED with 1 PropertyDifference on
    BucketPolicy.Document.Statement[0].Principal from
    {"Service":"logging.us-east-1.amazonaws.com"} to
    {"AWS":"arn:aws:iam::111122223333:root"}
  - CloudTrail: PutBucketPolicy on s3.amazonaws.com at
    2026-08-04T22:11:48Z by arn:aws:iam::111122223333:user/dev-alice
    from source IP 10.42.1.5
  - Config timeline: configurationItem captured 2026-08-04T22:11:49Z
    showing the policy Principal change
  - describe-change-set (drift-impact-probe): LogsBucket Action
    Modify, Replacement False, Scope [Properties] — the policy drift
    does NOT require Replacement
ROOT_CAUSE_CATALOG: #1 (out-of-band modification of CFN-managed resource)
RESOLUTION: RESET_TO_DRIFT
REMEDIATION:
  1. The change appears intentional (the cross-account grant is a
     legitimate logging use case). Accept the drift by updating the
     template to match the actual policy, then create and execute a
     ChangeSet:
     aws cloudformation create-change-set \
       --stack-name logging-stack \
       --change-set-name accept-bucket-policy-drift \
       --change-set-type UPDATE \
       --template-body file://template-with-updated-policy.yaml \
       --capabilities CAPABILITY_IAM
     aws cloudformation describe-change-set \
       --stack-name logging-stack \
       --change-set-name accept-bucket-policy-drift
     Confirm LogsBucket Action Modify, Replacement False. Then:
     aws cloudformation execute-change-set \
       --stack-name logging-stack --change-set-name accept-bucket-policy-drift
  2. Verify drift is resolved:
     DETECTION_ID=$(aws cloudformation detect-stack-drift \
       --stack-name logging-stack --query 'StackDriftDetectionId' --output text)
     aws cloudformation describe-stack-drift-detection-status \
       --stack-drift-detection-id $DETECTION_ID
     Expect StackDriftStatus IN_SYNC after DetectionStatus DETECTION_COMPLETE.
  3. Prevent recurrence — attach a deny policy on
     s3:PutBucketPolicy scoped to this bucket, conditioned on
     aws:CalledViaFirst != cloudformation.amazonaws.com, so future
     edits are made only through the stack. Alternative: deploy a
     Conformance Pack with cloudformation-stack-drift-detection-check
     alarming to the SRE SNS topic.
```

## Expert edge cases

These patterns represent genuine, non-obvious CloudFormation drift
behaviours that a senior operator would catch but a generalist would
miss.

### Drift detection does not run automatically

CloudFormation does not run drift detection on a schedule. The console
"drift status" column reflects the **last manual run**. A stack may
report `IN_SYNC` based on a stale detection hours or days old. Always
run `detect-stack-drift` before diagnosing, then poll
`describe-stack-drift-detection-status`. For continuous posture, pair
AWS Config with the `cloudformation-stack-drift-detection-check`
managed rule on a schedule.

### Not all resource types support drift detection

CloudFormation drift detection covers most AWS resources, but some
resource types (e.g., `AWS::CloudFormation::WaitConditionHandle`,
some third-party registered types, and resources with custom
`Default` values in extensions) report `NOT_CHECKED`. A stack can
report `DRIFTED` based on partial coverage — and conversely,
`IN_SYNC` based on partial coverage does not mean the un-checked
resources have not drifted. Always inspect the per-resource
`ResourceDriftStatus`, not just the stack-level
`StackDriftStatus`.

### Drift on tags is reported as MODIFIED but rarely impactful

Tags are mutable and almost never block updates. A `MODIFIED` drift
where the only `PropertyDifference` is `Tags` is low-priority and can
usually be resolved by `RESET_TO_DRIFT` (accept the actual tags into
the template) without risk. Reserve urgency for drift on
configuration properties that affect Replacement.

### `aws:CalledViaFirst` is the canonical prevention condition

A simple deny on the underlying service API breaks CloudFormation too.
The correct pattern is a `Condition` that allows the API only when
`aws:CalledViaFirst == cloudformation.amazonaws.com` — CloudFormation
sets this context key when it makes a downstream API call on behalf
of the stack. Apply the deny to all principals that should not make
direct changes, including the CloudFormation execution role itself
(the role inherits the context key correctly when CloudFormation
calls the service).

### Import does not reset drift — it imports the resource

Operators sometimes run `import-resources` expecting it to align the
template to the actual state. It does — but only because the operator
supplies a template that matches the actual resource. Import does not
auto-generate the template from the resource's current configuration.
For that, use the IaC Generator (`cloudformation create-generated-template`),
which emits a template fragment from the existing resource; then
import that fragment into the stack.

### Nested stack drift requires drilling into the child

A parent stack reports `DRIFTED` based on its own resources plus the
aggregate of its child stacks. A child in `DRIFTED` state propagates
up. The parent's `describe-stack-resource-drifts` shows the
`AWS::CloudFormation::Stack` resource as the carrier, but the actual
drifted resources are in the child. Always drill into the child via
its ARN (the parent resource's `PhysicalResourceId`).

### CDK drift differs from CloudFormation drift

`cdk drift` (2025) compares the synthesized template to the deployed
stack, but CDK construct-level drift is not the same as CloudFormation
resource-level drift. A CDK construct may synthesise into multiple
resources; construct-level drift hides which underlying resource
diverged. Always cross-reference the CloudFormation
`describe-stack-resource-drifts` for resource-level detail when
remediating CDK drift.

### `DeletionPolicy: Retain` resources drift silently after stack delete

A resource with `DeletionPolicy: Retain` is skipped on stack delete —
it persists in the account. Subsequent direct changes to that orphaned
resource are not tracked by CloudFormation (the stack no longer
exists). Use AWS Config to track these resources, or attach a
CloudTrail alarm scoped to the resource ARN.

### Drift can cause UPDATE_FAILED on an unrelated property change

A resource drifted out-of-band (e.g., an S3 bucket policy edited
directly). A later stack UPDATE that touches a different property
(e.g., lifecycle configuration) can fail because CloudFormation
reconciles all properties, including the drifted one. The fix is
either to revert the drift before the update, or to update the
template to match the drift first.

### Resource import requires exact property match

The template used in `--resources-to-import` must declare the
resource with properties that match the actual physical resource at
import time. A mismatch causes `IMPORT_FAILED` (similar to
`CREATE_FAILED` for normal stacks). Always run `cfn-lint` on the
import template and verify property values via Config or the
underlying service's describe API before the import.

## Expert heuristic — "Read the per-resource ResourceDriftStatus, not the stack-level StackDriftStatus"

The single most common diagnostic mistake is treating the stack-level
`StackDriftStatus: DRIFTED` as the diagnosis. It is the symptom. The
actionable signal is the per-resource `ResourceDriftStatus` on each
resource returned by `describe-stack-resource-drifts`, including the
specific `PropertyDifferences` for each drifted property.

Quick lookup table for common drift resolutions:

| Per-resource finding | What it means | Default resolution |
|---|---|---|
| `MODIFIED` on a mutable property | Property edited out-of-band; update is safe | `RESET_TO_DRIFT` if intentional, else `REVERT_TO_TEMPLATE` |
| `MODIFIED` on an immutable property | Property edited out-of-band; update triggers Replacement | `REVERT_TO_TEMPLATE` first; only `RESET_TO_DRIFT` if Replacement is acceptable |
| `DELETED` on a resource with no dependents | Resource removed manually; nothing depends on it | `REMOVE_FROM_TEMPLATE` or `update-stack` to recreate |
| `DELETED` on a resource with dependents in the stack | Resource removed manually; downstream resources will fail | `update-stack` to recreate first; then verify dependents |
| `ADDITION` (via Config) of a resource that should be managed | Out-of-band resource that overlaps the stack's responsibility | `IMPORT` to bring under management |
| `NOT_CHECKED` on a critical resource | Drift detection unsupported; unknown state | Pair AWS Config rule with periodic CloudTrail review |

When in doubt, run:
`aws cloudformation describe-stack-resource-drifts --stack-name <name>`
and read the `ResourceDriftStatus` and `PropertyDifferences` for each
non-`IN_SYNC` resource. The stack-level `StackDriftStatus` is the
symptom; the per-resource drift is the diagnosis.

## Anti-Patterns — NEVER

- **NEVER** treat `StackDriftStatus: DRIFTED` as the root cause. It
  is the symptom. The per-resource `ResourceDriftStatus` and
  `PropertyDifferences` are the diagnosis.
- **NEVER** recommend `update-stack` to reset drift on a resource
  whose drifted property is immutable without explicitly warning that
  the update triggers Replacement. Always probe with a ChangeSet
  first.
- **NEVER** recommend `import-resources` without verifying that the
  template properties match the actual physical resource exactly.
  Mismatch causes `IMPORT_FAILED`.
- **NEVER** declare `ROOT_CAUSE_FOUND` without naming the out-of-band
  actor (or explicitly stating that the CloudTrail event was not
  found and the actor is unknown).
- **NEVER** rely on a stale `StackDriftStatus` from the console.
  Always run `detect-stack-drift` fresh before diagnosing, then poll
  `describe-stack-drift-detection-status` to confirm completion.
- **NEVER** assume `IN_SYNC` on a stack with `NOT_CHECKED` resources
  means no drift exists. Drift detection does not cover all resource
  types; use AWS Config for full posture.
- **NEVER** treat `DeletionPolicy: Retain` resources as drifted when
  they persist after stack delete. They are intentionally retained;
  track them via AWS Config separately.
- **NEVER** run `update-stack` blind on a drifted stack. Always
  create and review a ChangeSet first, inspecting `Replacement` for
  every drifted resource.
- **NEVER** recommend a `Deny` IAM policy on the underlying service
  API without the `aws:CalledViaFirst: cloudformation.amazonaws.com`
  condition — an unconditional deny breaks CloudFormation itself.
- **NEVER** assume `cdk drift` output maps 1:1 to CloudFormation
  resource drift. Always cross-reference
  `describe-stack-resource-drifts` for resource-level detail.
- **NEVER** assume a nested stack's parent drift reflects the root
  cause. Drill into the child stack — the parent's
  `AWS::CloudFormation::Stack` resource only carries the child's
  status.
- **NEVER** conclude drift resolution without re-running
  `detect-stack-drift` and confirming `StackResourceDriftStatus:
  IN_SYNC` on every previously-drifted resource.

## Recent AWS features (2024-2026)

- **CloudFormation drift detection for nested stacks (2024-2025):**
  drift detection now recurses into nested child stacks, surfacing
  child drift via the parent's `describe-stack-resource-drifts`. The
  parent's `AWS::CloudFormation::Stack` resource carries the child's
  aggregate drift status; the per-resource detail is in the child.
- **Resource-level import (`import-resources`, enhanced 2024-2025):**
  bring an out-of-band resource under stack management without a
  full stack import. The `--resources-to-import` payload maps an
  existing physical resource to a new logical id in the template.
- **CDK drift detection (`cdk drift`, 2025):** CDK v2.180+ exposes
  `cdk drift <stack-name>`, comparing the synthesized template to
  the deployed stack. Construct-level drift is reported; cross-
  reference CloudFormation for resource-level detail.
- **IaC Generator (`create-generated-template`, 2024-2025):** generates
  CloudFormation template fragments from existing resources in the
  account. Useful for producing the template required for an
  `import-resources` operation on drifted or out-of-band resources.
- **CloudFormation Hooks (GA, 2024-2025):** pre-deployment Hooks fire
  on `CREATE_PRE_DEPLOYMENT`, `UPDATE_PRE_DEPLOYMENT`, and
  `DELETE_PRE_DEPLOYMENT`. Hooks do not prevent out-of-band drift
  directly but enforce compliance on the next stack update.
- **Conformance Pack: `cloudformation-stack-drift-detection-check`**
  (managed rule, 2024): schedules drift detection on a cadence and
  alerts on `StackDriftStatus: DRIFTED`. Pair with SNS + Lambda for
  auto-detection and remediation.
- **`aws:CalledViaFirst` condition key (enhanced 2024-2025):** now
  broadly supported across services, enabling precise IAM policies
  that allow mutations only when made via CloudFormation.

## References

See `references/drift-types-and-resolution.md` for the full
per-drift-type decision matrix with worked examples for each
resolution strategy, and `references/diagnostic-commands.md` for the
canonical command script for drift detection, forensic walk, and
remediation.

## Domain

AWS CloudOps / DevTools — Infrastructure-as-Code Configuration
Compliance.

## AWS documentation

- **AWS CloudFormation drift detection** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-stack-drift.html
- **Resource import** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/resource-import.html
- **CloudFormation Hooks** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/hooks.html
- **`aws:CalledViaFirst` condition key** — https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_condition-keys.html#condition-keys-calledviafirst
- **AWS Config conformance packs** — https://docs.aws.amazon.com/config/latest/developerguide/conformance-packs.html
- **CDK drift** — https://docs.aws.amazon.com/cdk/v2/guide/drift.html
- **CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/cloudformation/
