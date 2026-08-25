# CLI Commands and IaC — App Runner Service Deployer

Full copy-pasteable CLI command sequence for all 11 deployment steps.
Variables to substitute: `<region>`, `<account-id>`, `<service>`,
`<access-role>`, `<instance-role>`, `<image-uri>`, `<port>`,
`<subnets>`, `<security-groups>`, `<vc-name>`, `<log-group>`,
`<domain>`.

## Step 0: Prerequisites check

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region)

# Confirm ECR image exists (if ECR source)
aws ecr describe-images \
  --repository-name <repo> \
  --image-ids imageTag=<tag>

# Confirm access role trust policy (ECR source)
aws iam get-role --role-name <access-role> \
  --query 'Role.AssumeRolePolicyDocument'

# Confirm instance role trust policy
aws iam get-role --role-name <instance-role> \
  --query 'Role.AssumeRolePolicyDocument'

# Confirm VPC connector exists (if private resources)
aws apprunner describe-vpc-connector \
  --vpc-connector-arn arn:aws:apprunner:<region>:<account-id>:vpcconnector/<vc-name>/<id>

# Confirm service quota
aws service-quotas get-service-quota \
  --service-code apprunner \
  --quota-code L-DBB8PPEX
```

## Step 1: ECR access role (for ECR source)

```bash
# Access role — assumed by App Runner service to pull ECR image
aws iam create-role \
  --role-name <access-role> \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "tasks.apprunner.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach the managed policy purpose-built for App Runner ECR access
aws iam attach-role-policy \
  --role-name <access-role> \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess
```

For cross-account ECR, add an inline policy:

```bash
aws iam put-role-policy \
  --role-name <access-role> \
  --policy-name cross-account-ecr \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": [
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
      ],
      "Resource": "arn:aws:ecr:<region>:<other-acct>:repository/<repo>"
    }]
  }'
```

## Step 2: Instance role (application runtime identity)

```bash
aws iam create-role \
  --role-name <instance-role> \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "tasks.apprunner.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Application permissions (DynamoDB + S3 + Secrets Manager example)
aws iam put-role-policy \
  --role-name <instance-role> \
  --policy-name <service>-app-access \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:Query"],
        "Resource": "arn:aws:dynamodb:<region>:<account-id>:table/<table>"
      },
      {
        "Effect": "Allow",
        "Action": ["s3:GetObject", "s3:PutObject"],
        "Resource": "arn:aws:s3:::<bucket>/*"
      },
      {
        "Effect": "Allow",
        "Action": ["secretsmanager:GetSecretValue"],
        "Resource": "arn:aws:secretsmanager:<region>:<account-id>:secret:<service>/*"
      },
      {
        "Effect": "Allow",
        "Action": ["xray:PutTraceSegments", "xray:PutTelemetryRecords"],
        "Resource": "*"
      }
    ]
  }'
```

## Step 3: Pre-create CloudWatch log group with retention

```bash
aws logs create-log-group \
  --log-group-name /aws/apprunner/<service>

aws logs put-retention-policy \
  --log-group-name /aws/apprunner/<service> \
  --retention-in-days 30
```

## Step 4: VPC connector (for private resources)

```bash
aws apprunner create-vpc-connector \
  --vpc-connector-name <service>-vpc \
  --subnets subnet-aaa subnet-bbb subnet-ccc \
  --security-groups sg-priv-app \
  --tags Environment=production
```

Wait for the connector to become active:

```bash
aws apprunner describe-vpc-connector \
  --vpc-connector-arn arn:aws:apprunner:<region>:<account-id>:vpcconnector/<service>-vpc/<id> \
  --query 'VpcConnector.Status'
```

Status flow: `CREATING` -> `ACTIVE` (60-90 seconds).

## Step 5: Custom auto-scaling configuration (optional)

```bash
aws apprunner create-auto-scaling-configuration \
  --auto-scaling-configuration-name <service>-autoscale \
  --min-size 2 \
  --max-size 10 \
  --max-concurrency 100 \
  --tags Environment=production
```

Capture the returned ARN for the create-service call.

## Step 6: Observability configuration (optional)

```bash
aws apprunner create-observability-configuration \
  --observability-configuration-name <service>-obs \
  --trace-configuration Vendor=AWSXRAY \
  --tags Environment=production
```

## Step 7: Create the service (ECR source)

```bash
aws apprunner create-service \
  --service-name <service> \
  --source-configuration '{
    "ImageRepository": {
      "ImageIdentifier": "<image-uri>",
      "ImageRepositoryType": "ECR",
      "ImageConfiguration": {
        "Port": "<port>",
        "RuntimeEnvironmentVariables": [
          {"LOG_LEVEL": "info"},
          {"ENV": "production"}
        ],
        "RuntimeEnvironmentSecrets": [
          {"DB_PASSWORD": "arn:aws:secretsmanager:<region>:<account-id>:secret:<service>/db-XXXXXX"}
        ],
        "StartCommand": "node server.js"
      }
    },
    "AuthenticationConfiguration": {
      "AccessRoleArn": "arn:aws:iam::<account-id>:role/<access-role>"
    },
    "AutoDeploymentsEnabled": true,
    "ConfigurationSource": "API"
  }' \
  --instance-configuration '{
    "Cpu": "2048",
    "Memory": "4096",
    "InstanceRoleArn": "arn:aws:iam::<account-id>:role/<instance-role>"
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
      "VpcConnectorArn": "arn:aws:apprunner:<region>:<account-id>:vpcconnector/<service>-vpc/<id>"
    }
  }' \
  --auto-scaling-configuration-arn arn:aws:apprunner:<region>:<account-id>:autoscalingconfiguration/<service>-autoscale/<ver> \
  --observability-enabled \
  --observability-configuration-configuration-source AWS_XRAY \
  --tags Environment=production Application=<service>
```

## Step 7b: Create the service (source code repository)

```bash
aws apprunner create-service \
  --service-name <service> \
  --source-configuration '{
    "CodeRepository": {
      "RepositoryUrl": "https://github.com/org/<repo>",
      "SourceCodeVersion": {
        "Type": "BRANCH",
        "Value": "main"
      },
      "CodeConfiguration": {
        "ConfigurationSource": "API",
        "CodeConfigurationValues": {
          "Runtime": "nodejs20",
          "BuildCommand": "npm install",
          "StartCommand": "node server.js",
          "Port": "<port>",
          "RuntimeEnvironmentVariables": [
            {"LOG_LEVEL": "info"}
          ],
          "RuntimeEnvironmentSecrets": [
            {"DB_PASSWORD": "arn:aws:secretsmanager:<region>:<account-id>:secret:<service>/db-XXXXXX"}
          ]
        }
      },
      "SourceCodeVersion": {"Type": "BRANCH", "Value": "main"}
    },
    "AuthenticationConfiguration": {
      "ConnectionArn": "arn:aws:codeconnections:<region>:<account-id>:connection/<id>"
    },
    "AutoDeploymentsEnabled": true
  }' \
  --instance-configuration '{
    "Cpu": "1024",
    "Memory": "2048",
    "InstanceRoleArn": "arn:aws:iam::<account-id>:role/<instance-role>"
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
  --tags Environment=production Application=<service>
```

## Step 8: Manual deployment trigger (if AutoDeploymentsEnabled=false)

```bash
aws apprunner start-deployment --service-arn <service-arn>
```

Check operation status:

```bash
aws apprunner list-operations \
  --service-arn <service-arn> \
  --max-results 5
```

## Step 9: Custom domain association (optional)

```bash
aws apprunner associate-custom-domain \
  --service-arn <service-arn> \
  --domain-name <domain> \
  --enable-www-subdomain
```

For non-Route 53 domains, add the returned CNAME records to your DNS
provider to verify ownership.

## Step 10: Post-deployment verification

```bash
# Service status, source config, instance config, health check
aws apprunner describe-service --service-arn <service-arn>

# VPC connector subnets and status
aws apprunner describe-vpc-connector --vpc-connector-arn <vc-arn>

# Observability (X-Ray tracing state)
aws apprunner describe-observability-configuration \
  --observability-configuration-arn <obs-arn>

# Auto-scaling (min/max/concurrency)
aws apprunner describe-auto-scaling-configuration \
  --auto-scaling-configuration-arn <as-arn>

# Operations log (create, deploy, pause, resume)
aws apprunner list-operations --service-arn <service-arn>

# Log group and retention
aws logs describe-log-groups \
  --log-group-name-prefix /aws/apprunner/<service>

# Custom domain status
aws apprunner describe-custom-domains --service-arn <service-arn>

# IAM roles trust policies
aws iam get-role --role-name <access-role>
aws iam get-role --role-name <instance-role>
```

## Terraform equivalents

- `aws_apprunner_service` — service with `source_configuration`
  (`image_repository` or `code_repository`), `instance_configuration`
  (`cpu`, `memory`, `instance_role_arn`), `health_check_configuration`,
  `network_configuration` (`egress_configuration` with `vpc_connector_arn`).
- `aws_apprunner_vpc_connector` — `subnets`, `security_groups`.
- `aws_apprunner_auto_scaling_configuration_version` — `min_size`,
  `max_size`, `max_concurrency`. Reference via
  `auto_scaling_configuration_arn` on the service.
- `aws_apprunner_observability_configuration` — `trace_configuration`
  with `vendor = "AWSXRay"`.
- `aws_apprunner_custom_domain_association` — `domain_name`,
  `service_arn`, `enable_www_subdomain`.
- `aws_apprunner_vpc_ingress_connection` — for private endpoint mode.
- `aws_iam_role` (two) — access role (with
  `AWSAppRunnerServicePolicyForECRAccess` managed policy) and instance
  role (application permissions).

## CloudFormation equivalents

- `AWS::AppRunner::Service` — `SourceConfiguration`,
  `InstanceConfiguration`, `HealthCheckConfiguration`,
  `NetworkConfiguration`, `AutoScalingConfigurationArn`.
- `AWS::AppRunner::VpcConnector` — `Subnets`, `SecurityGroups`.
- `AWS::AppRunner::AutoScalingConfiguration` — `MinSize`, `MaxSize`,
  `MaxConcurrency`.
- `AWS::AppRunner::ObservabilityConfiguration` — `TraceConfiguration`.
- `AWS::AppRunner::VpcIngressConnection` — `IngressVpcConfiguration`.
- `AWS::IAM::Role` (two) — access role and instance role.

---

## Step 1: ECR access role (for ECR source — separate from instance role) (moved from SKILL.md)

**Two distinct roles. Never combine them.**

The ECR access role is assumed by the App Runner service to pull the
container image. The instance role is assumed by the application at
runtime. They are NEVER the same role.

```bash
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
```

`AWSAppRunnerServicePolicyForECRAccess` grants `ecr:GetDownloadUrlForLayer`,
`ecr:BatchGetImage`, `ecr:GetAuthorizationToken`. It is the managed policy
purpose-built for this role. Do NOT write a custom inline policy for ECR
pull — the managed policy is scoped and maintained by AWS.

---

## Step 2: Instance role (application runtime identity) (moved from SKILL.md)

The instance role is assumed by the application at runtime for AWS SDK
calls (DynamoDB, S3, Secrets Manager, etc.).

```bash
aws iam create-role \
  --role-name <service>-instance \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "tasks.apprunner.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

aws iam put-role-policy \
  --role-name <service>-instance \
  --policy-name <service>-app-access \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:Query"],
        "Resource": "arn:aws:dynamodb:<region>:<acct>:table/<table>"
      },
      {
        "Effect": "Allow",
        "Action": ["secretsmanager:GetSecretValue"],
        "Resource": "arn:aws:secretsmanager:<region>:<acct>:secret:<service>/*"
      }
    ]
  }'
```

| Workload | Instance role permissions |
|---|---|
| API backend (DynamoDB) | `dynamodb:GetItem`, `PutItem`, `Query` on table ARN |
| API backend (RDS via VPC connector) | No IAM — RDS auth is via secrets. Instance role fetches the secret. |
| S3 processor | `s3:GetObject`, `PutObject` on bucket ARN |
| SQS consumer | `sqs:ReceiveMessage`, `DeleteMessage` on queue ARN |

**NEVER use `AdministratorAccess` on either role.**

---

## Step 4: VPC connector (private resources) (moved from SKILL.md)

**This is the #1 App Runner networking pitfall.** If your app connects
to RDS, ElastiCache, internal ALBs, or any VPC-only resource, you MUST
attach a VPC connector. Without it, DNS resolves but the TCP connection
hangs silently until timeout.

```bash
aws apprunner create-vpc-connector \
  --vpc-connector-name <service>-vpc \
  --subnets subnet-aaa subnet-bbb subnet-ccc \
  --security-groups sg-priv-app
```

Rules:
- **Use PRIVATE subnets.** App Runner instances do not need public IPs.
- **Span >= 2 AZs** (3 for production HA).
- **Security group outbound** must allow the database port (e.g., 5432
  for Postgres, 3306 for MySQL, 6379 for Redis).
- **NAT Gateway NOT required** — the VPC connector uses AWS PrivateLink
  internally. The connector itself does not need internet access.
- **VPC connector is a separate resource** — create it before the service.

---

## Step 5: Health check policy (moved from SKILL.md)

App Runner probes the service on the configured path and port. A
mismatched path or port causes the service to stay in `CreateFailed`.

```json
{
  "Type": "APP",
  "Protocol": "HTTP",
  "Path": "/healthz",
  "IntervalInSeconds": 10,
  "TimeoutInSeconds": 5,
  "HealthyThreshold": 3,
  "UnhealthyThreshold": 5
}
```

- **Path MUST return HTTP 200** for the service to be considered healthy.
- **Interval 10s, healthy threshold 3** means a service is marked healthy
  after ~30s of successful probes.
- **Unhealthy threshold 5** means a service is marked unhealthy after
  ~50s of consecutive failures. NEVER set below 3 — transient blips
  cause spurious rollbacks.
- **If no health check is configured**, App Runner uses TCP probe on the
  service port. This catches the port being closed but NOT app-level
  unhealthiness (e.g., DB pool exhausted).

---

## Step 6: Auto-scaling configuration (moved from SKILL.md)

```bash
aws apprunner update-service \
  --service-arn <arn> \
  --auto-scaling-configuration-arn arn:aws:apprunner:<region>:<acct>:autoscalingconfiguration/DefaultConfiguration/1
```

Custom auto-scaling:

```bash
aws apprunner create-auto-scaling-configuration \
  --auto-scaling-configuration-name <service>-autoscale \
  --min-size 2 \
  --max-size 10 \
  --max-concurrency 100
```

| Parameter | Default | Production | Why |
|---|---|---|---|
| `min-size` | 1 | 2 (HA) | 1 = single point of failure during AZ outage |
| `max-size` | 25 | 10-20 | Cap cost; tune to traffic profile |
| `max-concurrency` | 100 | 50-200 | Requests per instance. Lower for CPU-heavy. |

- **Scale-to-zero**: `min-size=0` saves cost but adds cold-start latency
  (30-60s). ONLY for dev/staging or non-user-facing batch endpoints.
- **Provisioned concurrency** = `min-size >= 1`. This is the ONLY latency
  guarantee. At least one instance is always warm.
- **Scaling metric**: App Runner uses concurrent requests per instance
  (not CPU). An instance scales when `max-concurrency` is exceeded.

---

## Step 7: Secrets (Secrets Manager / SSM Parameter Store) (moved from SKILL.md)

Secrets are injected as environment variables at runtime via ARN
reference in `ConfigurationSources`. NOT visible in plaintext.

```json
{
  "RuntimeEnvironmentSecrets": [
    {"DB_PASSWORD": "arn:aws:secretsmanager:us-east-1:123456789012:secret:checkout/db-XXXXXX"},
    {"STRIPE_KEY": "arn:aws:ssm:us-east-1:123456789012:parameter/checkout/stripe-key"}
  ]
}
```

Instance role needs `secretsmanager:GetSecretValue` or
`ssm:GetParameters` plus `kms:Decrypt` if a customer-managed KMS key is
used.

---

## Step 8: Observability (CloudWatch Logs, X-Ray, Application Signals) (moved from SKILL.md)

**CloudWatch Logs:** App Runner streams to
`/aws/apprunner/<service-name>/<service-id>`. The log group name is NOT
configurable — it is derived from the service name. Pre-create a log
group with the right retention BEFORE creating the service, or App Runner
creates one with `Never Expire`.

```bash
aws logs create-log-group --log-group-name /aws/apprunner/<service-name>
aws logs put-retention-policy \
  --log-group-name /aws/apprunner/<service-name> \
  --retention-in-days 30
```

**X-Ray tracing:** set `TracingConfiguration Vendor=AWSXRay`. The instance
role needs `xray:PutTraceSegments` and `xray:PutTelemetryRecords`.

**Application Signals:** auto-instrumented for Java, Python, Node.js when
tracing is enabled. No code changes required.

---

## Step 9: Custom domain (optional) (moved from SKILL.md)

```bash
aws apprunner associate-custom-domain \
  --service-arn <arn> \
  --domain-name checkout.example.com \
  --enable-www-subdomain
```

App Runner provisions and manages the TLS certificate via AWS Certificate
Manager. For non-Route 53 domains, you must add CNAME records manually
to verify ownership.

---

## Step 10: Create the service (moved from SKILL.md)

```bash
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
  --observability-enabled \
  --observability-configuration-configuration-source AWS_XRAY \
  --tags Environment=production Application=checkout-api
```
