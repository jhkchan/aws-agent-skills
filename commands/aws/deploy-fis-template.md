---
description: Provision an AWS Fault Injection Simulator (FIS) experiment template with production-grade defaults (eight fault actions, tag-based target scoping, CloudWatch alarm stop conditions, IAM role scoped to fault action on target resources, log group, experiment start and rollback, report generation). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create fis experiment template"
  - "deploy fis template"
  - "fault injection simulator"
  - "chaos experiment aws"
  - "aws:ec2:stop-instances"
  - "aws:ec2:terminate-instances"
  - "aws:ecs:drain-container-instances"
  - "aws:lambda:invoke"
  - "aws:network:disrupt-connectivity"
  - "aws:rds:failover-db-cluster"
  - "aws:s3:pause-bucket-access"
  - "aws:cloudwatch:put-metric-data"
  - "fis stop condition"
  - "fis iam role"
  - "fis target tags"
routes_to: fis-template-deployer
---

# /aws:deploy-fis-template

Activate the `fis-template-deployer` skill and provision an AWS Fault
Injection Simulator experiment template with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Experiment template anatomy (JSON structure)
2. Actions (the eight fault types: EC2 stop/terminate, ECS drain, Lambda
   invoke, network disrupt, RDS failover, S3 pause, CloudWatch metric)
3. Targets (resource tags = safest scope; selectionMode)
4. Stop conditions (CloudWatch alarm auto-abort)
5. IAM role configuration (trust policy + scoped permissions)
6. Log group and report generation
7. Create, start, and rollback
8. Recent features (template versioning, cross-account, Step Functions)

## When to use

- You need to create a FIS experiment template.
- You are configuring fault injection on EC2/ECS/RDS/Lambda/S3/network.
- You need to scope experiment targets via resource tags and filters.
- You need to set stop conditions (CloudWatch alarms) for auto-abort.
- You need to configure the FIS IAM role with scoped permissions.
- You need to start, monitor, or abort a FIS experiment.

## When NOT to use

- **AWS Resilience Hub** — readiness assessment, not fault injection.
- **Chaos Mesh** — EKS-native chaos tool (different ecosystem).
- **Gremlin / Litmus** — third-party chaos tools (not AWS FIS).
- **Game day orchestration** — use Step Functions or game-day skills
  that orchestrate multiple FIS experiments.

## How to invoke

### Slash command

```
/aws:deploy-fis-template
```

Then provide: action ID, target resource type and tags, stop condition
alarm ARN, IAM role ARN, log group, duration, region, tags.

### Natural language

Any of these routes to the same skill:

- "create a FIS experiment template to stop an EC2 instance"
- "configure fault injection with aws:network:disrupt-connectivity"
- "set up a chaos experiment on my ECS cluster"
- "create an RDS failover experiment template"
- "configure a FIS stop condition alarm"

### CLI routing

```bash
node cli/bin/cli.js route "create a fis experiment template"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create FIS
experiment templates. The output checklist feeds into verification
pipelines and downstream audit skills.

## Example

```
You: /aws:deploy-fis-template

     Create a FIS experiment template in us-east-1 account
     123456789012. Action aws:ec2:stop-instances with startAfter
     5m. Target EC2 instances tagged FIS_Target=enabled,
     selectionMode COUNT(1). Stop condition alarm FIS-CPU-High.
     Role FISExperimentRole.

Skill:
  FIS_TEMPLATE: EXTVAR123456 — aws:ec2:stop-instances on EC2 tagged FIS_Target=enabled
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Action: aws:ec2:stop-instances — startAfter: 5m
    [✓] Target: tag FIS_Target=enabled (COUNT 1)
    [✓] Stop condition: FIS-CPU-High alarm
    [✓] IAM role: ec2:StopInstances scoped to FIS_Target tag
  VERIFICATION_COMMANDS:
    aws fis get-experiment-template --id EXTVAR123456 --region us-east-1
    aws cloudwatch describe-alarms --alarm-names FIS-CPU-High
```

## References

- Skill definition: `skills/fis-template-deployer/SKILL.md`
- Actions and targets guide: `skills/fis-template-deployer/references/actions-and-targets.md`
- IAM and stop conditions guide: `skills/fis-template-deployer/references/iam-and-stop-conditions.md`
- Eval suite: `skills/fis-template-deployer/evals/evals.json`
