# End-to-End Example: SSM Automation Runbook Deployment

A walkthrough showing how to use the `ssm-automation-deployer` skill
from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are creating an SSM Automation runbook that remediates EC2
instances using conditional branching. The runbook needs:

- Document name: RemediateEC2
- Schema version: 0.3 (required for aws:branch)
- Steps: DescribeInstances → aws:branch → Stop/Start/NoOp → Lambda notify
- Targets: resource group rg-prod-ec2
- Rate control: MaxConcurrency=10, MaxErrors=3
- Execution role: SSMAutomationRole (trust: ssm.amazonaws.com)
- SNS notification: arn:aws:sns:us-east-1:123456789012:ssm-alerts
- EventBridge schedule: NightlyRemediation (cron(0 2 ? * SUN *))

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-ssm-automation
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create an SSM Automation document RemediateEC2 that checks
      instance state and branches: if running stop it, if stopped
      start it. Use aws:branch. Targets via resource group
      rg-prod-ec2. Rate control MaxConcurrency 10 MaxErrors 3.
      Execution role SSMAutomationRole."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create an ssm automation document"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

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

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the execution role (if not existing)
aws iam create-role --role-name SSMAutomationRole \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ssm.amazonaws.com"},"Action":"sts:AssumeRole"}]}'

aws iam put-role-policy --role-name SSMAutomationRole \
  --policy-name SSMAutomationPermissions \
  --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["ec2:DescribeInstances","ec2:StopInstances","ec2:StartInstances","lambda:InvokeFunction","iam:PassRole"],"Resource":"*"}]}'

# Step 2: Create the SSM Automation document
aws ssm create-document \
  --name RemediateEC2 \
  --document-type Automation \
  --content file://remediate-ec2.json

# Step 3: Execute the runbook with targets and rate control
aws ssm start-automation-execution \
  --document-name RemediateEC2 \
  --targets '[{"Key":"ResourceGroup","Values":["rg-prod-ec2"]}]' \
  --target-parameter-name InstanceId \
  --max-concurrency "10" \
  --max-errors "3" \
  --automation-assume-role "arn:aws:iam::123456789012:role/SSMAutomationRole" \
  --notification-config '{"NotificationArn":"arn:aws:sns:us-east-1:123456789012:ssm-alerts","NotificationEvents":["Success","Failed"],"NotificationType":"Command"}'

# Step 4: Set up EventBridge scheduled execution
aws events put-rule --name "NightlyRemediation" \
  --schedule-expression "cron(0 2 ? * SUN *)"

aws events put-targets --rule "NightlyRemediation" \
  --targets '[{"Id":"SSMAutomation","Arn":"arn:aws:ssm:us-east-1:123456789012:automation-definition/RemediateEC2","RoleArn":"arn:aws:iam::123456789012:role/EventBridgeSSMRole"}]'
```

---

## Step 4 — Post-deployment verification

```bash
# Verify document exists
aws ssm describe-document --name RemediateEC2 \
  --query 'Document.{Name:Name,Type:DocumentType,Schema:SchemaVersion,Version:DocumentVersion}'

# Verify execution role trust policy
aws iam get-role --role-name SSMAutomationRole \
  --query 'Role.AssumeRolePolicyDocument'

# Verify EventBridge rule
aws events describe-rule --name NightlyRemediation \
  --query '{Name:Name,Schedule:ScheduleExpression,State:State}'

# Check recent automation executions
aws ssm describe-automation-executions \
  --filters Key=DocumentName,Values=RemediateEC2 \
  --query 'AutomationExecutionMetadataList[*].{ExecutionId:AutomationExecutionId,Status:AutomationExecutionStatus,Time:ExecutionStartTime}' \
  --max-results 5
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Execution role | Uses EC2 instance role | Separate role with ssm.amazonaws.com trust | Instance role is for SSM agent; execution role is for API calls |
| iam:PassRole | Missing | Included in permissions | aws:runInstances needs PassRole |
| Schema version | 0.1 (default) | 0.3 (required for aws:branch) | Branching requires 0.3+ |
| Rate control | Not set | MaxConcurrency + MaxErrors | Dynamic targets can match 100s of resources |
| SNS notifications | Not configured | Notification on Success/Failed | Failed automations go unnoticed without alerts |
| Target validation | Not checked | Resource group membership verified | Empty resource group = zero targets silently |
| EventBridge role | Not configured | Separate role with ssm:StartAutomationExecution | EventBridge needs permission to start automations |

---

## Related artifacts

- **Skill definition:** `skills/ssm-automation-deployer/SKILL.md`
- **Step actions and branching guide:** `skills/ssm-automation-deployer/references/step-actions-and-branching.md`
- **Execution role and targets guide:** `skills/ssm-automation-deployer/references/execution-role-and-targets.md`
- **Slash command:** `commands/aws/deploy-ssm-automation.md`
- **Eval suite:** `skills/ssm-automation-deployer/evals/evals.json`
- **Legacy test cases:** `skills/ssm-automation-deployer/eval/test-cases.yaml`
