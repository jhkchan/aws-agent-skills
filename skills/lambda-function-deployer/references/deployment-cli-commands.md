# Deployment CLI Commands — Lambda Function Deployer

Full copy-pasteable CLI command sequence for all 13 deployment steps.
Variables to substitute: `<name>`, `<region>`, `<account-id>`,
`<execution-role>`, `<runtime>`, `<handler>`, `<kms-key-arn>`,
`<subnet-ids>`, `<security-group>`, `<dlq-arn>`.

## Step 0: Prerequisites check

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region)

# Confirm function name is available
aws lambda get-function-configuration --function-name <name> 2>&1 || echo "Name is available"

# Confirm execution role exists
aws iam get-role --role-name <execution-role>
```

## Step 1: Execution IAM role (least-privilege)

```bash
# Create the trust policy + role
aws iam create-role \
  --role-name <name>-exec \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach CloudWatch Logs + service-specific permissions
# Option A: managed policy (quick, broader than needed)
aws iam attach-role-policy \
  --role-name <name>-exec \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Option B: custom inline policy (scoped to function log group)
aws iam put-role-policy \
  --role-name <name>-exec \
  --policy-name <name>-logs \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
        "Resource": "arn:aws:logs:<region>:<account-id>:log-group:/aws/lambda/<name>:*"
      }
    ]
  }'

# Add service-specific permissions (example: DynamoDB + SQS)
aws iam put-role-policy \
  --role-name <name>-exec \
  --policy-name <name>-service-access \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Query"],
        "Resource": "arn:aws:dynamodb:<region>:<account-id>:table/<table-name>"
      },
      {
        "Effect": "Allow",
        "Action": ["sqs:SendMessage"],
        "Resource": "arn:aws:sqs:<region>:<account-id>:<queue-name>"
      }
    ]
  }'

# Add X-Ray tracing permission
aws iam attach-role-policy \
  --role-name <name>-exec \
  --policy-arn arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess

# Add KMS decrypt for env var encryption
aws iam put-role-policy \
  --role-name <name>-exec \
  --policy-name <name>-kms \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": ["kms:Decrypt"],
      "Resource": "arn:aws:kms:<region>:<account-id>:key/<key-id>"
    }]
  }'
```

## Step 2: Pre-create CloudWatch log group with retention

```bash
aws logs create-log-group --log-group-name /aws/lambda/<name>
aws logs put-retention-policy \
  --log-group-name /aws/lambda/<name> \
  --retention-in-days 30
```

## Step 3: Package the function

### Zip package (<= 50 MB)

```bash
# Node.js
zip -r function.zip index.js node_modules/

# Python
zip -r function.zip lambda_function.py
# Or with dependencies:
pip install --target ./package -r requirements.txt
cd package && zip -r ../function.zip . && cd ..
zip -g function.zip lambda_function.py
```

### ECR container image (> 50 MB)

```dockerfile
# Dockerfile
FROM public.ecr.aws/lambda/nodejs:20
COPY app.js package*.json ./
RUN npm ci --production
CMD [ "app.handler" ]
```

```bash
# Create ECR repository
aws ecr create-repository --repository-name <name>

# Build, tag, push
docker build -t <name> .
docker tag <name>:latest <account-id>.dkr.ecr.<region>.amazonaws.com/<name>:latest
aws ecr get-login-password | docker login --username AWS --password-stdin <account-id>.dkr.ecr.<region>.amazonaws.com
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/<name>:latest
```

## Step 4: Create the function

### Zip deployment

```bash
aws lambda create-function \
  --function-name <name> \
  --runtime nodejs20.x \
  --handler index.handler \
  --role arn:aws:iam::<account-id>:role/<name>-exec \
  --zip-file fileb://function.zip \
  --memory-size 512 \
  --timeout 15 \
  --environment "Variables={DB_HOST=prod-db.example.com,DB_PORT=5432}" \
  --kms-key-arn "arn:aws:kms:<region>:<account-id>:key/<key-id>" \
  --tracing-config Mode=Active \
  --architectures x86_64
```

### ECR deployment

```bash
aws lambda create-function \
  --function-name <name> \
  --package-type Image \
  --code ImageUri=<account-id>.dkr.ecr.<region>.amazonaws.com/<name>:latest \
  --role arn:aws:iam::<account-id>:role/<name>-exec \
  --memory-size 1024 \
  --timeout 30 \
  --tracing-config Mode=Active
```

## Step 5: VPC configuration (if needed)

```bash
aws lambda update-function-configuration \
  --function-name <name> \
  --vpc-config SubnetIds=subnet-aaa,subnet-bbb,SecurityGroupIds=sg-xxx
```

**VPC prerequisites (NAT Gateway setup if internet access is needed):**

```bash
# Allocate Elastic IP for NAT Gateway
aws ec2 allocate-address --domain vpc

# Create NAT Gateway in a PUBLIC subnet
aws ec2 create-nat-gateway \
  --subnet-id subnet-public \
  --allocation-id eipalloc-xxx

# Update private subnet route table to route 0.0.0.0/0 through NAT
aws ec2 create-route \
  --route-table-id rtb-private \
  --destination-cidr-block 0.0.0.0/0 \
  --nat-gateway-id nat-xxx
```

## Step 6: Dead-letter queue / destination

### On-failure destination (recommended)

```bash
aws lambda put-function-event-invoke-config \
  --function-name <name> \
  --maximum-retry-attempts 2 \
  --maximum-event-age-in-seconds 21600 \
  --destination-config '{
    "OnFailure": {
      "Destination": "arn:aws:sqs:<region>:<account-id>:<name>-dlq"
    }
  }'
```

### DLQ (legacy, if destination not desired)

```bash
aws lambda update-function-configuration \
  --function-name <name> \
  --dead-letter-config TargetArn=arn:aws:sqs:<region>:<account-id>:<name>-dlq
```

## Step 7: Concurrency

### Reserved concurrency (cap + guarantee)

```bash
aws lambda put-function-concurrency \
  --function-name <name> \
  --reserved-concurrent-executions 50
```

### Provisioned concurrency (eliminate cold starts)

```bash
# Requires a published version or alias
aws lambda publish-version --function-name <name>
aws lambda create-alias \
  --function-name <name> \
  --name prod \
  --function-version 1

aws lambda put-provisioned-concurrency-config \
  --function-name <name> \
  --qualifier prod \
  --provisioned-concurrent-executions 10
```

## Step 8: Layers

```bash
aws lambda update-function-configuration \
  --function-name <name> \
  --layers \
    "arn:aws:lambda:<region>:464622532012:layer:AWS-Parameters-and-Secrets-Lambda-Extension:11" \
    "arn:aws:lambda:<region>:017000801446:layer:AWSLambdaPowertoolsPythonV3-python312-x86_64:1"
```

## Step 9: Code signing (regulated environments)

```bash
# Create signing profile
aws signer put-signing-profile \
  --profile-name <name>-signing \
  --platform AWSLambda-SHA384-ECDSA

# Create code signing config
aws lambda create-code-signing-config \
  --code-signing-config-name <name>-csc \
  --allowed-publishers SigningProfileVersionArns=$(aws signer get-signing-profile --profile-name <name>-signing --query 'SigningProfileArn' --output text) \
  --code-signing-policies UntrustedArtifactOnDeployment=Enforce

# Attach to function
aws lambda update-function-code-signing-config \
  --function-name <name> \
  --code-signing-config-arn $(aws lambda list-code-signing-configs --query 'CodeSigningConfigs[?Description==`<name>-csc`].CodeSigningConfigArn' --output text)
```

## Step 10: SnapStart (Java/Python cold-start optimization)

```bash
aws lambda update-function-configuration \
  --function-name <name> \
  --snap-start ApplyOn=PublishedVersions

# Must publish a version for SnapStart to take effect
aws lambda publish-version --function-name <name>
```

## Step 11: Tags

```bash
aws lambda tag-resource \
  --resource arn:aws:lambda:<region>:<account-id>:function:<name> \
  --tags Environment=production,Workload=api-backend,Owner=platform-team,CostCenter=12345
```

## Step 12: Verification

```bash
# Full function configuration
aws lambda get-function-configuration --function-name <name>

# Execution role policies
aws iam list-attached-role-policies --role-name <name>-exec
aws iam list-inline-role-policies --role-name <name>-exec

# Event invoke config (destinations, retries)
aws lambda get-function-event-invoke-config --function-name <name>

# Concurrency
aws lambda get-function-concurrency --function-name <name>
aws lambda list-provisioned-concurrency-configs --function-name <name>

# VPC config
aws lambda get-function-configuration --function-name <name> --query 'VpcConfig'

# Layers
aws lambda get-function-configuration --function-name <name> --query 'Layers'

# Code signing config
aws lambda get-function-code-signing-config --function-name <name>

# Log group retention
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/<name>

# SnapStart status
aws lambda get-function-configuration --function-name <name> --query 'SnapStart'

# Tracing config
aws lambda get-function-configuration --function-name <name> --query 'TracingConfig'

# Tags
aws lambda list-tags --resource arn:aws:lambda:<region>:<account-id>:function:<name>

# Test invocation
aws lambda invoke \
  --function-name <name> \
  --cli-binary-format raw-in-base64-out \
  --payload '{"test": true}' \
  /tmp/response.json
cat /tmp/response.json
```

## Terraform equivalent (aws_lambda_function + associated resources)

```hcl
# CloudWatch log group with retention
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.function_name}"
  retention_in_days = 30
}

# Execution IAM role
resource "aws_iam_role" "lambda_exec" {
  name = "${var.function_name}-exec"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

# CloudWatch Logs permissions (scoped to this function's log group)
resource "aws_iam_role_policy" "lambda_logs" {
  name = "${var.function_name}-logs"
  role = aws_iam_role.lambda_exec.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["logs:CreateLogStream", "logs:PutLogEvents"]
      Resource = "${aws_cloudwatch_log_group.lambda.arn}:*"
    }]
  })
}

# X-Ray tracing
resource "aws_iam_role_policy_attachment" "xray" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

# KMS decrypt for env vars
resource "aws_iam_role_policy" "lambda_kms" {
  name = "${var.function_name}-kms"
  role = aws_iam_role.lambda_exec.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["kms:Decrypt"]
      Resource = aws_kms_key.lambda_env.arn
    }]
  })
}

# Lambda function
resource "aws_lambda_function" "main" {
  function_name = var.function_name
  role          = aws_iam_role.lambda_exec.arn
  runtime       = "nodejs20.x"
  handler       = "index.handler"
  memory_size   = 512
  timeout       = 15
  architectures = ["x86_64"]

  filename         = "function.zip"
  source_code_hash = filebase64sha256("function.zip")

  environment {
    variables = {
      DB_HOST = "prod-db.example.com"
      DB_PORT = "5432"
    }
  }

  kms_key_arn = aws_kms_key.lambda_env.arn

  tracing_config {
    mode = "Active"
  }

  vpc_config {
    subnet_ids         = ["subnet-aaa", "subnet-bbb"]
    security_group_ids = [aws_security_group.lambda.id]
  }

  layers = [
    "arn:aws:lambda:${data.aws_region.current.name}:464622532012:layer:AWS-Parameters-and-Secrets-Lambda-Extension:11"
  ]

  depends_on = [
    aws_cloudwatch_log_group.lambda,
    aws_iam_role_policy.lambda_logs,
  ]
}

# On-failure destination
resource "aws_lambda_function_event_invoke_config" "main" {
  function_name          = aws_lambda_function.main.function_name
  maximum_retry_attempts = 2
  maximum_event_age_in_seconds = 21600

  destination_config {
    on_failure {
      destination = aws_sqs_queue.dlq.arn
    }
  }
}

# Reserved concurrency
resource "aws_lambda_provisioned_concurrency_config" "main" {
  function_name                     = aws_lambda_function.main.function_name
  qualifier                         = aws_lambda_alias.prod.name
  provisioned_concurrent_executions = 10
}
```


## Step 10 deep dive: packaging — zip vs ECR (moved from SKILL.md)

**Zip package (for functions <= 50 MB compressed / 250 MB uncompressed):**

```bash
# Package the function
zip -r function.zip index.js node_modules/

# Deploy
aws lambda create-function \
  --function-name <name> \
  --runtime nodejs20.x \
  --handler index.handler \
  --role arn:aws:iam::<account-id>:role/<execution-role> \
  --zip-file fileb://function.zip
```

**ECR container image (for functions > 50 MB or custom runtime):**

```dockerfile
FROM public.ecr.aws/lambda/nodejs:20
COPY app.js package*.json ./
RUN npm ci --production
CMD [ "app.handler" ]
```

```bash
# Build and push
docker build -t <name> .
docker tag <name>:latest <account-id>.dkr.ecr.<region>.amazonaws.com/<name>:latest
aws ecr get-login-password | docker login --username AWS --password-stdin <account-id>.dkr.ecr.<region>.amazonaws.com
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/<name>:latest

# Deploy
aws lambda create-function \
  --function-name <name> \
  --package-type Image \
  --code ImageUri=<account-id>.dkr.ecr.<region>.amazonaws.com/<name>:latest \
  --role arn:aws:iam::<account-id>:role/<execution-role>
```

The execution role needs `ecr:BatchGetImage` and
`ecr:GetDownloadUrlForLayer` on the ECR repository, OR you can use a
resource-based ECR policy.


## Step 11 deep dive: logging CLI (moved from SKILL.md)

```bash
aws logs create-log-group \
  --log-group-name /aws/lambda/<name> \
  --retention-in-days 30
```

If the log group already exists, update retention:

```bash
aws logs put-retention-policy \
  --log-group-name /aws/lambda/<name> \
  --retention-in-days 30
```

