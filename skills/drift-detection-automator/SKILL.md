---
name: drift-detection-automator
description: Designs and implements automated CloudFormation drift detection workflows across single-account and multi-account environments. Wires scheduled EventBridge rules for periodic drift detection runs, AWS Config rules for individual resource drift, Lambda comparison functions for desired-vs-actual state analysis, SNS notifications with severity-based routing, SSM Automation remediation (CloudFormation update or custom Lambda), multi-account via CloudFormation StackSets, drift suppression for known-acceptable changes, drift report export to S3 with Athena query, IaC pipeline integration (Terraform plan as drift check), and Config Aggregator cross-account visibility. Emits AUTOMATION_DEPLOYED with the full detection+notification pipeline or REVIEW_REQUIRED with the specific gap. Use when building drift detection automation, scheduling drift checks, integrating drift detection with IaC pipelines, or setting up multi-account drift visibility.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Gemini). No AWS CLI required for offline workflow design. Live deployment uses aws cloudformation detect-stack-drift, describe-stack-drift-detection-status, describe-stack-resource-drifts, aws configservice put-config-rule, describe-config-rules, aws events put-rule, put-targets, aws lambda create-function, aws sns create-topic, subscribe, aws ssm create-document, start-automation-execution, aws cloudformation...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '4'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Governance
  task_type: automate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: AUTOMATION_DEPLOYED | REVIEW_REQUIRED
  when_to_use: Building automated CloudFormation drift detection, scheduling periodic drift checks via EventBridge, wiring Config rules for resource drift, designing Lambda desired-vs-actual comparison functions, setting up SSM Automation remediation for drifted stacks, configuring multi-account drift detection via StackSets, suppressing known-acceptable drift, exporting drift reports to S3/Athena, integrating drift checks into IaC pipelines (Terraform plan), or establishing Config Aggregator cross-account drift visibility.
  when_not_to_use: Investigating a specific CloudFormation stack failure or rollback (use cloudformation-stack-troubleshooter or cloudformation-stack- rollback-troubleshooter). Deploying new CloudFormation stacks (use the deployer family). Troubleshooting drift on a single stack without automation (use cloudformation-drift-troubleshooter). Terraform state management and import belong to the Terraform toolchain.
  activation_triggers: automate drift detection, schedule drift check, CloudFormation drift automation, Config rule resource drift, drift detection EventBridge, Lambda desired vs actual, drift remediation SSM, drift suppression, multi-account drift StackSets, drift report S3 Athena, Terraform plan drift check, Config Aggregator drift
  invocation_schema: 'Input: either (a) a CloudFormation stack name or set of stacks plus desired detection cadence, OR (b) a drift automation requirement ("detect drift hourly and notify", "auto-remediate drift on non-production stacks"). Output: deterministic DRIFT_AUTOMATION block per stack set — DETECTION/COMPARISON/NOTIFICATION/REMEDIATION/ INTEGRATION/SAFETY/VERDICT — where VERDICT is AUTOMATION_DEPLOYED (pipeline ready) or REVIEW_REQUIRED (specific gap cited).'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: AWS CloudFormation, drift detection, stack drift, resource drift, EventBridge scheduled, AWS Config, Config Aggregator, desired state, actual state, Lambda comparison, SNS notification, SSM Automation, CloudFormation StackSets, drift suppression, drift report, Amazon Athena, Terraform plan, IaC pipeline, governance automation
  tags: cloudformation, drift-detection, config, eventbridge, lambda, governance, ssm-automation, stacksets, automate
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
Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

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
Moved verbatim to [references/drift-comparison-and-remediation.md](references/drift-comparison-and-remediation.md) - load on demand (see References below).

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
Moved verbatim to [references/drift-reporting-and-athena.md](references/drift-reporting-and-athena.md) - load on demand (see References below).

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
Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

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
Moved verbatim to [references/worked-examples.md](references/worked-examples.md) - load on demand (see References below).

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
Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) - load on demand (see References below).

## Appendix A — Drift detection methods comparison
Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## Appendix B — Drift remediation decision tree
Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## Recent AWS features (2024-2026)
Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## Expert heuristic: drift remediation blast radius
Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## References (load on demand)

- [references/worked-examples.md](references/worked-examples.md) — secondary worked example (REVIEW_REQUIRED) moved from SKILL.md
- [references/advanced-patterns.md](references/advanced-patterns.md) — Step-0 expert knowledge, appendices, GitHub Actions workflow, 2024-2026 features moved from SKILL.md
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — pre-flight safety checks moved from SKILL.md
- [references/drift-comparison-and-remediation.md](references/drift-comparison-and-remediation.md) — SSM Automation change-set runbook moved from SKILL.md
- [references/drift-reporting-and-athena.md](references/drift-reporting-and-athena.md) — drift report export + Athena DDL moved from SKILL.md

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
