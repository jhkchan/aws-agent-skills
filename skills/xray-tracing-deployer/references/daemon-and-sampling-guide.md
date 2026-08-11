# Daemon and Sampling Guide — X-Ray Tracing Deployer

Full copy-pasteable CLI command sequence for daemon deployment (EC2,
ECS, EKS, Lambda), sampling rule creation (default + custom), IAM role
setup, group creation, and Terraform / CloudFormation equivalents.

Variables to substitute: `<region>`, `<account-id>`, `<service>`,
`<app-role>`, `<cluster>`, `<task-family>`, `<function-name>`.

## Step 0: Prerequisites check

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region)

# Confirm app role has X-Ray permissions
aws iam list-attached-role-policies --role-name <app-role> \
  --query 'AttachedPolicies[*].PolicyName'
aws iam list-role-policies --role-name <app-role>

# Confirm region supports X-Ray
aws xray get-sampling-rules --region <region> --query 'SamplingRuleRecords[0].SamplingRule.RuleName'

# Confirm VPC endpoint (if private VPC, no NAT)
aws ec2 describe-vpc-endpoints \
  --filter Name=service-name,Values=com.amazonaws.<region>.xray

# Confirm encryption config
aws xray get-encryption-config
```

## Step 1: IAM permissions for the application runtime role

### Option A: Managed policy (recommended)

```bash
aws iam attach-role-policy \
  --role-name <app-role> \
  --policy-arn arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess
```

`AWSXRayDaemonWriteAccess` grants:
- `xray:PutTraceSegments`
- `xray:PutTelemetryRecords`
- `xray:GetSamplingRules`
- `xray:GetSamplingTargets`
- `xray:GetEncryptionConfig`

### Option B: Custom inline policy (for least-privilege scoping)

```bash
aws iam put-role-policy \
  --role-name <app-role> \
  --policy-name <service>-xray-write \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": [
        "xray:PutTraceSegments",
        "xray:PutTelemetryRecords",
        "xray:GetSamplingRules",
        "xray:GetSamplingTargets",
        "xray:GetEncryptionConfig"
      ],
      "Resource": "*"
    }]
  }'
```

### ECS task execution role (for the daemon sidecar container)

The ECS task EXECUTION role also needs X-Ray permissions IF the daemon
container pulls from ECR (not needed for the public ECR image). If using
a private ECR-hosted daemon image, add ECR pull permissions to the
execution role.

## Step 2: X-Ray daemon deployment

### EC2 (systemd)

```bash
# Create xray user
useradd -r -s /bin/false xray

# Download the daemon
curl -o /tmp/xray.zip \
  https://s3.<region>.amazonaws.com/aws-xray-assets.<region>/xray-daemon/aws-xray-daemon-linux-3.x.zip
mkdir -p /opt/aws-xray-daemon /var/log/xray
unzip /tmp/xray.zip -d /opt/aws-xray-daemon
chown -R xray:xray /opt/aws-xray-daemon /var/log/xray

# Create systemd unit
cat > /etc/systemd/system/xray.service << 'EOF'
[Unit]
Description=AWS X-Ray Daemon
After=network.target

[Service]
Type=simple
User=xray
ExecStart=/opt/aws-xray-daemon/xray -o /var/log/xray/xray.log --region <region>
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now xray
systemctl status xray
```

### ECS Fargate (sidecar container)

Add the daemon as a second container in the SAME task definition:

```bash
aws ecs register-task-definition \
  --family <task-family> \
  --network-mode awsvpc \
  --requires-compatibilities FARGATE \
  --cpu 1024 --memory 2048 \
  --task-role-arn arn:aws:iam::<account-id>:role/<app-role> \
  --execution-role-arn arn:aws:iam::<account-id>:role/<exec-role> \
  --container-definitions '[
    {
      "name": "app",
      "image": "<app-image-uri>",
      "essential": true,
      "cpu": 768, "memory": 1536,
      "portMappings": [{"containerPort": 8080, "protocol": "tcp"}],
      "environment": [
        {"name": "AWS_XRAY_DAEMON_ADDRESS", "value": "127.0.0.1:2000"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/<service>",
          "awslogs-region": "<region>",
          "awslogs-stream-prefix": "ecs"
        }
      }
    },
    {
      "name": "xray-daemon",
      "image": "public.ecr.aws/xray/aws-xray-daemon:4.1",
      "essential": true,
      "cpu": 256, "memory": 512,
      "portMappings": [{"containerPort": 2000, "protocol": "udp"}],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/xray-daemon",
          "awslogs-region": "<region>",
          "awslogs-stream-prefix": "xray"
        }
      }
    }
  ]'
```

### ECS EC2 (daemon-as-a-service)

On ECS EC2, run the daemon as a SEPARATE ECS service (one per instance).
The app sends to the HOST IP, not localhost:

```bash
# App task definition — set the daemon address to the host IP
# The ECS task metadata endpoint v4 provides the host IP at
# ${ECS_CONTAINER_METADATA_URI_V4}/task (field: DockerId -> host IP)

# Or use the ECS task networking env:
"environment": [
  {"name": "AWS_XRAY_DAEMON_ADDRESS", "value": "<host-ip>:2000"}
]
```

### EKS / Kubernetes (DaemonSet)

```bash
cat << 'EOF' | kubectl apply -f -
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: aws-xray-daemon
  namespace: kube-system
  labels:
    app: aws-xray-daemon
spec:
  selector:
    matchLabels:
      app: aws-xray-daemon
  template:
    metadata:
      labels:
        app: aws-xray-daemon
    spec:
      serviceAccountName: aws-xray-daemon
      containers:
        - name: xray-daemon
          image: public.ecr.aws/xray/aws-xray-daemon:4.1
          imagePullPolicy: Always
          ports:
            - containerPort: 2000
              protocol: UDP
          env:
            - name: AWS_REGION
              value: "<region>"
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: aws-xray-daemon
  namespace: kube-system
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::<account-id>:role/<app-role>
EOF
```

The app deployment uses the downward API to discover the node IP:

```yaml
env:
  - name: AWS_XRAY_DAEMON_ADDRESS
    valueFrom:
      fieldRef:
        fieldPath: status.hostIP
```

### Lambda (built-in — no daemon deployment)

```bash
# Enable active tracing
aws lambda update-function-configuration \
  --function-name <function-name> \
  --tracing-config Mode=Active

# Add Powertools layer (for clean annotation syntax)
aws lambda update-function-configuration \
  --function-name <function-name> \
  --layers arn:aws:lambda:<region>:017000801446:layer:AWSLambdaPowertoolsPythonV2:75 \
  --tracing-config Mode=Active
```

## Step 3: Sampling rules

### Default rule (always present)

```bash
aws xray create-sampling-rule --cli-input-json '{
  "SamplingRule": {
    "RuleName": "Default",
    "ResourceARN": "*",
    "Priority": 10000,
    "FixedRate": 0.05,
    "ReservoirSize": 1,
    "ServiceName": "*",
    "ServiceType": "*",
    "Host": "*",
    "HTTPMethod": "*",
    "URLPath": "*",
    "Version": 1,
    "Attributes": {}
  }
}'
```

### Custom rule — 100% sampling for checkout

```bash
aws xray create-sampling-rule --cli-input-json '{
  "SamplingRule": {
    "RuleName": "<service>-checkout-100",
    "ResourceARN": "*",
    "Priority": 100,
    "FixedRate": 1.0,
    "ReservoirSize": 10,
    "ServiceName": "<service>",
    "ServiceType": "*",
    "Host": "*",
    "HTTPMethod": "POST",
    "URLPath": "/checkout/*",
    "Version": 1,
    "Attributes": {}
  }
}'
```

### Custom rule — attribute-based sampling

```bash
aws xray create-sampling-rule --cli-input-json '{
  "SamplingRule": {
    "RuleName": "production-traces-100",
    "ResourceARN": "*",
    "Priority": 50,
    "FixedRate": 1.0,
    "ReservoirSize": 5,
    "ServiceName": "*",
    "ServiceType": "*",
    "Host": "*",
    "HTTPMethod": "*",
    "URLPath": "*",
    "Version": 1,
    "Attributes": {"environment": "production"}
  }
}'
```

### List and verify sampling rules

```bash
aws xray get-sampling-rules
aws xray get-sampling-targets
```

### Update a sampling rule

```bash
aws xray update-sampling-rule --cli-input-json '{
  "SamplingRuleUpdate": {
    "RuleName": "Default",
    "FixedRate": 0.01,
    "ReservoirSize": 1
  }
}'
```

### Delete a sampling rule

```bash
aws xray delete-sampling-rule --rule-name <name>
```

## Step 4: Groups (saved filter expressions)

```bash
aws xray create-group \
  --group-name "<service>-fault-group" \
  --filter-expression 'service("<service>") { fault = true }'

aws xray create-group \
  --group-name "<service>-checkout-latency" \
  --filter-expression 'annotation.region = "us-east-1" AND service("<service>") AND response.status = 200'

aws xray get-groups
```

## Step 5: Encryption config (CMK)

```bash
# Create a CMK
KEY_ID=$(aws kms create-key \
  --description "X-Ray encryption key" \
  --query 'KeyMetadata.KeyId' --output text)

# Grant X-Ray service access to the key
aws kms create-grant \
  --key-id $KEY_ID \
  --grantee-principal xray.<region>.amazonaws.com \
  --operations Decrypt Encrypt GenerateDataKey DescribeKey

# Set X-Ray encryption config
aws xray put-encryption-config \
  --type KMS \
  --key-id $KEY_ID

aws xray get-encryption-config
```

## Step 6: Post-deployment verification

```bash
# Sampling rules and targets
aws xray get-sampling-rules
aws xray get-sampling-targets

# Service map (last 1 hour)
START=$(date -u -v-1H +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -u -d '1 hour ago' +"%Y-%m-%dT%H:%M:%SZ")
END=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
aws xray get-service-graph --start-time $START --end-time $END

# Trace summaries
aws xray get-trace-summaries --start-time $START --end-time $END

# Groups
aws xray get-groups

# Insights
aws xray get-insight-summaries --start-time $START --end-time $END

# Encryption config
aws xray get-encryption-config

# ECS task definition (daemon sidecar)
aws ecs describe-task-definition --task-definition <task-family>

# Lambda tracing config
aws lambda get-function-configuration --function-name <function-name> --query 'TracingConfig'
```

## Terraform equivalents

- `aws_xray_sampling_rule` — `rule_name`, `priority`, `fixed_rate`,
  `reservoir_size`, `service_name`, `host`, `http_method`, `url_path`,
  `attributes`.
- `aws_xray_group` — `group_name`, `filter_expression`,
  `insights_configuration`.
- `aws_xray_encryption_config` — `type = "KMS"`, `key_id`.
- `aws_iam_role_policy_attachment` — attach
  `AWSXRayDaemonWriteAccess` to the app role.
- `aws_lambda_function` — `tracing_config { mode = "Active" }`.
- `aws_ecs_task_definition` — add the `xray-daemon` sidecar container.
- `kubernetes_daemon_set` — EKS DaemonSet (via kubectl or Helm).

## CloudFormation equivalents

- `AWS::XRay::SamplingRule` — `RuleName`, `Priority`, `FixedRate`,
  `ReservoirSize`, `ServiceName`, `Host`, `HTTPMethod`, `URLPath`,
  `Attributes`.
- `AWS::XRay::Group` — `GroupName`, `FilterExpression`,
  `InsightsConfiguration`.
- `AWS::XRay::EncryptionConfig` — `Type = KMS`, `KeyId`.
- `AWS::IAM::Role` — attach `AWSXRayDaemonWriteAccess` managed policy.
- `AWS::ECS::TaskDefinition` — add the `xray-daemon` sidecar container.
- `AWS::Lambda::Function` — `TracingConfig: { Mode: Active }`.
