---
name: drift-detection-automator
description: >-
  Designs and implements automated CloudFormation drift detection
  workflows across single-account and multi-account environments. Wires
  scheduled EventBridge rules for periodic drift detection runs,
  AWS Config rules for individual resource drift, Lambda comparison
  functions for desired-vs-actual state analysis, SNS notifications with
  severity-based routing, SSM Automation remediation (CloudFormation
  update or custom Lambda), multi-account via CloudFormation StackSets,
  drift suppression for known-acceptable changes, drift report export
  to S3 with Athena query, IaC pipeline integration (Terraform plan as
  drift check), and Config Aggregator cross-account visibility. Emits
  AUTOMATION_DEPLOYED with the full detection+notification pipeline or
  REVIEW_REQUIRED with the specific gap. Use when building drift
  detection automation, scheduling drift checks, integrating drift
  detection with IaC pipelines, or setting up multi-account drift
  visibility.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Gemini). No AWS CLI required for offline workflow design. Live
  deployment uses aws cloudformation detect-stack-drift,
  describe-stack-drift-detection-status, describe-stack-resource-drifts,
  aws configservice put-config-rule, describe-config-rules,
  aws events put-rule, put-targets, aws lambda create-function,
  aws sns create-topic, subscribe, aws ssm create-document,
  start-automation-execution, aws cloudformation create-stack-set,
  create-stack-instances, and aws athena start-query-execution —
  AWS CLI v2, SSO or key-based credentials.
keywords:
  - AWS CloudFormation
  - drift detection
  - stack drift
  - resource drift
  - EventBridge scheduled
  - AWS Config
  - Config Aggregator
  - desired state
  - actual state
  - Lambda comparison
  - SNS notification
  - SSM Automation
  - CloudFormation StackSets
  - drift suppression
  - drift report
  - Amazon Athena
  - Terraform plan
  - IaC pipeline
  - governance automation
tags: [cloudformation, drift-detection, config, eventbridge, lambda, governance, ssm-automation, stacksets, automate]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 4
  supports_pipeline: true
  entry_point: false
  family: Governance
  task_type: automate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "AUTOMATION_DEPLOYED | REVIEW_REQUIRED"
  when_to_use: >-
    Building automated CloudFormation drift detection, scheduling periodic
    drift checks via EventBridge, wiring Config rules for resource drift,
    designing Lambda desired-vs-actual comparison functions, setting up
    SSM Automation remediation for drifted stacks, configuring multi-account
    drift detection via StackSets, suppressing known-acceptable drift,
    exporting drift reports to S3/Athena, integrating drift checks into
    IaC pipelines (Terraform plan), or establishing Config Aggregator
    cross-account drift visibility.
  when_not_to_use: >-
    Investigating a specific CloudFormation stack failure or rollback
    (use cloudformation-stack-troubleshooter or cloudformation-stack-
    rollback-troubleshooter). Deploying new CloudFormation stacks (use
    the deployer family). Troubleshooting drift on a single stack without
    automation (use cloudformation-drift-troubleshooter). Terraform state
    management and import belong to the Terraform toolchain.
  activation_triggers:
    - "automate drift detection"
    - "schedule drift check"
    - "CloudFormation drift automation"
    - "Config rule resource drift"
    - "drift detection EventBridge"
    - "Lambda desired vs actual"
    - "drift remediation SSM"
    - "drift suppression"
    - "multi-account drift StackSets"
    - "drift report S3 Athena"
    - "Terraform plan drift check"
    - "Config Aggregator drift"
  invocation_schema: >-
    Input: either (a) a CloudFormation stack name or set of stacks plus
    desired detection cadence, OR (b) a drift automation requirement
    ("detect drift hourly and notify", "auto-remediate drift on
    non-production stacks"). Output: deterministic DRIFT_AUTOMATION block
    per stack set — DETECTION/COMPARISON/NOTIFICATION/REMEDIATION/
    INTEGRATION/SAFETY/VERDICT — where VERDICT is AUTOMATION_DEPLOYED
    (pipeline ready) or REVIEW_REQUIRED (specific gap cited).
---

# Drift Detection Automator

## Mindset

**One-line takeaway:** CloudFormation drift detection is NOT automatic —
it must be triggered per-stack via `detect-stack-drift`. A complete drift
automation pipeline is a five-stage loop: **schedule** (EventBridge cron)
→ **detect** (`DetectStackDrift` API) → **compare** (Lambda analyzes
drift details) → **notify** (SNS with severity) → **remediate** (SSM
Automation or human-approved CloudFormation update). A gap in ANY stage
produces a silent failure: drift accumulates undetected, the detection
runs but results are ignored, or remediation fires on a production stack
without approval and causes an outage.

- **Drift detection is per-stack and on-demand.** CloudFormation does NOT
  continuously monitor for drift. Without a scheduled trigger, drift
  accumulates silently. This is the #1 misconception.
- **Config rules detect individual resource drift** but do NOT detect
  stack-level drift. The two are complementary: Config catches real-time
  resource changes; CFN drift detection catches divergence from template.
- **Remediation should be human-approved for production stacks.** Auto-
  remediating drift by re-applying the template can revert an intentional
  hotfix applied during an incident. Always require approval for prod.
- **Drift suppression is essential** for known-acceptable changes (ASG
  capacity, Lambda alias traffic shifts). Without suppression, these
  create false-positive noise.

## Quick navigation

| You want to... | Go to |
|---|---|
| Schedule periodic drift detection | Step 2 |
| Pick Config rule vs CFN drift detection | Step 3 |
| Wire Lambda for desired-vs-actual comparison | Step 4 |
| Set up SNS with severity-based routing | Step 5 |
| Configure SSM Automation remediation | Step 6 |
| Deploy multi-account via StackSets | Step 7 |
| Suppress known-acceptable drift | Step 8 |
| Export drift reports to S3/Athena | Step 9 |
| Integrate with Terraform plan | Step 10 |
| Set up Config Aggregator cross-account | Step 11 |
| Avoid common automation pitfalls | Anti-Patterns |

## Critical rules at a glance (do NOT bury these)

1. **`detect-stack-drift` is synchronous API but asynchronous execution.**
   Returns a `StackDriftDetectionId` immediately. Poll
   `describe-stack-drift-detection-status` for completion.

2. **`describe-stack-resource-drifts` returns the detailed diff.** Each
   drift includes `PropertyDifferences` — exact properties that differ
   between template and actual resource. This is the Lambda's input.

3. **Config `cloudformation-stack-drift-detection-check` reads the LAST
   drift result.** It does NOT run `detect-stack-drift`. You still need
   scheduled triggers to refresh drift status.

4. **Auto-remediation of production drift is dangerous.** An operator may
   have intentionally modified a resource during an incident. Re-applying
   the template reverts the hotfix. Always route production remediation
   through human approval.

5. **Not all resource types support drift detection.** Unsupported types
   report `NOT_CHECKED`. A "no drift" result may mean the resource type
   is not checked, not that it is clean.

## Pre-flight: data requirements

| Input | Source | Why |
|---|---|---|
| Stack names | `list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE` | Detection targets |
| Resource count per stack | `describe-stack-resources` | Sizing — large stacks take longer |
| Existing drift status | `describe-stack-drift-detection-status` | Current state |
| Config rules for drift | `describe-config-rules` | Existing rules |
| Config Aggregator | `describe-configuration-aggregators` | Cross-account visibility |
| SNS topic ARN | `sns list-topics` | Notification target |
| SSM documents | `ssm list-documents --document-type Automation` | Remediation runbooks |
| StackSets | `list-stack-sets` | Multi-account targets |
| IaC tool | (user input) | Terraform / CFN / CDK — drives pipeline integration |

**If the input is malformed**, emit:

```text
DRIFT_AUTOMATION: <reference>
STACK: <name or UNKNOWN>
VERDICT: ERROR
REASON: Cannot design drift automation — stack names and detection cadence are required.
GAP: Re-supply list-stacks output and the desired detection schedule.
```

## Process — Workflow design (apply in order)

### Step 0: Expert knowledge — non-obvious CloudFormation + Config behaviors

- **Drift detection does NOT modify the stack.** `detect-stack-drift` is
  read-only. Remediation is a SEPARATE step (update-stack or change-set).

- **`detect-stack-drift` has an API rate limit.** Running detection on
  more than ~50 stacks simultaneously throttles. For fleets, stagger via
  SQS queue with batch size 10 or Step Functions map state.

- **Config's drift rule reads the LAST result.** It does NOT trigger new
  detection. If the last detection was 30 days ago, the rule reports
  30-day-old status. You MUST schedule periodic `detect-stack-drift`.

- **Not all resource types support drift detection.** Unsupported types
  report `NOT_CHECKED`. Common unsupported: `AWS::CloudFormation::Wait*`,
  nested stacks (now supported as of 2024-2025 — recurses into children).

- **Stack update reverts drift but may cause interruption.** For resources
  requiring replacement (immutable property changes), this means downtime.
  Always review the change-set before executing.

- **StackSet drift detection runs per stack-instance.** Iterate
  `list-stack-instances` and call `detect-stack-drift` per instance. For
  large StackSets (100+), use Step Functions Distributed Map.

- **Config Aggregator provides cross-account visibility WITHOUT deploying
  Lambda to each account.** The aggregator pulls Config data from members
  into a central account. Recommended pattern for multi-account.

- **Terraform `plan` detects drift against Terraform state, NOT CFN.** If
  resources are Terraform-managed, CFN drift detection does not apply.

### Step 1: Classify the stack and detection cadence

| Stack class | Cadence | Auto-remediate? | Why |
|---|---|---|---|
| Production, critical | Daily (off-peak) | No — approval required | Hotfixes show as drift; auto-revert causes outage |
| Production, non-critical | Daily | No — notify only | Same risk; lower urgency |
| Staging | Hourly | Yes (with rollback tested) | Pre-prod — safe to auto-remediate |
| Development | Every 6 hours | Yes | Fast iteration; drift is expected |
| Sandbox | Weekly | No — log only | Ephemeral; drift is noise |

**Decision rule:** default to **notify-only** for production. Auto-
remediation requires: (a) non-production stack, (b) tested runbook,
(c) documented rollback path, (d) CloudTrail audit configured.

### Step 2: Schedule periodic drift detection via EventBridge

```bash
aws events put-rule \
  --name drift-detection-daily \
  --schedule-expression "cron(0 2 * * ? *)" \
  --state ENABLED

aws events put-targets \
  --rule drift-detection-daily \
  --targets '[{
    "Id": "drift-detection-lambda",
    "Arn": "arn:aws:lambda:us-east-1:111111111111:function:drift-detector",
    "Input": "{\"stack_filter\": \"production-*\", \"remediate\": false}"
  }]'
```

The Lambda iterates stacks and triggers detection:

```python
cfn = boto3.client('cloudformation')

def lambda_handler(event, context):
    for stack_name in list_stacks(event.get('stack_filter', '*')):
        response = cfn.detect_stack_drift(StackName=stack_name)
        status = poll_detection_status(stack_name, response['StackDriftDetectionId'])
        if status['StackDriftStatus'] == 'DRIFTED':
            drifts = cfn.describe_stack_resource_drifts(
                StackName=stack_name,
                StackResourceDriftStatusFilters=['MODIFIED'])
            notify_drift(stack_name, drifts)
            if event.get('remediate'):
                trigger_remediation(stack_name, drifts)
```

For > 50 stacks, use SQS: `EventBridge cron → SQS (names) → Lambda (batch 10)`.

### Step 3: Config rule for resource-level drift

```bash
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "cloudformation-stack-drift-detection-check",
    "Source": {"Owner": "AWS", "SourceIdentifier": "CLOUDFORMATION_STACK_DRIFT_DETECTION_CHECK"},
    "Scope": {"ComplianceResourceTypes": ["AWS::CloudFormation::Stack"]},
    "MaximumExecutionFrequency": "TwentyFour_Hours"
  }'
```

**IMPORTANT:** this rule reads the LAST drift result. Pair it with the
scheduled detection (Step 2) to keep drift status current.

### Step 4: Lambda desired-vs-actual comparison

```python
def classify_drift(drift):
    severity = 'LOW'
    critical_props = ['SecurityGroups', 'PolicyDocument', 'AssumeRolePolicyDocument',
                      'BucketEncryption', 'PublicAccessBlockConfiguration']
    for diff in drift.get('PropertyDifferences', []):
        if any(c in diff['PropertyPath'] for c in critical_props):
            return 'CRITICAL'
        elif diff['DifferenceType'] in ['ADD', 'REMOVE', 'NOT_EQUAL']:
            severity = max(severity, 'MEDIUM')
    return severity
```

For the full severity classification matrix and comparison patterns, see
**references/drift-comparison-and-remediation.md**.

### Step 5: SNS notification with severity-based routing

```python
def notify_drift(stack_name, drift_results, topic_arn):
    max_severity = max((r['severity'] for r in drift_results), default='NONE')
    subject = f"[Drift {max_severity}] {stack_name} — {len(drift_results)} resources drifted"
    sns.publish(TopicArn=topic_arn, Subject=subject,
               Message=json.dumps({'stack': stack_name, 'drifts': drift_results}, indent=2),
               MessageAttributes={'severity': {'DataType': 'String', 'StringValue': max_severity}})
```

**SNS subscription filters:**

| Severity | Filter | Action |
|---|---|---|
| CRITICAL | `severity = CRITICAL` | Page on-call |
| HIGH | `severity in [CRITICAL, HIGH]` | Email security + ops |
| MEDIUM | `severity in [CRITICAL, HIGH, MEDIUM]` | Email ops |
| LOW | All | Log to CloudWatch |

### Step 6: SSM Automation remediation

**Option A — CloudFormation change-set (re-apply template):**

```yaml
---
schemaVersion: '0.3'
assumeRole: '{{ AutomationAssumeRole }}'
description: 'Remediate CloudFormation drift via change-set'
parameters:
  StackName: {type: String}
  AutomationAssumeRole: {type: String}
mainSteps:
  - name: CreateChangeSet
    action: aws:executeAwsApi
    inputs:
      Service: cloudformation
      Api: CreateChangeSet
      StackName: '{{ StackName }}'
      ChangeSetName: 'drift-remediation-{{ global:TIMESTAMP }}'
      ChangeSetType: UPDATE
      UsePreviousTemplate: true
      Capabilities: '["CAPABILITY_IAM","CAPABILITY_NAMED_IAM"]'
    outputs:
      - {Name: ChangeSetId, Selector: '$.Id', Type: String}
  - name: ApproveRemediation
    action: aws:approve
    inputs:
      NotificationArn: 'arn:aws:sns:us-east-1:111111111111:drift-approval'
      Message: 'Approve drift remediation for {{ StackName }}?'
      MinRequiredApprovals: 1
  - name: ExecuteChangeSet
    action: aws:executeAwsApi
    inputs:
      Service: cloudformation
      Api: ExecuteChangeSet
      ChangeSetName: '{{ CreateChangeSet.ChangeSetId }}'
      StackName: '{{ StackName }}'
    isCritical: true
    onFailure: abort
```

**Production:** always include the `aws:approve` step. **Non-production:**
remove the approval step for auto-remediation.

### Step 7: Multi-account via StackSets

```bash
aws cloudformation create-stack-set \
  --stack-set-name drift-detection-pipeline \
  --template-body file://drift-detection-stackset.yaml \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --permission-model SERVICE_MANAGED \
  --auto-deployment Enabled=true,RetainStacksOnAccountDeletion=false

aws cloudformation create-stack-instances \
  --stack-set-name drift-detection-pipeline \
  --deployment-targets OrganizationalUnitIds=['ou-abc1-1234abcd'] \
  --regions us-east-1 us-west-2 eu-west-1
```

For per-instance drift detection across the StackSet, iterate
`list-stack-instances` and call `detect-stack-drift` per instance.

### Step 8: Drift suppression for known-acceptable changes

```python
SUPPRESSION_RULES = {
    'AWS::AutoScaling::AutoScalingGroup': ['DesiredCapacity', 'MinSize', 'MaxSize'],
    'AWS::Lambda::Alias': ['RoutingConfig'],
    'AWS::IAM::Role': ['PermissionsBoundary'],
    'AWS::S3::Bucket': ['ReplicationStatus'],
}

def is_suppressed(drift):
    rtype = drift['ResourceType']
    if rtype not in SUPPRESSION_RULES:
        return False
    suppressed = SUPPRESSION_RULES[rtype]
    return all(d['PropertyPath'] in suppressed for d in drift.get('PropertyDifferences', []))
```

Store rules in SSM Parameter Store for runtime updates:

```bash
aws ssm put-parameter --name /drift-detection/suppression-rules \
  --type String --value file://suppression-rules.json --tier Standard
```

**Review suppression rules quarterly.** A suppressed property today may
become critical tomorrow.

### Step 9: Drift report export to S3 + Athena

```python
def export_drift_report(drift_results, bucket, date_str):
    key = f"drift-reports/dt={date_str}/drift-report.json"
    s3.put_object(Bucket=bucket, Key=key,
                 Body=json.dumps(drift_results, indent=2),
                 ContentType='application/json')
```

Athena table:

```sql
CREATE EXTERNAL TABLE IF NOT EXISTS drift_reports (
  stack_name string, account_id string, region string,
  resource_id string, resource_type string, drift_severity string,
  drift_status string, detection_time string, property_path string,
  expected_value string, actual_value string)
PARTITIONED BY (dt string)
STORED AS JSON
LOCATION 's3://drift-reports-bucket/drift-reports/';
```

Common queries — top drifted resource types, most frequent drift by stack,
critical drift not remediated. See **references/drift-reporting-and-athena.md**.

### Step 10: IaC pipeline integration (Terraform plan as drift check)

```bash
# Exit code 0 = no changes, 1 = error, 2 = changes (drift)
terraform plan -detailed-exitcode -out=plan.tfplan
if [ $? -eq 2 ]; then
    terraform show -json plan.tfplan | jq '[.resource_changes[] | select(.change.actions != ["no-op"])]' > drift.json
    aws s3 cp drift.json s3://drift-reports/$(date +%Y-%m-%d)/
    aws sns publish --topic-arn $SNS_TOPIC --subject "Terraform Drift" --message file://drift.json
fi
```

GitHub Actions integration:

```yaml
name: Drift Detection
on:
  schedule: [{cron: '0 2 * * *'}]
jobs:
  drift-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3
      - run: |
          terraform init -input=false
          terraform plan -detailed-exitcode -out=plan.tfplan || exit_code=$?
          if [ $exit_code -eq 2 ]; then
            echo "::warning::Drift detected"
            terraform show -json plan.tfplan > drift.json
          fi
```

### Step 11: Config Aggregator cross-account drift visibility

```bash
aws configservice put-configuration-aggregator \
  --configuration-aggregator-name drift-visibility-aggregator \
  --organization-aggregation-source '{
    "RoleArn": "arn:aws:iam::111111111111:role/ConfigAggregatorRole",
    "AllAwsRegions": true
  }'

aws configservice aggregate-discovered-resources \
  --configuration-aggregator-name drift-visibility-aggregator \
  --resource-type AWS::CloudFormation::Stack \
  --filters '{"ComplianceType": "NON_COMPLIANT"}'
```

The aggregator provides a single pane across all accounts WITHOUT
deploying Lambda to each member. The drift detection Lambda runs only
in the aggregator account.

## Output format

```text
DRIFT_AUTOMATION: <reference>
STACK: <stack-name or stack-set-name>
DETECTION:
  - Method: <EventBridge scheduled | Config rule | Terraform plan>
  - Cadence: <hourly | daily | weekly>
  - Config rule: <name if applicable>
COMPARISON:
  - Lambda: <function name>
  - Severity classification: <CRITICAL/HIGH/MEDIUM/LOW property-based>
  - Suppression rules: <list of suppressed properties>
NOTIFICATION:
  - SNS topic: <arn>
  - Routing: <CRITICAL -> page | HIGH -> email | MEDIUM -> log | LOW -> ignore>
REMEDIATION:
  - Method: <SSM Automation | CloudFormation update | Terraform apply | manual>
  - Auto-remediate: <true for non-prod | false for prod>
  - Approval gate: <aws:approve | Change Manager | none>
INTEGRATION:
  - Config Aggregator: <enabled | disabled>
  - Drift report: <S3 bucket + Athena table>
  - IaC pipeline: <Terraform plan | CloudFormation CI/CD>
SAFETY:
  - Production protection: <approval required | auto-remediate blocked>
  - Rollback: <change-set rollback | CloudFormation rollback | none>
  - Rate limiting: <Lambda concurrency | SQS buffer>
AUDIT:
  - CloudTrail: cloudformation:DetectStackDrift, cloudformation:ExecuteChangeSet
  - CloudWatch: Lambda invocation logs + drift metrics
VERDICT: AUTOMATION_DEPLOYED | REVIEW_REQUIRED
GAP: <if REVIEW_REQUIRED, the specific missing piece>
TEMPLATE: <CLI snippet or YAML for the pipeline>
```

### Worked example — AUTOMATION_DEPLOYED, staging stack daily drift

```text
DRIFT_AUTOMATION: staging-drift-pipeline
STACK: staging-web-app
DETECTION:
  - Method: EventBridge scheduled (cron 0 2 * * ? *)
  - Cadence: daily at 02:00 UTC
  - Config rule: cloudformation-stack-drift-detection-check
COMPARISON:
  - Lambda: drift-detector
  - Severity classification: CRITICAL (SecurityGroups, IAM policies), MEDIUM (other)
  - Suppression rules: ASG DesiredCapacity, Lambda RoutingConfig
NOTIFICATION:
  - SNS topic: arn:aws:sns:us-east-1:111111111111:drift-alerts
  - Routing: CRITICAL -> page on-call | HIGH -> email | MEDIUM -> log
REMEDIATION:
  - Method: SSM Automation (CloudFormation change-set re-apply)
  - Auto-remediate: true (staging — non-production)
  - Approval gate: none (non-prod)
INTEGRATION:
  - Config Aggregator: enabled (cross-account visibility)
  - Drift report: s3://drift-reports/dt={date}/ + Athena table drift_reports
SAFETY:
  - Production protection: approval required (separate pipeline for prod)
  - Rollback: change-set rollback tested
  - Rate limiting: Lambda concurrency 5, SQS buffer for > 50 stacks
AUDIT:
  - CloudTrail: cloudformation:DetectStackDrift, cloudformation:ExecuteChangeSet
VERDICT: AUTOMATION_DEPLOYED
GAP: None
TEMPLATE:
  aws events put-rule --name drift-detection-daily --schedule-expression "cron(0 2 * * ? *)"
```

### Worked example — REVIEW_REQUIRED, production stack

```text
DRIFT_AUTOMATION: prod-drift-pipeline
STACK: prod-payment-service
DETECTION:
  - Method: EventBridge scheduled (cron 0 2 * * ? *)
  - Cadence: daily at 02:00 UTC
COMPARISON:
  - Lambda: drift-detector
  - Severity: CRITICAL (3 resources: SG modified, IAM policy changed, ALB listener)
NOTIFICATION:
  - SNS topic: arn:aws:sns:us-east-1:111111111111:drift-alerts-critical
  - Routing: CRITICAL -> page on-call
REMEDIATION:
  - Method: MANUAL — SSM Change Manager approval required
  - Auto-remediate: BLOCKED (production stack)
SAFETY: production protection active, approval required
VERDICT: REVIEW_REQUIRED
GAP: Production drift detected but auto-remediation intentionally blocked. Operator must review 3 drifted resources. If intentional hotfixes from incident response, update the CFN template to match. If unintentional, create a change-set to revert. Do NOT auto-remediate without approval — re-applying the template may revert an active hotfix and cause a production outage.
TEMPLATE: (SSM Automation with aws:approve gate — see Step 6)
```

## Anti-Patterns — NEVER do these things

- NEVER auto-remediate production stack drift without human approval.
  An operator may have applied an intentional hotfix. Re-applying the
  template reverts the hotfix and causes an outage.

- NEVER assume `detect-stack-drift` runs automatically. CloudFormation
  does NOT continuously monitor. Without a scheduled trigger, drift
  accumulates silently.

- NEVER assume the Config drift rule triggers new detection. It reads
  the LAST result. Pair it with scheduled `detect-stack-drift` calls.

- NEVER run `detect-stack-drift` on more than 50 stacks simultaneously.
  The API throttles. Use SQS with batch processing or Step Functions.

- NEVER execute a CloudFormation change-set to fix drift without
  reviewing it first. Some changes require resource replacement
  (downtime). Always check the change-set for replacements.

- NEVER suppress drift without quarterly review. A suppressed property
  that is acceptable today may mask an unauthorized change tomorrow.

- NEVER confuse Terraform plan drift with CloudFormation drift. They
  detect drift against different sources of truth. If resources are
  Terraform-managed, CFN drift detection does not apply.

- NEVER omit severity classification from the comparison Lambda. A
  SecurityGroup modification and a tag change are not the same severity.
  Without classification, operators develop notification fatigue.

- NEVER deploy drift detection to a single Region for multi-Region
  StackSets. Each stack-instance in each Region needs detection.

- NEVER remediate drift on a StackSet blindly. The StackSet may manage
  production and non-production instances. Filter by OU or account tags.

- NEVER forget that `describe-stack-resource-drifts` returns
  `NOT_CHECKED` for unsupported types. "No drift" may mean "not checked."

- NEVER use `update-stack` directly for drift remediation. Always use
  `create-change-set` first for review. `update-stack` executes with
  no preview.

- NEVER skip the Config Aggregator for multi-account visibility.
  Deploying a Lambda to every account is expensive. The aggregator
  provides cross-account visibility from a single account.

## Pre-flight safety checks

- **MANDATORY CONFIRMATION GATE.** Before state-changing operations:
  `CONFIRM: About to <action> for stack <stack> in account <account>.
  Proceed? (yes/no)`

- **Verify the stack exists and is stable** before scheduling:
  `describe-stacks --stack-name <name> --query 'Stacks[0].StackStatus'`

- **For production, verify the approval SNS topic has confirmed
  subscriptions.** Unconfirmed means `aws:approve` blocks indefinitely.

- **Test the remediation SSM document in non-production.** Create
  deliberate drift, run the document, verify the stack returns to
  `IN_SYNC`.

- **For StackSets, verify `auto-deployment`** so new accounts receive
  the drift detection pipeline automatically.

## Appendix A — Drift detection methods comparison

| Method | Scope | Real-time? | Pros | Cons |
|---|---|---|---|---|
| `detect-stack-drift` (scheduled) | Per-stack | No (on-demand) | Comprehensive; all property diffs | Must schedule; rate limited |
| Config rule `cfn-stack-drift-check` | Per-stack | Near-real-time | Config compliance; Security Hub | Reads last result only |
| Custom Config rule (Lambda) | Per-resource | Real-time | Catches changes as they happen | No stack-level drift; custom Lambda |
| Terraform `plan -detailed-exitcode` | Per-state | Pipeline-driven | Native to Terraform; CI/CD | Terraform resources only |
| Config Aggregator | Cross-account | Near-real-time | Single pane across accounts | Read-only; no remediation |

## Appendix B — Drift remediation decision tree

```
Is the stack production?
├─ Yes → Notify + human approval (aws:approve or Change Manager)
│        └─ Intentional hotfix? → update template
│           Unintentional?      → create change-set to revert
└─ No  → Remediation runbook tested?
        ├─ Yes → Auto-remediate via SSM (change-set re-apply)
        └─ No  → REVIEW_REQUIRED — test in sandbox first
```

## Recent AWS features (2024-2026)

- **StackSets auto-deployment (2024):** New accounts in an OU
  automatically receive StackSet deployments, including the drift
  detection Lambda.

- **Nested stack drift detection (2024-2025):** `detect-stack-drift` now
  recurses into nested stacks. Previously showed as `NOT_CHECKED`.

- **Config Conformance Pack for drift (2024):** Managed pack
  `operational-best-practices-for-cloudformation` includes drift rules.

- **Change-set drift preview (2025):** `create-change-set` shows which
  drifted properties will be reverted, before execution.

- **Step Functions Distributed Map (2024):** Native iteration for > 10,000
  stack-instances with concurrency control. Replaces Lambda + SQS.

- **Config Aggregator advanced query (2025):** `select-aggregate-resource-
  config` SQL queries for cross-account drift without Athena.

## Expert heuristic: drift remediation blast radius

Drift remediation on production stacks is the most dangerous governance
automation. Re-applying a template to "fix" drift can revert an
intentional hotfix, trigger resource replacement (downtime), or cascade
failures across dependent stacks.

> ALWAYS classify the stack (production vs non-production) before
> enabling auto-remediation. For production, require human approval.
> For non-production, validate the runbook in sandbox first.

**Stack classification techniques:**

| Technique | Mechanism | Limit |
|---|---|---|
| Stack name pattern | `prod-*` → approval | Name-based, fragile |
| Stack tags | `Environment: production` → manual | More robust; tag-driven |
| OU-based scoping | Prod OU → manual; Sandbox → auto | Strongest; org-level |
| Account isolation | Prod accounts excluded from auto | Complete isolation |
| Change Manager gate | All prod via Change Template | Human approval per execution |

**3-phase validation:**

1. **Sandbox — detect + auto-remediate:** Deploy full pipeline. Create
   deliberate drift. Verify detection → notification → remediation →
   `IN_SYNC`.
2. **Staging — detect + notify only:** Monitor drift patterns 1 week.
   Tune suppression rules for acceptable changes.
3. **Production — detect + notify only (permanent):** All remediation
   requires human-approved change-set. Never flip to auto without
   architecture review.

**Post-deploy alarms:** SSM Automation Executions Failed > 0 for the
remediation runbook. CFN drift status = DRIFTED for > 48 hours on
production stacks (detection fires but remediation never succeeds/approved).

**Surface in output:** `STACK_CLASS: <production | staging | dev |
sandbox>` and `REMEDIATION_MODE: <auto | approval-required | notify-only>`.
If `STACK_CLASS` is `production` and `REMEDIATION_MODE` is `auto`, flag
as UNSAFE.

## Domain

AWS CloudOps / Governance Automation — CloudFormation drift detection
and remediation.

## AWS documentation

- **CloudFormation drift detection** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-stack-drift.html
- **Config rule cloudformation-stack-drift-detection-check** — https://docs.aws.amazon.com/config/latest/developerguide/cloudformation-stack-drift-detection-check.html
- **CloudFormation StackSets** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/what-is-cfnstacksets.html
- **Config Aggregator** — https://docs.aws.amazon.com/config/latest/developerguide/aggregate-data.html
- **Config Conformance Packs** — https://docs.aws.amazon.com/config/latest/developerguide/conformance-packs.html
- **SSM Automation** — https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-automation.html
- **Terraform plan exit codes** — https://developer.hashicorp.com/terraform/cli/commands/plan#detailed-exitcode
- **Step Functions Distributed Map** — https://docs.aws.amazon.com/step-functions/latest/dg/concepts-asl-use-map-state-distributed.html
