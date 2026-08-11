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
