---
name: ssm-automation-deployer
description: 'Provisions AWS Systems Manager (SSM) Automation documents with production defaults: document type (Automation, Command, Session), schema version, parameters, mainSteps (aws:executeAwsApi, aws:runInstances, aws:invokeLambdaFunction, aws:sleep, aws:changeInstanceState, aws:branch), targets via resource groups and tags, rate control (concurrency, error threshold), automation execution role trust policy, SNS notifications, document sharing, version management, nested runbook, and EventBridge integration. Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating an SSM Automation runbook, designing multi-step remediation workflows, setting up aws:branch conditional routing, configuring rate control, or integrating EventBridge schedules. Triggers: create SSM Automation document, SSM runbook, aws:executeAwsApi, aws:invokeLambdaFunction, aws:branch, SSM rate control, SSM execution role, EventBridge SSM automation, nested runbook, SSM document version management.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with ssm, iam, lambda, events, and sns access. Works with Terraform aws_ssm_document resources and CloudFormation AWS::SSM::Document templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Management
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, ssm, automation, runbook, cloudops, deploy, management, provisioning, remediation, eventbridge
  dependencies: aws-orchestrator
  keywords: aws, systems manager, ssm, automation, runbook, document, cloudops, deploy, provisioning, aws:executeAwsApi, aws:invokeLambdaFunction, aws:runInstances, aws:changeInstanceState, aws:sleep, aws:branch, rate control, concurrency, error threshold, resource groups, targets, execution role, sns notification, eventbridge, nested runbook, version management
  when_to_use: Invoke when the user wants to create an SSM Automation document (runbook), design multi-step remediation or operational workflows, use aws:branch for conditional step routing, configure rate control (concurrency and error threshold) for target execution, set up the automation execution role with correct trust policy, wire SNS notifications on success/failure, share documents (private vs public), manage document versions, build nested runbooks, or integrate with EventBridge for scheduled automations. Do NOT invoke for SSM Session Manager (use session skills), SSM Patch Manager (use patch skills), or SSM Parameter Store (use parameter skills).
---

# SSM Automation Deployer

An AWS CloudOps agent skill that provisions AWS Systems Manager (SSM)
Automation documents with correct production defaults. The skill walks
the operator through document type selection, schema version,
parameter definition, mainSteps sequencing (aws:executeAwsApi,
aws:runInstances, aws:invokeLambdaFunction, aws:sleep,
aws:changeInstanceState, aws:branch), target collection via resource
groups and tags, rate control (concurrency, error threshold),
automation execution role trust policy, SNS notifications on
success/failure, document sharing and version management, nested
runbook patterns, and EventBridge integration for scheduled
automations, captures all design decisions, and emits a
READY_TO_DEPLOY checklist with verification commands.

## Activation keywords

create SSM Automation document, SSM runbook, aws:executeAwsApi,
aws:invokeLambdaFunction, aws:branch conditional, SSM rate control,
SSM automation execution role, EventBridge SSM automation, nested
runbook, SSM document version management, aws:runInstances,
aws:changeInstanceState.

## STRICT output contract

When this skill is invoked with an SSM-Automation-provisioning
request (create a runbook, design a multi-step workflow, configure
rate control or targets, wire SNS notifications, integrate
EventBridge, or a partial configuration), the agent MUST respond with
the READY_TO_DEPLOY checklist defined in the "Output format" section
using the literal all-caps labels `SSM_AUTOMATION:`, `VERDICT:`,
`CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface the
checklist with prose, headings, or disclaimers — emit the block as
the first lines of the response. This contract is what assertion-
based evals and downstream provisioning pipelines rely on; deviating
from the literal labels breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Document type and schema version | Core document setup |
| Step 2 — Parameters | Input definition |
| Step 3 — mainSteps and action types | Workflow steps |
| Step 4 — aws:branch conditional routing | Conditional logic |
| Step 5 — Targets (resource groups, tags) | Target collection |
| Step 6 — Rate control | Concurrency and error threshold |
| Step 7 — Automation execution role | IAM trust policy |
| Step 8 — SNS notifications | Success/failure alerts |
| Step 9 — Document sharing and versions | Private vs public |
| Step 10 — Nested runbook pattern | Composability |
| Step 11 — EventBridge integration | Scheduled automations |
| Step 12 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/step-actions-and-branching.md | Step action detail |
| references/execution-role-and-targets.md | IAM + target collection detail |

## Mindset

**One-line takeaway:** An SSM Automation document (runbook) is a
JSON/YAML document that defines a sequence of steps (actions) that
SSM executes on your behalf. Each step uses a predefined action type
(aws:executeAwsApi, aws:invokeLambdaFunction, aws:runInstances,
aws:sleep, aws:changeInstanceState, aws:branch). The execution role
(trust policy: `ssm.amazonaws.com`) grants SSM permission to perform
these actions. Rate control governs how many targets execute
concurrently and when to stop on errors.

Three misconceptions dominate SSM Automation misdesign at provisioning
time:

- **"The execution role is the same as the instance role."** It is
  NOT. The automation execution role (assume role) is assumed by the
  SSM service (`ssm.amazonaws.com`) to execute API calls within the
  runbook steps. The instance role (instance profile) is attached to
  EC2 instances for the SSM agent. These are separate roles with
  separate trust policies.

- **"aws:branch is just a conditional display flag."** It is NOT.
  `aws:branch` is a step action that evaluates a conditional and
  routes execution to different steps based on the evaluation. It is
  the ONLY way to implement conditional branching in an Automation
  runbook. Without it, all steps execute linearly.

- **"Targets are just a resource IDs list."** They are NOT. Targets
  can be explicit resource IDs, or dynamically collected via resource
  groups or tag-based queries. Dynamic targets enable the runbook to
  operate on resources that match a tag or resource group at execution
  time, not just at authoring time. Rate control (concurrency, error
  threshold) applies to the target set.

## Configuration dependency graph (novel heuristic)

SSM Automation document configurations are NOT independent. The
execution role must exist and have the correct trust policy before
the document can execute. Targets must be collectable. Rate control
must be set within service quotas. Use this graph to sequence
provisioning.

| Configuration | Hard dependencies | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Document type (Automation) | None — chosen at creation | Cannot change type; must recreate | determines action types available |
| Schema version | document type chosen | 0.3 required for aws:branch | step definition syntax |
| Parameters | schema version chosen | typed; defaults applied if not provided | runtime input binding |
| mainSteps | parameters defined | steps execute in order; outputs chain | the workflow |
| aws:branch steps | steps defined before/after branch | missing NextStep targets cause failure | conditional routing |
| Targets (resource groups) | resource group exists | empty group = zero targets at runtime | dynamic target collection |
| Targets (tags) | tags exist on resources | no match = zero targets | dynamic target collection |
| Rate control (concurrency) | targets defined | concurrency above 10 needs quota | parallelism across targets |
| Rate control (error threshold) | targets defined | stops execution when exceeded | blast radius limitation |
| Automation execution role | IAM role with trust for ssm.amazonaws.com | role passed at execution; missing = failure | SSM permission to perform API calls |
| SNS notification | SNS topic exists | notification on success/failure | execution status alerts |
| Document sharing | document exists | public requires AWS review | cross-account access |
| Document version | document exists | each update = new version; default used | version management |
| EventBridge schedule | document + execution role exist | EventBridge triggers start-automation-execution | scheduled automations |

**The execution-role-trust-policy row is the one a baseline model
misses.** The automation execution role must have a trust policy
allowing `ssm.amazonaws.com` to assume it. The role's permissions
must cover every API call made in every step.

**Cross-dependency gotchas:**
- The execution role is passed at execution time
  (`--automation-assume-role`), not at document creation.
- `aws:branch` requires schema version 0.3+.
- Rate control concurrency default limit is 10 (soft quota).
- Dynamic targets are evaluated at execution time, not creation time.
- Public document sharing requires AWS review and approval.

## Expert heuristic: step sequencing with aws:branch conditional

A baseline model creates a linear sequence of steps. The correct
heuristic recognizes that real operational workflows require
conditional branching — execute step A only if a condition is met,
otherwise skip to step B.

```text
Step flow with aws:branch:

  Step 1: aws:executeAwsApi (DescribeInstances)
     → outputs instance state
     ↓
  Step 2: aws:branch
     ├── State == "running"  → NextStep: StopStep
     ├── State == "stopped"  → NextStep: StartStep
     └── Default             → NextStep: NoOpStep
     ↓
  Step 3/4/5: respective action (isEnd: true)

aws:branch requires schema version 0.3+
```

**Key implication:** without `aws:branch`, every runbook is linear.
Conditional routing is essential for remediation workflows (if X
then Y else Z), idempotent operations, and multi-tenant operations.

## Expert heuristic: execution role trust policy

The automation execution role is assumed by SSM to execute API calls
in runbook steps. Trust policy MUST allow `ssm.amazonaws.com`.

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "ssm.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

**The role's permissions must cover every API call in every step.**
For example, if Step 1 calls `ec2:DescribeInstances` and Step 2 calls
`ec2:StopInstances`, the role's permission policy must include both.
**`iam:PassRole` is needed** if any step passes a role to a service
(e.g., `aws:runInstances` with an instance profile).

## Expert heuristic: target collection via resource groups

Target-collection modes and rate-control implications moved to
[references/execution-role-and-targets.md](references/execution-role-and-targets.md) (load on demand).

## Prerequisites (verify before provisioning)

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Document name and type | Required at creation | Confirm (type = Automation) |
| Execution role exists | SSM assumes this role to run steps | `aws iam get-role --role-name <role>` |
| Execution role trust policy | Trust must allow ssm.amazonaws.com | `aws iam get-role --query 'Role.AssumeRolePolicyDocument'` |
| Execution role permissions | Every API call in every step must be allowed | Review role policy against step actions |
| SNS topic exists (if notifications) | SNS ARN for success/failure alerts | `aws sns get-topic-attributes --topic-arn <arn>` |
| Resource group exists (if dynamic targets) | Target collection | `aws resource-groups get-group --group-name <name>` |
| Tags exist (if tag-based targets) | Target collection | `aws resourcegroupstaggingapi get-resources` |
| Lambda function exists (if invoke step) | Step invokes Lambda | `aws lambda get-function --function-name <name>` |
| Schema version 0.3+ (if aws:branch) | Branching requires 0.3+ | Confirm in document JSON |
| EventBridge rule (if scheduled) | Schedule trigger | `aws events describe-rule --name <name>` |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Document type and schema version

| Document type | Use case | Actions |
|---|---|---|
| Automation | Multi-step workflows (remediation, deployment) | aws:executeAwsApi, aws:runInstances, aws:invokeLambdaFunction, aws:sleep, aws:changeInstanceState, aws:branch, aws:assertAwsResourceProperty, aws:waitForResourceProperty |
| Command | Run command on managed instances | aws:runShellScript, aws:runPowerShellScript |
| Session | Configure Session Manager | Session-type configurations |

**For Automation runbooks, use schema version 0.3** (required for
`aws:branch`).

## Step 2 — Parameters

```yaml
parameters:
  InstanceId:
    type: String
    description: "EC2 instance ID to remediate"
    allowedPattern: "^i-[a-f0-9]+$"
  ActionType:
    type: String
    allowedValues: [Stop, Start, Restart]
    default: Restart
```

## Step 3 — mainSteps and action types

Each step uses a predefined action type. Steps execute in order;
outputs chain to later steps via `{{ StepName.OutputName }}`.

| Action | Description | Key inputs |
|---|---|---|
| aws:executeAwsApi | Call any AWS API | Service, Api, + params |
| aws:runInstances | Launch EC2 instances | ImageId, InstanceType, MinCount, MaxCount |
| aws:invokeLambdaFunction | Invoke Lambda | FunctionName, Payload |
| aws:sleep | Wait a duration | Duration (ISO 8601, e.g., "PT30S") |
| aws:changeInstanceState | Change EC2 state | InstanceIds, DesiredState |
| aws:branch | Conditional routing | Choices (NextStep + Condition), Default |
| aws:assertAwsResourceProperty | Assert property | assertions |
| aws:waitForResourceProperty | Wait until match | PropertySelector, DesiredValues |

## Step 4 — aws:branch conditional routing

```yaml
  - name: BranchOnState
    action: aws:branch
    inputs:
      Choices:
        - NextStep: StopInstance
          Condition: "{{ CheckState.State == 'running' }}"
        - NextStep: StartInstance
          Condition: "{{ CheckState.State == 'stopped' }}"
      Default: NoActionNeeded
```

Each choice routes to a different step. `Default` is the fallback.
Steps can end with `isEnd: true` to terminate the runbook.

## Step 5 — Targets (resource groups, tags)

```bash
# Resource group targets
aws ssm start-automation-execution \
  --document-name "RemediateEC2" \
  --targets '[{"Key":"ResourceGroup","Values":["rg-prod-ec2"]}]' \
  --target-parameter-name "InstanceId" \
  --automation-assume-role "arn:aws:iam::123456789012:role/SSMAutomationRole"

# Tag-based targets
aws ssm start-automation-execution \
  --document-name "RemediateEC2" \
  --targets '[{"Key":"tag:Environment","Values":["production"]}]' \
  --target-parameter-name "InstanceId" \
  --automation-assume-role "arn:aws:iam::123456789012:role/SSMAutomationRole"
```

## Step 6 — Rate control

| Parameter | Description | Example |
|---|---|---|
| MaxConcurrency | Max parallel executions (count or %) | "10" |
| MaxErrors | Stop when error count exceeds (count or %) | "3" |

```bash
aws ssm start-automation-execution \
  --document-name "PatchProduction" \
  --targets '[{"Key":"tag:Environment","Values":["production"]}]' \
  --target-parameter-name "InstanceId" \
  --max-concurrency "10" \
  --max-errors "3" \
  --automation-assume-role "arn:aws:iam::123456789012:role/SSMAutomationRole"
```

## Step 7 — Automation execution role

```bash
# Create role with SSM trust
aws iam create-role --role-name SSMAutomationRole \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ssm.amazonaws.com"},"Action":"sts:AssumeRole"}]}'

# Attach permissions covering ALL step API calls
aws iam put-role-policy --role-name SSMAutomationRole \
  --policy-name SSMAutomationPermissions \
  --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["ec2:DescribeInstances","ec2:StopInstances","ec2:StartInstances","lambda:InvokeFunction","iam:PassRole"],"Resource":"*"}]}'
```

Pass at execution: `--automation-assume-role "arn:aws:iam::...:role/SSMAutomationRole"`

## Step 8 — SNS notifications

```bash
aws ssm start-automation-execution \
  --document-name "MyRunbook" \
  --automation-assume-role "arn:aws:iam::123456789012:role/SSMAutomationRole" \
  --notification-config '{"NotificationArn":"arn:aws:sns:us-east-1:123456789012:ssm-alerts","NotificationEvents":["Success","Failed","TimedOut"],"NotificationType":"Command"}'
```

## Step 9 — Document sharing and version management

```bash
# Share with specific accounts
aws ssm modify-document-permission --name "MyRunbook" \
  --permission-type "Share" --account-ids-to-add '["999999999999"]'

# Update document (creates new version)
aws ssm update-document --name "MyRunbook" --content file://runbook-v2.json

# Set default version
aws ssm update-document-default-version --name "MyRunbook" --document-version "2"
```

**Public sharing requires AWS review and approval.**

## Step 10 — Nested runbook pattern

```yaml
  - name: InvokeChildRunbook
    action: aws:executeAutomation
    inputs:
      DocumentName: "ChildRemediation"
      RuntimeParameters:
        InstanceId: "{{ InstanceId }}"
```

## Step 11 — EventBridge integration

```bash
aws events put-rule --name "NightlyPatchAutomation" \
  --schedule-expression "cron(0 2 ? * SUN *)"

aws events put-targets --rule "NightlyPatchAutomation" \
  --targets '[{"Id":"SSMAutomation","Arn":"arn:aws:ssm:us-east-1:123456789012:automation-definition/PatchProduction","RoleArn":"arn:aws:iam::123456789012:role/EventBridgeSSMRole","Input":"{\"DocumentName\":\"PatchProduction\",\"Targets\":[{\"Key\":\"tag:Environment\",\"Values\":[\"production\"]}]}"}]'
```

## Step 12 — Recent features

Recent SSM Automation features (multi-condition aws:branch, dynamic
parameters, cross-account, per-step metrics, dry-run) moved to [references/advanced-patterns.md](references/advanced-patterns.md).

## NEVER do these things

1. **NEVER conflate the execution role with the instance role.** The
   automation execution role is assumed by `ssm.amazonaws.com`. The
   instance role is attached to EC2 instances. Separate roles.

2. **NEVER omit `iam:PassRole` from the execution role.** If any step
   passes a role to a service (e.g., `aws:runInstances`), the
   execution role needs `iam:PassRole`.

3. **NEVER use schema version below 0.3 for runbooks with
   `aws:branch`.** Branching requires 0.3+.

4. **NEVER forget rate control on dynamic targets.** Dynamic targets
   can match hundreds of resources. Without rate control, automation
   may exceed quotas or cause cascading failures.

5. **NEVER hardcode resource IDs in a production runbook.** Use
   parameters for reusability.

6. **NEVER assume dynamic targets always return results.** A resource
   group may be empty. Always validate target count.

7. **NEVER publish a document as public without AWS review.** Public
   sharing requires approval.

8. **NEVER forget to set the default document version after updating.**
   Without setting default, executions use the old version.

9. **NEVER pass the execution role at document creation time.** The
   role ARN is passed at execution time.

10. **NEVER create a production runbook without SNS notifications.**
    Failed automations go unnoticed without SNS alerts.

## Output format

```text
SSM_AUTOMATION: <document-name> (Automation, schema <version>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Document name: <name>
  [✓|✗] Document type: Automation
  [✓|✗] Schema version: <0.3>
  [✓|✗] Parameters: <count> (<key params>)
  [✓|✗] mainSteps: <count> steps (<action-type list>)
  [✓|✗] aws:branch steps: <count> (conditional routing)
  [✓|✗] Targets: explicit IDs | resource group <name> | tags <key=value>
  [✓|✗] Rate control: MaxConcurrency=<value>, MaxErrors=<value>
  [✓|✗] Execution role: <role-name> (trust: ssm.amazonaws.com)
  [✓|✗] Execution role permissions: cover all step actions
  [✓|✗] SNS notification: <topic-arn> (events: <event-list>)
  [✓|✗] Document sharing: Private | Shared (<account-ids>) | Public
  [✓|✗] Document version: <version> (default)
  [✓|✗] Nested runbook: yes (<child-document>) | no
  [✓|✗] EventBridge schedule: <rule-name> (<schedule>) | none
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws ssm describe-document --name <document-name>
  aws iam get-role --role-name <role-name>
  aws ssm get-document --name <document-name> --document-version <version>
```

### Worked example — EC2 remediation runbook with branching

```text
SSM_AUTOMATION: RemediateEC2 (Automation, schema 0.3)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Document name: RemediateEC2
  [✓] Document type: Automation
  [✓] Schema version: 0.3
  [✓] Parameters: InstanceId (String), ActionType (String, default Restart)
  [✓] mainSteps: 5 steps (aws:executeAwsApi, aws:branch, aws:changeInstanceState, aws:sleep, aws:invokeLambdaFunction)
  [✓] aws:branch steps: 1 (BranchOnState: running→Stop, stopped→Start)
  [✓] Targets: resource group rg-prod-ec2
  [✓] Rate control: MaxConcurrency=10, MaxErrors=3
  [✓] Execution role: SSMAutomationRole (trust: ssm.amazonaws.com)
  [✓] Execution role permissions: ec2:DescribeInstances, ec2:StopInstances, ec2:StartInstances, lambda:InvokeFunction, iam:PassRole
  [✓] SNS notification: arn:aws:sns:us-east-1:123456789012:ssm-alerts (events: Success, Failed)
  [✓] Document sharing: Private
  [✓] Document version: 1 (default)
  [✓] Nested runbook: no
  [✓] EventBridge schedule: NightlyRemediation (cron(0 2 ? * SUN *))
  [✓] Tags: Environment=production, Owner=cloudops
VERIFICATION_COMMANDS:
  aws ssm describe-document --name RemediateEC2
  aws iam get-role --role-name SSMAutomationRole
  aws ssm get-document --name RemediateEC2 --document-version 1
```

## Error handling

Error-handling deep dives (AccessDenied, InvalidAssumeRole, branch
mis-evaluation, zero targets, throttling) moved to [references/error-handling.md](references/error-handling.md).

## References (load on demand)

- [references/step-actions-and-branching.md](references/step-actions-and-branching.md) — Step action syntax, inputs, and aws:branch conditional detail.
- [references/execution-role-and-targets.md](references/execution-role-and-targets.md) — Execution role trust policy and permissions; resource-group/tag target collection and rate control.
- [references/advanced-patterns.md](references/advanced-patterns.md) — Recent SSM Automation features (moved from Step 12).
- [references/error-handling.md](references/error-handling.md) — Execution failure deep dives (moved from Error handling).

## Domain

AWS CloudOps / Systems Manager Automation Document Provisioning &
Operational Runbook Automation.

## AWS documentation

- **SSM Automation** — https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-automation.html
- **Automation actions** — https://docs.aws.amazon.com/systems-manager/latest/userguide/automation-actions.html
- **aws:branch** — https://docs.aws.amazon.com/systems-manager/latest/userguide/automation-action-branch.html
- **Execution role** — https://docs.aws.amazon.com/systems-manager/latest/userguide/automation-setup-iam.html
- **Rate control** — https://docs.aws.amazon.com/systems-manager/latest/userguide/automation-rate-control.html
- **Document sharing** — https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-ssm-docs.html
- **EventBridge integration** — https://docs.aws.amazon.com/systems-manager/latest/userguide/monitoring-scheduled-events.html
