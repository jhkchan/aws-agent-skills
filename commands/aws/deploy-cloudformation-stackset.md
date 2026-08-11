---
description: Provision an AWS CloudFormation StackSet with production-grade defaults (SERVICE_MANAGED or SELF_MANAGED permission model, OU/account deployment targets, operation preferences, managed execution, drift detection). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create stackset"
  - "cloudformation stackset"
  - "deploy stackset"
  - "service managed stackset"
  - "self managed stackset"
  - "stackset organizations"
  - "stackset drift detection"
  - "stack instances"
  - "deploy template multiple accounts"
  - "stackset operation preferences"
  - "failure tolerance"
  - "max concurrent stackset"
  - "nested stacks vs stacksets"
  - "managed execution stackset"
  - "iac generator cloudformation"
routes_to: cloudformation-stackset-deployer
---

# /aws:deploy-cloudformation-stackset

Activate the `cloudformation-stackset-deployer` skill and provision an
AWS CloudFormation StackSet with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Permission model (SELF_MANAGED vs SERVICE_MANAGED)
2. Deployment targets (OUs, accounts, regions)
3. StackSet creation (template, parameters, capabilities)
4. Operation preferences (failure tolerance, concurrency)
5. Stack instances (deploy, managed execution)
6. Drift detection (per-instance and StackSet-level)
7. StackSets vs nested stacks
8. Update and delete operations
9. Recent features (StackSet drift, IaC generator)

## When to use

- You need to deploy a CloudFormation template across many accounts
  and/or regions.
- You are choosing between SELF_MANAGED and SERVICE_MANAGED.
- You are targeting organizational units for auto-deployment.
- You need to tune operation preferences (failure tolerance, max
  concurrent accounts/regions).
- You want managed execution with continuous drift detection.
- You need to generate CloudFormation templates from existing
  resources via the IaC generator.

## When NOT to use

- **Single-account, single-region stacks** — use
  `aws cloudformation deploy` directly.
- **Drift detection on a standalone stack** — use
  `cloudformation-drift-troubleshooter`.
- **Raw stack failures** — use `cloudformation-stack-troubleshooter`.

## How to invoke

### Slash command

```
/aws:deploy-cloudformation-stackset
```

Then provide: StackSet name, permission model, template source
(file or S3 URL), deployment targets (OU IDs or account list),
regions, capabilities, parameters, operation preferences,
managed execution setting, tags.

### Natural language

Any of these routes to the same skill:

- "create a service-managed stackset for OU ou-abc-12345678"
- "deploy a stackset across 50 accounts with tuned operation preferences"
- "enable managed execution and drift detection on my stackset"
- "create a self-managed stackset with admin and execution roles"

### CLI routing

```bash
node cli/bin/cli.js route "create a cloudformation stackset"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create or update
CloudFormation StackSets for multi-account/multi-region deployments.
The output checklist feeds into verification pipelines and downstream
governance skills.

## Example

```
You: /aws:deploy-cloudformation-stackset

     Create a SERVICE_MANAGED StackSet named baseline-iam-roles
     targeting OU ou-abc-12345678 across us-east-1, us-west-2,
     eu-west-1. Template at s3://my-bucket/templates/baseline-iam.yaml.
     Enable managed execution. Account: 111111111111.

Skill:
  STACKSET: baseline-iam-roles
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Permission model: SERVICE_MANAGED
    [✓] Organizations trusted access: Enabled
    [✓] Deployment targets: ou-abc-12345678
    [✓] Regions: us-east-1, us-west-2, eu-west-1
    [✓] Capabilities: CAPABILITY_IAM
    [✓] Managed execution: Active=true
    [✓] Operation preferences: FailureTolerancePercentage=5, MaxConcurrentPercentage=20
  VERIFICATION_COMMANDS:
    aws cloudformation describe-stack-set --stack-set-name baseline-iam-roles
    aws organizations list-aws-service-access-for-organization --service-principal cloudformation.amazonaws.com
```

## References

- Skill definition: `skills/cloudformation-stackset-deployer/SKILL.md`
- Permission models and roles: `skills/cloudformation-stackset-deployer/references/permission-models-and-roles.md`
- Operation preferences and drift: `skills/cloudformation-stackset-deployer/references/operation-preferences-and-drift.md`
- Eval suite: `skills/cloudformation-stackset-deployer/evals/evals.json`
