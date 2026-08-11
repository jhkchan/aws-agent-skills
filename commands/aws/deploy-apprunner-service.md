---
description: Deploy an AWS App Runner service with production-grade configuration (source selection: ECR image vs source code repository, instance sizing with CPU/memory, port and environment variables, secrets via Secrets Manager / SSM, VPC connector for private resources, auto-scaling with min/max and concurrency, custom domain with managed TLS, observability with CloudWatch Logs and X-Ray tracing, deployment trigger automatic vs manual, health check policy). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create app runner service"
  - "deploy app runner"
  - "app runner deployment"
  - "apprunner ecr source"
  - "apprunner source code repository"
  - "apprunner vpc connector"
  - "app runner auto scaling"
  - "app runner custom domain"
  - "app runner health check"
  - "app runner observability"
  - "app runner xray tracing"
  - "app runner manual deployment"
  - "apprunner instance role"
  - "apprunner access role"
  - "apprunner secrets"
  - "app runner arm64 graviton"
  - "app runner vpc ingress"
routes_to: apprunner-service-deployer
---

# /aws:deploy-apprunner-service

Activate the `apprunner-service-deployer` skill and deploy an Amazon
App Runner service with production-grade configuration.

## What it does

The skill walks an 11-step deployment procedure and emits a
READY_TO_DEPLOY checklist:

1. ECR access role (for ECR source — separate from instance role)
2. Instance role (application runtime identity)
3. Instance configuration (CPU/memory combos, App Runner sizing)
4. VPC connector (private resources: RDS, ElastiCache, internal ALBs)
5. Health check policy (APP probe with path, interval, thresholds)
6. Auto-scaling configuration (min/max instances, concurrency)
7. Secrets (Secrets Manager / SSM Parameter Store references)
8. Observability (CloudWatch Logs, X-Ray tracing, Application Signals)
9. Custom domain (managed TLS via ACM, optional www subdomain)
10. Create the service (source config, instance config, network config)
11. Verification commands

## When to use

- You need to create a new App Runner service with production
  defaults.
- You are deploying a containerized web app or API to App Runner and
  want to validate configuration against best practices.
- You need deployment CLI commands or Terraform / CloudFormation
  templates.
- You want to check for deployment blockers (missing VPC connector,
  missing access role, missing instance role, invalid CPU/memory combo).

## How to invoke

### Slash command

```
/aws:deploy-apprunner-service
```

Then provide: service name, source type (ECR image or code repository),
container image (with tag) or repo URL + connection ARN, instance size
(vCPU / memory), port, health check path, access role (if ECR),
instance role, VPC connector (if private resources), auto-scaling
parameters, secrets ARNs, and any optional features (custom domain,
X-Ray tracing, manual deployment trigger).

### Natural language

Any of these routes to the same skill:

- "deploy an App Runner service"
- "create an App Runner service from ECR"
- "configure App Runner VPC connector"
- "set up App Runner auto-scaling"
- "enable App Runner X-Ray tracing"

### CLI routing

```bash
node cli/bin/cli.js route "deploy app runner service"
```

## What the checklist contains

The output is a single block with literal labels:

```
SERVICE: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓]      Source — ECR image <uri> | source code repo <url>
  [✓]      Source type — ECR | CODE, access role <arn>
  [✓]      Instance configuration — <cpu> vCPU / <memory> MB, port <port>
  [✓]      Environment variables — <vars>
  [✓]      Secrets — <secret-names>
  [✓]      Instance role — <role>
  [✓]      Auto-scaling — min <x> / max <y>, concurrency <n>
  [✓]      VPC connector — <arn>
  [✓]      Health check — GET <path>
  [✓]      Deployment trigger — automatic | manual
  [✓]      Observability — CloudWatch + X-Ray
  [OPTIONAL] Custom domain — <domain>
VERIFICATION_COMMANDS:
  aws apprunner describe-service ...
  aws apprunner describe-vpc-connector ...
```

The output checklist feeds into verification pipelines and audit
skills (e.g., a CloudWatch alarm auditor for post-deployment checks).

## Example

```
You: /aws:deploy-apprunner-service

     Deploy a production App Runner service checkout-api-prod in
     us-east-1. ECR image
     123456789012.dkr.ecr.us-east-1.amazonaws.com/checkout-api:2.1.0.
     Port 8080 with health check GET /healthz. 2 vCPU / 4096 MB.
     Access role AppRunnerECRAccess. Instance role checkout-instance
     with DynamoDB + S3. Secret DB_PASSWORD from
     secretsmanager:checkout/db. VPC connector checkout-vpc with
     subnets subnet-priv-a, subnet-priv-b, subnet-priv-c and
     sg-priv-app. Auto-scaling min 2 / max 10, concurrency 100.
     CloudWatch /aws/apprunner/checkout-api-prod with 30-day
     retention, X-Ray tracing enabled. Custom domain
     checkout.example.com. Account: 123456789012.

Skill:
  SERVICE: checkout-api-prod
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓]      Source — ECR image 123456789012.dkr.ecr.us-east-1.amazonaws.com/checkout-api:2.1.0
    [✓]      Source type — ECR (image), access role AppRunnerECRAccess
    [✓]      Instance configuration — 2 vCPU / 4096 MB, port 8080
    [✓]      Secrets — DB_PASSWORD from secretsmanager:checkout/db
    [✓]      Instance role — checkout-instance (DynamoDB + S3 scoped)
    [✓]      Auto-scaling — min 2 / max 10, concurrency 100
    [✓]      VPC connector — checkout-vpc (3 subnets, 1 SG)
    [✓]      Health check — GET /healthz (HTTP 200), healthy threshold 3, interval 10s
    [✓]      Observability — CloudWatch Logs /aws/apprunner/checkout-api-prod, retention 30 days, X-Ray tracing enabled
    [OPTIONAL] Custom domain — checkout.example.com (managed TLS)
  VERIFICATION_COMMANDS:
    aws apprunner describe-service --service-arn arn:aws:apprunner:us-east-1:123456789012:service/checkout-api-prod/abc
    aws apprunner describe-vpc-connector --vpc-connector-arn arn:aws:apprunner:us-east-1:123456789012:vpcconnector/checkout-vpc/abc
    aws logs describe-log-groups --log-group-name-prefix /aws/apprunner/checkout-api-prod
```

## References

- Skill definition: `skills/apprunner-service-deployer/SKILL.md`
- Deployment CLI commands: `skills/apprunner-service-deployer/references/cli-commands-and-iac.md`
- Source and config guide: `skills/apprunner-service-deployer/references/source-and-config-guide.md`
- Eval suite: `skills/apprunner-service-deployer/evals/evals.json`
