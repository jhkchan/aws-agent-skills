# Deployment CLI Commands — ECS Fargate Deployer

Full copy-pasteable CLI command sequence for all 10 deployment steps.
Variables to substitute: `<cluster>`, `<region>`, `<account-id>`,
`<exec-role>`, `<task-role>`, `<family>`, `<image-uri>`, `<service>`,
`<subnets>`, `<security-group>`, `<tg-arn>`, `<log-group>`.

## Step 0: Prerequisites check

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region)

# Confirm cluster exists with Fargate capacity provider
aws ecs describe-clusters --clusters <cluster> --include ATTACHMENTS

# Confirm ECR image exists
aws ecr describe-images \
  --repository-name <repo> \
  --image-ids imageTag=<tag>

# Confirm execution role + task role trust policy
aws iam get-role --role-name <exec-role> --query 'Role.AssumeRolePolicyDocument'
aws iam get-role --role-name <task-role> --query 'Role.AssumeRolePolicyDocument'
```

## Step 1: Task execution role + task role (separate)

```bash
# Task EXECUTION role — used by ECS agent (image pull, log write, secret fetch)
aws iam create-role \
  --role-name <service>-exec \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ecs-tasks.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach managed AmazonECSTaskExecutionRolePolicy (ECR + CloudWatch)
aws iam attach-role-policy \
  --role-name <service>-exec \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# Add Secrets Manager + SSM + KMS (inline scoped to specific ARNs)
aws iam put-role-policy \
  --role-name <service>-exec \
  --policy-name <service>-secrets \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": ["secretsmanager:GetSecretValue"],
        "Resource": "arn:aws:secretsmanager:<region>:<account-id>:secret:<service>/*"
      },
      {
        "Effect": "Allow",
        "Action": ["ssm:GetParameters"],
        "Resource": "arn:aws:ssm:<region>:<account-id>:parameter/<service>/*"
      },
      {
        "Effect": "Allow",
        "Action": ["kms:Decrypt"],
        "Resource": "arn:aws:kms:<region>:<account-id>:key/<key-id>"
      }
    ]
  }'

# Task ROLE — used by application code at runtime
aws iam create-role \
  --role-name <service>-task \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ecs-tasks.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Application permissions (DynamoDB + S3 example)
aws iam put-role-policy \
  --role-name <service>-task \
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
      }
    ]
  }'
```

## Step 2: Pre-create CloudWatch log group with retention

```bash
aws logs create-log-group --log-group-name /ecs/<service>
aws logs put-retention-policy \
  --log-group-name /ecs/<service> \
  --retention-in-days 30
```

## Step 3: Register task definition

```bash
aws ecs register-task-definition \
  --family <family> \
  --network-mode awsvpc \
  --requires-compatibilities FARGATE \
  --cpu 512 \
  --memory 1024 \
  --execution-role-arn arn:aws:iam::<account-id>:role/<service>-exec \
  --task-role-arn arn:aws:iam::<account-id>:role/<service>-task \
  --runtime-platform operatingSystemFamily=LINUX,cpuArchitecture=X86_64 \
  --container-definitions '[
    {
      "name": "app",
      "image": "<image-uri>",
      "essential": true,
      "cpu": 0,
      "memory": 0,
      "portMappings": [{"containerPort": 8080, "protocol": "tcp"}],
      "environment": [
        {"name": "LOG_LEVEL", "value": "info"},
        {"name": "DB_HOST", "value": "prod-db.cluster.example.rds.amazonaws.com"}
      ],
      "secrets": [
        {"name": "DB_PASSWORD", "valueFrom": "arn:aws:secretsmanager:<region>:<account-id>:secret:<service>/db-XXXXXX"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/<service>",
          "awslogs-region": "<region>",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8080/healthz || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]'
```

## Step 4: ALB target group (target_type=ip REQUIRED)

```bash
aws elbv2 create-target-group \
  --name tg-<service> \
  --protocol HTTP \
  --port 8080 \
  --vpc-id vpc-xxx \
  --target-type ip \
  --health-check-path /healthz \
  --health-check-interval-seconds 30 \
  --health-check-timeout-seconds 5 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3 \
  --matcher HttpCode=200
```

## Step 5: ALB listener rule

```bash
aws elbv2 create-listener-rule \
  --listener-arn arn:aws:elasticloadbalancing:<region>:<account-id>:listener/app/<alb>/<id>/<listener-id> \
  --priority 10 \
  --conditions Field=path-pattern,Values=["/<service>/*"] \
  --actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:<region>:<account-id>:targetgroup/tg-<service>/<id>
```

## Step 6: Security group for the task

```bash
# Create SG allowing inbound from the ALB SG
aws ec2 create-security-group \
  --group-name sg-<service> \
  --description "ECS <service> task SG" \
  --vpc-id vpc-xxx

aws ec2 authorize-security-group-ingress \
  --group-id <task-sg-id> \
  --protocol tcp \
  --port 8080 \
  --source-group <alb-sg-id>
```

## Step 7: Create ECS service (with circuit breaker + capacity provider strategy)

```bash
aws ecs create-service \
  --cluster <cluster> \
  --service-name <service> \
  --task-definition <family>:1 \
  --desired-count 3 \
  --scheduling-strategy REPLICA \
  --deployment-controller type=ECS \
  --deployment-configuration \
    deploymentCircuitBreaker={enable=true,rollback=true},\
minimumHealthyPercent=100,maximumPercent=200,\
availabilityZoneRebalancing=ENABLED \
  --capacity-provider-strategy \
    capacityProvider=FARGATE,weight=4,base=2 \
    capacityProvider=FARGATE_SPOT,weight=1 \
  --network-configuration \
    awsvpcConfiguration={subnets=[subnet-aaa,subnet-bbb],securityGroups=[<task-sg-id>],assignPublicIp=DISABLED} \
  --load-balancers \
    targetGroupArn=arn:aws:elasticloadbalancing:<region>:<account-id>:targetgroup/tg-<service>/<id>,\
containerName=app,containerPort=8080
```

## Step 8: Auto-scaling (target tracking on CPU)

```bash
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --scalable-dimension ecs:service:DesiredCount \
  --resource-id service/<cluster>/<service> \
  --min-capacity 3 \
  --max-capacity 12

aws application-autoscaling put-scaling-policy \
  --service-namespace ecs \
  --scalable-dimension ecs:service:DesiredCount \
  --resource-id service/<cluster>/<service> \
  --policy-name <service>-cpu-60 \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{
    "TargetValue": 60.0,
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
    },
    "ScaleOutCooldown": 60,
    "ScaleInCooldown": 300
  }'
```

## Step 9: Tag the service

```bash
aws ecs tag-resource \
  --resource-arn arn:aws:ecs:<region>:<account-id>:service/<cluster>/<service> \
  --tags key=Environment,value=production key=Application,value=<service>
```

## Step 10: Post-deployment verification

```bash
aws ecs describe-services --cluster <cluster> --services <service>
aws ecs describe-task-definition --task-definition <family>:1
aws ecs describe-tasks --cluster <cluster> --tasks <task-id>
aws ec2 describe-security-groups --group-ids <task-sg-id>
aws elbv2 describe-target-health --target-group-arn <tg-arn>
aws logs describe-log-groups --log-group-name-prefix /ecs/<service>
aws application-autoscaling describe-scaling-policies \
  --service-namespace ecs \
  --resource-id service/<cluster>/<service>
```

## Terraform equivalents

- `aws_ecs_task_definition` — task definition with `family`, `cpu`,
  `memory`, `container_definitions`, `execution_role_arn`,
  `task_role_arn`, `network_mode = "awsvpc"`,
  `requires_compatibilities = ["FARGATE"]`.
- `aws_ecs_service` — service with `cluster`, `task_definition`,
  `desired_count`, `launch_type = "FARGATE"` (or
  `capacity_provider_strategy`), `network_configuration`,
  `load_balancer`, `deployment_circuit_breaker`,
  `deployment_minimum_healthy_percent`,
  `deployment_maximum_percent`.
- `aws_lb_target_group` — `target_type = "ip"`, `port`, `vpc_id`,
  `health_check`.
- `aws_lb_listener_rule` — `listener_arn`, `priority`, `conditions`,
  `actions`.
- `aws_appautoscaling_target` and `aws_appautoscaling_policy` — for
  target tracking.
- `aws_iam_role` (two) — execution role (with
  `AmazonECSTaskExecutionRolePolicy` + custom secrets inline) and task
  role (application permissions).

## CloudFormation equivalents

- `AWS::ECS::TaskDefinition` — `Family`, `Cpu`, `Memory`,
  `ContainerDefinitions`, `ExecutionRoleArn`, `TaskRoleArn`,
  `NetworkMode: awsvpc`.
- `AWS::ECS::Service` — `Cluster`, `TaskDefinition`, `DesiredCount`,
  `LaunchType: FARGATE`, `NetworkConfiguration`,
  `LoadBalancers`, `DeploymentConfiguration`.
- `AWS::ElasticLoadBalancingV2::TargetGroup` — `TargetType: ip`.
- `AWS::ApplicationAutoScaling::ScalableTarget` and
  `AWS::ApplicationAutoScaling::ScalingPolicy`.
