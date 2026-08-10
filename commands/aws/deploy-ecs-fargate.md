---
description: Deploy an ECS Fargate service with production-grade configuration (task definition with right-sized CPU/memory, container health check, awsvpc networking, ALB target_type=ip, deployment circuit breaker with rollback, separate execution role and task role, secrets via Secrets Manager / SSM, FireLens / CloudWatch logging, and target-tracking auto-scaling). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create ecs fargate service"
  - "deploy ecs fargate"
  - "ecs fargate deployment"
  - "ecs task definition"
  - "ecs service definition"
  - "fargate cpu memory"
  - "ecs awsvpc networking"
  - "fargate security group"
  - "alb target group ecs"
  - "ecs listener rule"
  - "ecs auto scaling"
  - "fargate spot"
  - "ecs circuit breaker"
  - "ecs task execution role"
  - "ecs task role"
  - "ecs firelens"
  - "ecs container health check"
  - "ecs secrets"
routes_to: ecs-fargate-deployer
---

# /aws:deploy-ecs-fargate

Activate the `ecs-fargate-deployer` skill and deploy an ECS Fargate
service with production-grade configuration.

## What it does

The skill walks a 10-step deployment procedure and emits a
READY_TO_DEPLOY checklist:

1. Task execution role + task role (separate, least-privilege)
2. Task definition (CPU/memory combos, Fargate sizing)
3. Container definitions (image, ports, env vars, secrets, health check)
4. Service definition (desired count, circuit breaker, min/max percent)
5. Networking (awsvpc, private subnets, security groups)
6. Load balancer integration (ALB target_type=ip, listener rules)
7. Secrets (Secrets Manager / SSM Parameter Store references)
8. Logging (awslogs driver or FireLens log routing)
9. Auto-scaling (target tracking on CPU/memory/ALB request count)
10. Verification commands

## When to use

- You need to create a new ECS Fargate service with production
  defaults.
- You are deploying a container workload to Fargate and want to
  validate configuration against best practices.
- You need deployment CLI commands or Terraform / CloudFormation
  templates.
- You want to check for deployment blockers (wrong target_type,
  missing NAT Gateway, missing execution role).

## How to invoke

### Slash command

```
/aws:deploy-ecs-fargate
```

Then provide: cluster name, service name, container image (with tag),
task size (vCPU / memory), desired count, subnets, security group,
ALB target group ARN, execution role, task role, and any optional
features (Spot blend, auto-scaling, FireLens logging).

### Natural language

Any of these routes to the same skill:

- "deploy an ECS Fargate service"
- "create a Fargate task definition"
- "configure ECS Fargate Spot capacity provider"
- "set up ECS with ALB target type ip"
- "enable ECS deployment circuit breaker with rollback"

### CLI routing

```bash
node cli/bin/cli.js route "deploy ecs fargate service"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The output checklist feeds into verification pipelines and audit
skills (e.g., an ECS service auditor for post-deployment checks).

## Example

```
You: /aws:deploy-ecs-fargate

     Deploy a production ECS Fargate service payments-api-prod in
     cluster payments-prod. Image
     123456789012.dkr.ecr.us-east-1.amazonaws.com/payments-api:1.2.3.
     Port 8080 with health check GET /healthz. 0.5 vCPU / 1024 MB.
     Desired count 3 across subnet-aaa and subnet-bbb with
     sg-payments-api. ALB tg-payments-api (target_type=ip). Circuit
     breaker with rollback. Execution role payments-exec with ECR +
     Secrets Manager. Task role payments-task with DynamoDB + S3.
     Secret DB_PASSWORD from secretsmanager:payments/db. CloudWatch
     /ecs/payments-api with 30-day retention. Auto-scale 60% CPU
     min 3 max 12. Account: 123456789012.

Skill:
  SERVICE: payments-api-prod
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓]      Cluster — payments-prod (Fargate capacity provider)
    [✓]      Task definition — payments-api:5 (0.5 vCPU / 1024 MB)
    [✓]      Container — 123456789012.dkr.ecr.us-east-1.amazonaws.com/payments-api:1.2.3
    [✓]      Container health check — GET /healthz (30s interval, 5s timeout, 3 retries)
    [✓]      Networking — awsvpc, subnets subnet-aaa/subnet-bbb, sg-payments-api
    [✓]      Load balancer — ALB tg-payments-api:8080 (target type ip)
    [✓]      Deployment circuit breaker — enabled with rollback
    [✓]      Execution role — payments-exec (ECR + Secrets Manager + logs)
    [✓]      Task role — payments-task (DynamoDB + S3 scoped)
    [✓]      Secrets — DB_PASSWORD from secretsmanager:payments/db
    [✓]      Logging — awslogs → CloudWatch /ecs/payments-api, retention 30 days
    [✓]      Auto-scaling — target tracking 60% CPU, min 3 / max 12
  VERIFICATION_COMMANDS:
    aws ecs describe-services --cluster payments-prod --services payments-api-prod
    aws ecs describe-task-definition --task-definition payments-api:5
    aws elbv2 describe-target-groups --names tg-payments-api
    aws logs describe-log-groups --log-group-name-prefix /ecs/payments-api
    aws application-autoscaling describe-scaling-policies --service-namespace ecs --resource-id service/payments-prod/payments-api-prod
```

## References

- Skill definition: `skills/ecs-fargate-deployer/SKILL.md`
- Deployment CLI commands: `skills/ecs-fargate-deployer/references/deployment-cli-commands.md`
- Networking and scaling guide: `skills/ecs-fargate-deployer/references/networking-and-scaling-guide.md`
- Eval suite: `skills/ecs-fargate-deployer/evals/evals.json`
