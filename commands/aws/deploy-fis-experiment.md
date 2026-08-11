---
description: Provision AWS Fault Injection Service (FIS) experiment templates with production-safe defaults — EC2/ECS/EKS/RDS/Aurora/Lambda/network actions, CloudWatch alarm stop conditions, least-privilege IAM role, logging to S3 + CloudWatch Logs. Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create fis experiment"
  - "fis experiment template"
  - "fault injection experiment"
  - "chaos engineering drill"
  - "game day experiment"
  - "aurora failover test"
  - "rds failover experiment"
  - "eks pod disruption"
  - "eks pod kill"
  - "ecs stop task experiment"
  - "ec2 stop instances experiment"
  - "ec2 send api error"
  - "network blackhole experiment"
  - "network latency injection"
  - "network packet loss"
  - "lambda invoke async experiment"
  - "fis stop condition"
  - "alarm-based stop"
  - "fis iam role"
  - "fis budget duration"
routes_to: fis-experiment-deployer
---

# /aws:deploy-fis-experiment

Activate the `fis-experiment-deployer` skill and provision AWS Fault
Injection Service experiment templates with production-safe defaults.

## What it does

The skill walks an 8-step provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Confirm experiment intent + blast radius
2. Scope targets via tags / ARNs / filters
3. Choose fault action(s) + parameters
4. Configure stop conditions (CloudWatch alarms)
5. Create IAM execution role with least privilege (tag-scoped)
6. Configure experiment logging (S3 + CloudWatch Logs)
7. Set budgetDuration + (optional) schedule
8. Verify via `get-experiment-template` + emit checklist

Supported fault actions:
- `aws:ec2:stop-instances`, `aws:ec2:send-api-error`, `aws:ec2:terminate-instances`
- `aws:ecs:stop-task`
- `aws:eks:pod-cleanup` (via SSM kubectl on worker node)
- `aws:network:disrupt-connectivity` (via SSM — blackhole, latency, loss)
- `aws:rds:failover-db-cluster` (Aurora)
- `aws:lambda:invoke-async`

## When to use

- You are running a game day, DR drill, or resilience gate check.
- You need an FIS experiment template targeting a specific resource subset.
- You want CloudWatch alarms as stop conditions for an automatic halt.
- You need a least-privilege IAM role scoped by tag for the FIS execution.
- You want experiment logging to S3 and CloudWatch Logs.
- You want to validate Aurora failover, EKS pod recovery, or network resilience.

## How to invoke

### Slash command

```
/aws:deploy-fis-experiment
```

Then provide: experiment name, target resources (tags/ARNs/filters),
fault action(s) and parameters, stop condition alarm name(s), IAM role
name, logging destinations, and budgetDuration.

### Natural language

Any of these routes to the same skill:

- "create an FIS experiment to stop a canary instance"
- "set up an aurora failover drill"
- "build a network blackhole experiment"
- "configure an EKS pod disruption template"
- "provision chaos engineering for game day"

### CLI routing

```bash
node cli/bin/cli.js route "create fis experiment template"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create or update
an FIS experiment template. The output checklist feeds into
verification pipelines and operate skills (start/stop experiment) and
into audit skills for post-game-day review.

## Example

```
You: /aws:deploy-fis-experiment

     Provision an FIS experiment template called ec2-stop-canary
     targeting instances tagged fis-target=true (1 instance). Stop
     for 60s with alarm fis-stop-error-rate as stop condition.
     budgetDuration 2 minutes.

Skill:
  EXPERIMENT_TEMPLATE: ec2-stop-canary (action: aws:ec2:stop-instances, target: fis-target=true)
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Intent + blast radius: Stop one canary instance for 60s to validate auto-recovery, blast radius 1 instance
    [✓] Target scoped: resourceTags fis-target=true (1 instance i-0abc123)
    [✓] Action(s): aws:ec2:stop-instances (duration PT60S)
    [✓] Stop condition(s): fis-stop-error-rate (state: OK)
    [✓] IAM role: fis-execution-role (fis trust, ec2:StopInstances scoped to aws:ResourceTag/fis-target=true)
    [✓] Logging: S3 fis-logs-111111111111 + CloudWatch Logs /aws/fis/ec2-stop-canary
    [✓] budgetDuration: PT2M (rationale: 2x the 60s stop action for rollback margin)
  VERIFICATION_COMMANDS:
    aws fis get-experiment-template --id <TEMPLATE_ID>
    aws ec2 describe-instances --filters Name=tag:fis-target,Values=true
    aws cloudwatch describe-alarms --alarm-names fis-stop-error-rate
    ...
```

## References

- Skill definition: `skills/fis-experiment-deployer/SKILL.md`
- Fault action catalog: `skills/fis-experiment-deployer/references/fault-action-catalog.md`
- IAM + logging templates: `skills/fis-experiment-deployer/references/iam-and-logging-templates.md`
- Eval suite: `skills/fis-experiment-deployer/evals/evals.json`
