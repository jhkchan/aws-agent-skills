---
description: Provision an AWS Systems Manager (SSM) Automation document (runbook) with production-grade defaults (document type, schema version, parameters, mainSteps with aws:executeAwsApi/aws:invokeLambdaFunction/aws:runInstances/aws:changeInstanceState/aws:sleep/aws:branch, targets via resource groups and tags, rate control, execution role trust policy, SNS notifications, document sharing, version management, nested runbook, EventBridge integration). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create ssm automation document"
  - "ssm automation runbook"
  - "aws:executeawsapi"
  - "aws:invokelambdafunction"
  - "aws:runinstances"
  - "aws:changeinstancestate"
  - "aws:branch"
  - "aws:sleep"
  - "ssm rate control"
  - "ssm concurrency"
  - "ssm error threshold"
  - "ssm automation execution role"
  - "ssm assume role"
  - "ssm resource group targets"
  - "ssm tag-based targets"
  - "ssm sns notification"
  - "eventbridge ssm automation"
  - "ssm scheduled automation"
  - "nested runbook"
  - "aws:executeautomation"
  - "ssm document version"
  - "ssm document sharing"
  - "ssm runbook conditional"
routes_to: ssm-automation-deployer
---

# /aws:deploy-ssm-automation

Activate the `ssm-automation-deployer` skill and provision an AWS
Systems Manager (SSM) Automation document with production-grade
defaults.

## What it does

The skill walks a 12-step provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Document type and schema version (Automation, 0.3 for branching)
2. Parameters (typed inputs)
3. mainSteps and action types (aws:executeAwsApi, aws:invokeLambdaFunction,
   aws:runInstances, aws:sleep, aws:changeInstanceState)
4. aws:branch conditional routing
5. Targets (resource groups, tags)
6. Rate control (concurrency, error threshold)
7. Automation execution role (trust: ssm.amazonaws.com)
8. SNS notifications (success/failure)
9. Document sharing and version management
10. Nested runbook pattern (aws:executeAutomation)
11. EventBridge integration (scheduled automations)
12. Recent features (multi-condition branch, cross-account, dry-run)

## When to use

- You need to create a new SSM Automation runbook.
- You are designing a multi-step remediation workflow.
- You need aws:branch conditional routing in a runbook.
- You need to configure rate control for fleet-wide operations.
- You need to set up the automation execution role.
- You need SNS notifications on automation success/failure.
- You want to schedule automations via EventBridge.
- You need nested runbook composition.

## When NOT to use

- **SSM Session Manager** — use session skills.
- **SSM Patch Manager** — use patch baseline/operator skills.
- **SSM Parameter Store** — use parameter skills.
- **SSM Run Command (one-off)** — use Command document skills.

## How to invoke

### Slash command

```
/aws:deploy-ssm-automation
```

Then provide: document name, schema version, parameters, mainSteps
(action types), targets (resource group or tags), rate control
(MaxConcurrency, MaxErrors), execution role name, SNS topic ARN,
EventBridge schedule (if applicable), and document sharing
preference.

### Natural language

Any of these routes to the same skill:

- "create an SSM Automation runbook for EC2 remediation"
- "set up an SSM document with aws:branch conditional routing"
- "create a nested runbook with aws:executeAutomation"
- "schedule an SSM automation via EventBridge"
- "configure rate control for an SSM Automation document"

### CLI routing

```bash
node cli/bin/cli.js route "create an ssm automation document"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create SSM
Automation runbooks. The output checklist feeds into verification
pipelines and audit skills.

## Example

```
You: /aws:deploy-ssm-automation

     Create an SSM Automation document "RemediateEC2" that checks
     instance state with aws:executeAwsApi and uses aws:branch to
     route: if running stop it, if stopped start it. Invoke Lambda
     "remediation-handler" after. Targets via resource group
     "rg-prod-ec2". Rate control: MaxConcurrency 10, MaxErrors 3.
     Execution role: SSMAutomationRole. SNS to
     arn:aws:sns:us-east-1:123456789012:ssm-alerts.

Skill:
  SSM_AUTOMATION: RemediateEC2 (Automation, schema 0.3)
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] mainSteps: 5 (aws:executeAwsApi, aws:branch, aws:changeInstanceState, aws:sleep, aws:invokeLambdaFunction)
    [✓] aws:branch: 1 (running→Stop, stopped→Start)
    [✓] Targets: resource group rg-prod-ec2
    [✓] Rate control: MaxConcurrency=10, MaxErrors=3
    [✓] Execution role: SSMAutomationRole (trust: ssm.amazonaws.com)
    [✓] SNS: arn:aws:sns:us-east-1:123456789012:ssm-alerts
  VERIFICATION_COMMANDS:
    aws ssm describe-document --name RemediateEC2
    aws iam get-role --role-name SSMAutomationRole
```

## References

- Skill definition: `skills/ssm-automation-deployer/SKILL.md`
- Step actions and branching: `skills/ssm-automation-deployer/references/step-actions-and-branching.md`
- Execution role and targets: `skills/ssm-automation-deployer/references/execution-role-and-targets.md`
- Eval suite: `skills/ssm-automation-deployer/evals/evals.json`
