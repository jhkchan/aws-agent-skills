# End-to-End Example: ECS Fargate Deployment

A walkthrough showing how to use the `ecs-fargate-deployer` skill from
invocation through verification. Mirrors the structured-eval pattern of
shipping a concrete worked example per skill.

---

## Scenario

You are deploying a production ECS Fargate service that fronts a public
API via an ALB, pulls a container image from ECR, reads secrets from
Secrets Manager, writes to DynamoDB, and auto-scales on CPU. The
service requires:

- 0.5 vCPU / 1024 MB task size
- Container health check at GET /healthz
- ALB target group (target_type=ip)
- Deployment circuit breaker with rollback
- Separate execution role (ECR + Secrets + logs) and task role (DynamoDB + S3)
- Secret injection from Secrets Manager
- CloudWatch log group with 30-day retention
- Target-tracking auto-scaling (60% CPU, min 3 / max 12)
- Desired count 3 across 2 AZs

Service name: `payments-api-prod`
Cluster: `payments-prod`
Region: `us-east-1`
Account: `123456789012`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-ecs-fargate
```

Then paste the service requirements.

### Option B: Natural language

```
You: "Deploy a production ECS Fargate service payments-api-prod in
      cluster payments-prod. Image
      123456789012.dkr.ecr.us-east-1.amazonaws.com/payments-api:1.2.3.
      Port 8080 with health check GET /healthz. 0.5 vCPU / 1024 MB.
      Desired count 3 across subnet-aaa and subnet-bbb with
      sg-payments-api. ALB tg-payments-api (target_type=ip). Circuit
      breaker with rollback. Execution role payments-exec with ECR +
      Secrets Manager. Task role payments-task with DynamoDB + S3.
      Secret DB_PASSWORD from secretsmanager:payments/db. CloudWatch
      /ecs/payments-api with 30-day retention. Auto-scale 60% CPU
      min 3 max 12. Account: 123456789012."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "deploy ecs fargate service"
```

Output:

```
[Phase: Deploy | Skills routed: ecs-fargate-deployer]

Primary route: ecs-fargate-deployer (score: 18)
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
SERVICE: payments-api-prod
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓]      Cluster — payments-prod (Fargate capacity provider)
  [✓]      Task definition — payments-api:5 (0.5 vCPU / 1024 MB)
  [✓]      Container — 123456789012.dkr.ecr.us-east-1.amazonaws.com/payments-api:1.2.3
  [✓]      Container health check — GET /healthz (30s interval, 5s timeout, 3 retries)
  [✓]      Networking — awsvpc, subnets subnet-aaa/subnet-bbb, sg-payments-api
  [✓]      Load balancer — ALB tg-payments-api:8080 (target type ip)
  [✓]      Desired count — 3 (across 2 AZs)
  [✓]      Deployment circuit breaker — enabled with rollback
  [✓]      Minimum healthy percent — 100% / Maximum percent — 200%
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

---

## Step 3 — Deployment commands

The skill generates the CLI sequence (from
`references/deployment-cli-commands.md`):

```bash
# Step 1a: Execution role (image pull + log write + secret fetch)
aws iam create-role \
  --role-name payments-exec \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ecs-tasks.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

aws iam attach-role-policy \
  --role-name payments-exec \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

aws iam put-role-policy \
  --role-name payments-exec \
  --policy-name payments-secrets \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": ["secretsmanager:GetSecretValue"],
        "Resource": "arn:aws:secretsmanager:us-east-1:123456789012:secret:payments/db-*"
      },
      {
        "Effect": "Allow",
        "Action": ["kms:Decrypt"],
        "Resource": "arn:aws:kms:us-east-1:123456789012:key/payments-cmk-id"
      }
    ]
  }'

# Step 1b: Task role (application identity — DynamoDB + S3)
aws iam create-role \
  --role-name payments-task \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ecs-tasks.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

aws iam put-role-policy \
  --role-name payments-task \
  --policy-name payments-app-access \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:Query"],
        "Resource": "arn:aws:dynamodb:us-east-1:123456789012:table/payments-table"
      },
      {
        "Effect": "Allow",
        "Action": ["s3:PutObject"],
        "Resource": "arn:aws:s3:::payments-receipts/*"
      }
    ]
  }'

# Step 2: Pre-create the log group with retention
aws logs create-log-group --log-group-name /ecs/payments-api
aws logs put-retention-policy \
  --log-group-name /ecs/payments-api \
  --retention-in-days 30

# Step 3: Register the task definition
aws ecs register-task-definition \
  --family payments-api \
  --network-mode awsvpc \
  --requires-compatibilities FARGATE \
  --cpu 512 \
  --memory 1024 \
  --execution-role-arn arn:aws:iam::123456789012:role/payments-exec \
  --task-role-arn arn:aws:iam::123456789012:role/payments-task \
  --container-definitions '[
    {
      "name": "app",
      "image": "123456789012.dkr.ecr.us-east-1.amazonaws.com/payments-api:1.2.3",
      "essential": true,
      "portMappings": [{"containerPort": 8080, "protocol": "tcp"}],
      "environment": [
        {"name": "LOG_LEVEL", "value": "info"},
        {"name": "DB_HOST", "value": "payments-db.cluster.example.rds.amazonaws.com"}
      ],
      "secrets": [
        {"name": "DB_PASSWORD", "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789012:secret:payments/db-XXXXXX"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/payments-api",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8080/healthz || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 30
      }
    }
  ]'

# Step 4: Create the service
aws ecs create-service \
  --cluster payments-prod \
  --service-name payments-api-prod \
  --task-definition payments-api:1 \
  --desired-count 3 \
  --scheduling-strategy REPLICA \
  --deployment-controller type=ECS \
  --deployment-configuration "deploymentCircuitBreaker={enable=true,rollback=true},minimumHealthyPercent=100,maximumPercent=200,availabilityZoneRebalancing=ENABLED" \
  --capacity-provider-strategy capacityProvider=FARGATE,weight=1 \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-aaa,subnet-bbb],securityGroups=[sg-payments-api],assignPublicIp=DISABLED}" \
  --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/tg-payments-api/abc,containerName=app,containerPort=8080"

# Step 5: Auto-scaling
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --scalable-dimension ecs:service:DesiredCount \
  --resource-id service/payments-prod/payments-api-prod \
  --min-capacity 3 \
  --max-capacity 12

aws application-autoscaling put-scaling-policy \
  --service-namespace ecs \
  --scalable-dimension ecs:service:DesiredCount \
  --resource-id service/payments-prod/payments-api-prod \
  --policy-name payments-api-cpu-60 \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{
    "TargetValue": 60.0,
    "PredefinedMetricSpecification": {"PredefinedMetricType": "ECSServiceAverageCPUUtilization"},
    "ScaleOutCooldown": 60,
    "ScaleInCooldown": 300
  }'
```

---

## Step 4 — Post-deployment verification

```bash
# Service status + deployments + circuit breaker state
aws ecs describe-services --cluster payments-prod --services payments-api-prod

# Task definition (CPU, memory, roles, container defs)
aws ecs describe-task-definition --task-definition payments-api:1

# ALB target group health (must show healthy targets)
aws elbv2 describe-target-health \
  --target-group-arn arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/tg-payments-api/abc

# Log group retention (must show 30 days)
aws logs describe-log-groups --log-group-name-prefix /ecs/payments-api

# Auto-scaling policy
aws application-autoscaling describe-scaling-policies \
  --service-namespace ecs \
  --resource-id service/payments-prod/payments-api-prod
```

---

## What the skill catches that a naive deployment misses

| Configuration | Naive deployment | Skill output | Why the skill is right |
|---|---|---|---|
| ALB target_type | `instance` (default for some templates) | `ip` | Fargate tasks register by ENI private IP. `instance` silently fails registration. |
| Execution role vs task role | Conflated into one | Separate roles | The execution role pulls images + writes logs; the task role is the app's identity. Conflating produces least-privilege violations or pull failures. |
| Secrets Manager permission on execution role | Not added | Added | The execution role fetches the secret at container start. Without `secretsmanager:GetSecretValue`, the task fails immediately. |
| CloudWatch log group | Not pre-created | Pre-created with 30-day retention | ECS does NOT auto-create log groups. The first task fails with `ResourceNotFoundException`. |
| Deployment circuit breaker | Disabled (default) | Enabled with rollback | A bad task definition leaves the service degraded indefinitely without rollback. |
| Container health check | Omitted | Defined | Without it, the circuit breaker has no signal and never fires. |
| Auto-scaling cooldowns | scaleIn=60 (default-ish) | scaleIn=300 | Sub-300s scale-in causes flapping. |
| Capacity provider strategy | launch-type=FARGATE (legacy) | capacity-provider strategy | The launch-type API cannot use FARGATE_SPOT. Spot is a capacity provider. |

---

## Related artifacts

- **Skill definition:** `skills/ecs-fargate-deployer/SKILL.md`
- **Deployment CLI commands:** `skills/ecs-fargate-deployer/references/deployment-cli-commands.md`
- **Networking and scaling guide:** `skills/ecs-fargate-deployer/references/networking-and-scaling-guide.md`
- **Slash command:** `commands/aws/deploy-ecs-fargate.md`
- **Eval suite:** `skills/ecs-fargate-deployer/evals/evals.json`
- **Legacy test cases:** `skills/ecs-fargate-deployer/eval/test-cases.yaml`
