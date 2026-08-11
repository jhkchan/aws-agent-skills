# End-to-End Example: App Runner Service Deployment

A walkthrough showing how to use the `apprunner-service-deployer` skill
from invocation through verification. Mirrors the structured-eval pattern
of shipping a concrete worked example per skill.

---

## Scenario

You are deploying a production App Runner service that fronts a public
checkout API, pulls a container image from ECR, reads secrets from
Secrets Manager, writes to DynamoDB via a VPC connector, and auto-scales
on concurrency. The service requires:

- 2 vCPU / 4096 MB instance size
- Health check at GET /healthz
- VPC connector for Aurora PostgreSQL access in private subnets
- Separate ECR access role and instance role
- Secret injection from Secrets Manager
- CloudWatch log group with 30-day retention
- X-Ray tracing enabled
- Auto-scaling (min 2 / max 10, concurrency 100)
- Custom domain checkout.example.com

Service name: `checkout-api-prod`
Region: `us-east-1`
Account: `123456789012`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-apprunner-service
```

Then paste the service requirements.

### Option B: Natural language

```
You: "Deploy a production App Runner service checkout-api-prod in
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
      checkout.example.com. Account: 123456789012."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "deploy app runner service"
```

Output:

```
[Phase: Deploy | Skills routed: apprunner-service-deployer]

Primary route: apprunner-service-deployer (score: 18)
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
SERVICE: checkout-api-prod
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓]      Source — ECR image 123456789012.dkr.ecr.us-east-1.amazonaws.com/checkout-api:2.1.0
  [✓]      Source type — ECR (image), access role AppRunnerECRAccess
  [✓]      Instance configuration — 2 vCPU / 4096 MB, port 8080
  [✓]      Environment variables — LOG_LEVEL=info, ENV=production
  [✓]      Secrets — DB_PASSWORD from secretsmanager:checkout/db
  [✓]      Instance role — checkout-instance (DynamoDB + S3 scoped)
  [✓]      Auto-scaling — min 2 / max 10, concurrency 100
  [✓]      VPC connector — checkout-vpc (3 subnets, 1 SG)
  [✓]      Health check — GET /healthz (HTTP 200), healthy threshold 3, interval 10s
  [✓]      Deployment trigger — automatic
  [✓]      Observability — CloudWatch Logs /aws/apprunner/checkout-api-prod, retention 30 days, X-Ray tracing enabled
  [OPTIONAL] Custom domain — checkout.example.com (managed TLS)
VERIFICATION_COMMANDS:
  aws apprunner describe-service --service-arn arn:aws:apprunner:us-east-1:123456789012:service/checkout-api-prod/abc
  aws apprunner describe-vpc-connector --vpc-connector-arn arn:aws:apprunner:us-east-1:123456789012:vpcconnector/checkout-vpc/abc
  aws iam get-role --role-name AppRunnerECRAccess
  aws logs describe-log-groups --log-group-name-prefix /aws/apprunner/checkout-api-prod
```

---

## Step 3 — Deployment commands

The skill generates the CLI sequence (from
`references/cli-commands-and-iac.md`):

```bash
# Step 1a: ECR access role (image pull)
aws iam create-role \
  --role-name AppRunnerECRAccess \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "tasks.apprunner.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

aws iam attach-role-policy \
  --role-name AppRunnerECRAccess \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess

# Step 1b: Instance role (application identity — DynamoDB + S3)
aws iam create-role \
  --role-name checkout-instance \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "tasks.apprunner.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

aws iam put-role-policy \
  --role-name checkout-instance \
  --policy-name checkout-app-access \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:Query"],
        "Resource": "arn:aws:dynamodb:us-east-1:123456789012:table/checkout-table"
      },
      {
        "Effect": "Allow",
        "Action": ["s3:PutObject"],
        "Resource": "arn:aws:s3:::checkout-receipts/*"
      },
      {
        "Effect": "Allow",
        "Action": ["xray:PutTraceSegments", "xray:PutTelemetryRecords"],
        "Resource": "*"
      }
    ]
  }'

# Step 2: Pre-create the log group with retention
aws logs create-log-group --log-group-name /aws/apprunner/checkout-api-prod
aws logs put-retention-policy \
  --log-group-name /aws/apprunner/checkout-api-prod \
  --retention-in-days 30

# Step 3: Create VPC connector
aws apprunner create-vpc-connector \
  --vpc-connector-name checkout-vpc \
  --subnets subnet-priv-a subnet-priv-b subnet-priv-c \
  --security-groups sg-priv-app

# Step 4: Create custom auto-scaling config
aws apprunner create-auto-scaling-configuration \
  --auto-scaling-configuration-name checkout-autoscale \
  --min-size 2 \
  --max-size 10 \
  --max-concurrency 100

# Step 5: Create the service
aws apprunner create-service \
  --service-name checkout-api-prod \
  --source-configuration '{
    "ImageRepository": {
      "ImageIdentifier": "123456789012.dkr.ecr.us-east-1.amazonaws.com/checkout-api:2.1.0",
      "ImageRepositoryType": "ECR",
      "ImageConfiguration": {
        "Port": "8080",
        "RuntimeEnvironmentVariables": [
          {"LOG_LEVEL": "info"},
          {"ENV": "production"}
        ],
        "RuntimeEnvironmentSecrets": [
          {"DB_PASSWORD": "arn:aws:secretsmanager:us-east-1:123456789012:secret:checkout/db-XXXXXX"}
        ],
        "StartCommand": "node server.js"
      }
    },
    "AuthenticationConfiguration": {
      "AccessRoleArn": "arn:aws:iam::123456789012:role/AppRunnerECRAccess"
    },
    "AutoDeploymentsEnabled": true
  }' \
  --instance-configuration '{
    "Cpu": "2048",
    "Memory": "4096",
    "InstanceRoleArn": "arn:aws:iam::123456789012:role/checkout-instance"
  }' \
  --health-check-configuration '{
    "Type": "APP",
    "Protocol": "HTTP",
    "Path": "/healthz",
    "IntervalInSeconds": 10,
    "TimeoutInSeconds": 5,
    "HealthyThreshold": 3,
    "UnhealthyThreshold": 5
  }' \
  --network-configuration '{
    "EgressConfiguration": {
      "EgressType": "VPC",
      "VpcConnectorArn": "arn:aws:apprunner:us-east-1:123456789012:vpcconnector/checkout-vpc/abc"
    }
  }' \
  --auto-scaling-configuration-arn arn:aws:apprunner:us-east-1:123456789012:autoscalingconfiguration/checkout-autoscale/1 \
  --observability-enabled \
  --observability-configuration-configuration-source AWS_XRAY \
  --tags Environment=production Application=checkout-api

# Step 6: Associate custom domain
aws apprunner associate-custom-domain \
  --service-arn arn:aws:apprunner:us-east-1:123456789012:service/checkout-api-prod/abc \
  --domain-name checkout.example.com \
  --enable-www-subdomain
```

---

## Step 4 — Post-deployment verification

```bash
# Service status, source config, instance config, health check
aws apprunner describe-service \
  --service-arn arn:aws:apprunner:us-east-1:123456789012:service/checkout-api-prod/abc

# VPC connector subnets and status
aws apprunner describe-vpc-connector \
  --vpc-connector-arn arn:aws:apprunner:us-east-1:123456789012:vpcconnector/checkout-vpc/abc

# Operations log (create, deploy)
aws apprunner list-operations \
  --service-arn arn:aws:apprunner:us-east-1:123456789012:service/checkout-api-prod/abc

# Log group retention (must show 30 days)
aws logs describe-log-groups \
  --log-group-name-prefix /aws/apprunner/checkout-api-prod

# Custom domain status
aws apprunner describe-custom-domains \
  --service-arn arn:aws:apprunner:us-east-1:123456789012:service/checkout-api-prod/abc
```

---

## What the skill catches that a naive deployment misses

| Configuration | Naive deployment | Skill output | Why the skill is right |
|---|---|---|---|
| ECR access role | Not created | Created with managed policy | App Runner cannot pull the ECR image without the access role. The create-service call fails. |
| VPC connector | Not configured | Created with private subnets | DNS resolves but TCP connections to RDS hang silently until timeout. #1 silent-failure pitfall. |
| Log group retention | Not pre-created (defaults to Never Expire) | Pre-created with 30-day retention | App Runner creates the log group with Never Expire if it does not exist. |
| X-Ray tracing | Not enabled | Enabled via observability config | Tracing must be explicitly enabled. The instance role also needs xray permissions. |
| Health check policy | Omitted | Defined with APP probe | Without it, App Runner uses TCP probe which misses app-level unhealthiness. |
| Auto-scaling concurrency | Default (100, but min=1) | Custom (min 2, max 10, concurrency 100) | Default min-size=1 is a single point of failure for HA. |
| Deployment trigger | Default (automatic) | Explicit (automatic for dev, manual for prod) | Auto-deploy in production without change-management is risky. |

---

## Related artifacts

- **Skill definition:** `skills/apprunner-service-deployer/SKILL.md`
- **Deployment CLI commands:** `skills/apprunner-service-deployer/references/cli-commands-and-iac.md`
- **Source and config guide:** `skills/apprunner-service-deployer/references/source-and-config-guide.md`
- **Slash command:** `commands/aws/deploy-apprunner-service.md`
- **Eval suite:** `skills/apprunner-service-deployer/evals/evals.json`
- **Legacy test cases:** `skills/apprunner-service-deployer/eval/test-cases.yaml`
