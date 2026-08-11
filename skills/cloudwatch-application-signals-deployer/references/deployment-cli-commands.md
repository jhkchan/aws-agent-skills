# Deployment CLI Commands — Application Signals Deployer

Full copy-pasteable CLI command sequence for all 10 enablement steps.
Variables to substitute: `<region>`, `<account-id>`, `<service-name>`,
`<environment>`, `<runtime>`, `<role-name>`, `<cluster-name>`.

## Step 0: Prerequisites check

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=${AWS_DEFAULT_REGION:-us-east-1}

# Confirm Application Signals is opted in (no error = enabled)
aws application-signals list-services --region ${REGION}

# Confirm the AWS service-linked role exists
aws iam get-role --role-name AWSServiceRoleForCloudWatchApplicationSignals

# Confirm workload role policies
aws iam list-attached-role-policies --role-name <role-name>

# Confirm X-Ray default sampling rule exists and FixedRate >= 0.05
aws xray get-sampling-rules --region ${REGION} \
  --query 'SamplingRuleRecords[?SamplingRule.RuleName==`Default`].SamplingRule'
```

## Step 1: Opt in the account (if not yet opted in)

```bash
# First call to ListServices opts the account in.
# To attach the service-linked role explicitly:
aws iam create-service-linked-role \
  --aws-service-name cloudwatch.application-signals.amazonaws.com
```

## Step 2: Attach IAM policies to the workload role

```bash
WORKLOAD_ROLE=<role-name>

aws iam attach-role-policy \
  --role-name ${WORKLOAD_ROLE} \
  --policy-arn arn:aws:iam::aws:policy/CloudWatchApplicationSignalsReportServiceAccess

aws iam attach-role-policy \
  --role-name ${WORKLOAD_ROLE} \
  --policy-arn arn:aws:iam::aws:policy/AWSXrayWriteOnlyAccess

# Verify both attached
aws iam list-attached-role-policies --role-name ${WORKLOAD_ROLE} \
  --query 'AttachedPolicies[].PolicyArn'
```

The `CloudWatchApplicationSignalsReportServiceAccess` policy grants
permissions to publish the derived RED metrics and service topology to
the `AWS/ApplicationSignals` and `AWS/ApplicationSignalsClient` metric
namespaces. The `AWSXrayWriteOnlyAccess` policy grants X-Ray segment
write permissions.

## Step 3a: ECS Fargate task definition (Java sidecar pattern)

Register a task definition with the ADOT collector sidecar and the
auto-instrumentation Java agent injected into the application container.

```bash
cat > /tmp/payments-api-task-def.json <<'EOF'
{
  "family": "payments-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::<account-id>:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::<account-id>:role/payments-api-task",
  "containerDefinitions": [
    {
      "name": "payments-api",
      "image": "<account-id>.dkr.ecr.<region>.amazonaws.com/payments-api:latest",
      "cpu": 512,
      "memory": 1024,
      "essential": true,
      "environment": [
        { "name": "AWS_SERVICE_NAME", "value": "payments-api" },
        { "name": "AWS_APPLICATION_ENVIRONMENT", "value": "prod" },
        { "name": "OTEL_EXPORTER_OTLP_ENDPOINT", "value": "http://localhost:4317" },
        { "name": "OTEL_RESOURCE_ATTRIBUTES", "value": "service.name=payments-api,service.namespace=payments" },
        { "name": "JAVA_TOOL_OPTIONS", "value": "-javaagent:/opt/aws-opentelemetry-agent/aws-opentelemetry-agent.jar" }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/payments-api",
          "awslogs-region": "<region>",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "dependsOn": [
        { "containerName": "aws-otel-collector", "condition": "START" }
      ]
    },
    {
      "name": "aws-otel-collector",
      "image": "public.ecr.aws/aws-observability/aws-otel-collector:latest",
      "cpu": 512,
      "memory": 512,
      "essential": true,
      "command": ["--config=/etc/otel-collector-config.yaml"],
      "environment": [
        { "name": "AWS_PROMETHEUS_SCRAPING_SERVICE_NAME", "value": "payments-api-otel" }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/payments-api-otel",
          "awslogs-region": "<region>",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
EOF

aws ecs register-task-definition \
  --cli-input-json file:///tmp/payments-api-task-def.json
```

The ADOT collector configuration file (`/etc/otel-collector-config.yaml`
baked into the sidecar image, or mounted via a ConfigMap-style volume)
ships traces to X-Ray and the derived metrics to CloudWatch via the
`awsemf` exporter.

## Step 3b: EKS — install the OpenTelemetry Operator

```bash
helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
helm repo update

helm install opentelemetry-operator open-telemetry/opentelemetry-operator \
  --namespace opentelemetry-operator-system --create-namespace \
  --set admissionWebhooks.certManager.enabled=false \
  --set manager.collectorImage.repository=public.ecr.aws/aws-observability/aws-otel-collector

# Annotate the workload deployment to enable Java injection
kubectl annotate deploy payments-api \
  instrumentation.opentelemetry.io/inject-java="true" \
  instrumentation.opentelemetry.io/container-names="payments-api"

# Roll the deployment so the webhook mutates new pods
kubectl rollout restart deploy/payments-api
```

For Python workloads:

```bash
kubectl annotate deploy payments-api \
  instrumentation.opentelemetry.io/inject-python="true"
```

## Step 3c: EC2 — install CloudWatch agent + ADOT Java agent

```bash
# Install CloudWatch agent via SSM Run Command
aws ssm send-command \
  --document-name AmazonCloudWatch-ManageAgent \
  --document-version "1" \
  --targets "Key=tag:Name,Values=payments-api-instance" \
  --parameters '{"action":["configure"],"mode":["ec2"],"optionalConfigurationSource":["ssm"],"optionalConfigurationLocation":["AmazonCloudWatch-payments-api"],"optionalRestart":["yes"]}'

# ADOT Java agent baked into the AMI or installed via user-data
# JAVA_TOOL_OPTIONS=-javaagent:/opt/aws-opentelemetry-agent/aws-opentelemetry-agent.jar
```

## Step 3d: Lambda — attach the ADOT layer

```bash
# Java 21 Lambda (x86_64)
aws lambda update-function-configuration \
  --function-name payments-api \
  --layers arn:aws:lambda:<region>:901920570463:layer:aws-otel-java-wrapper-amd64:19 \
  --environment Variables='{AWS_SERVICE_NAME=payments-api,AWS_APPLICATION_ENVIRONMENT=prod,OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317}'

# Python 3.12 Lambda (x86_64)
aws lambda update-function-configuration \
  --function-name payments-api \
  --layers arn:aws:lambda:<region>:901920570463:layer:aws-otel-python-amd64-3-12:5
```

Layer ARNs are Region-specific. Get the latest from
https://aws-otel.github.io/docs/getting-started/lambda/lambda.

## Step 4: Set service name + environment labels

These environment variables are REQUIRED on the application container:

```bash
AWS_SERVICE_NAME=<service-name>
AWS_APPLICATION_ENVIRONMENT=<environment>
OTEL_RESOURCE_ATTRIBUTES=service.name=<service-name>,service.namespace=<namespace>
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

For Java, also set:
```bash
JAVA_TOOL_OPTIONS=-javaagent:/opt/aws-opentelemetry-agent/aws-opentelemetry-agent.jar
```

For Python:
```bash
OTEL_PYTHON_FLASK_EXCLUDED_URLS=/health,/metrics
```

## Step 5: Configure X-Ray sampling

```bash
cat > /tmp/sampling-rule.json <<'EOF'
{
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
}
EOF

# Update if Default already exists, otherwise create
aws xray create-sampling-rule --cli-input-json file:///tmp/sampling-rule.json \
  || aws xray update-sampling-rule --cli-input-json file:///tmp/sampling-rule.json
```

For a low-traffic service under initial verification, set `FixedRate=1.0`
for the first 30 minutes, then drop to `0.05`.

## Step 6: Wire service discovery

**CloudMap enrichment (optional):**

```bash
NAMESPACE_ID=$(aws servicediscovery list-namespaces \
  --query 'Namespaces[?Name==`payments.local`].Id' --output text)

aws servicediscovery create-service \
  --name payments-api \
  --namespace-id ${NAMESPACE_ID} \
  --dns-config '{"NamespaceId":"'${NAMESPACE_ID}'","DnsRecords":[{"Type":"A","TTL":10}]}'
```

**Kubernetes enrichment:** the OTel Operator's Kubernetes attributes
processor tags traces automatically with `k8s.pod.name`,
`k8s.namespace.name`, and `k8s.service.name`. No additional CLI step.

Discovery is eventually consistent — expect 5-10 minutes after the
first trace arrives.

## Step 7: Verify RED metrics

After 5-10 minutes of trace flow, check the `AWS/ApplicationSignals`
namespace:

```bash
aws cloudwatch list-metrics --namespace AWS/ApplicationSignals \
  --metric-name Latency \
  --dimensions Name=ServiceName,Value=<service-name>

aws cloudwatch list-metrics --namespace AWS/ApplicationSignals \
  --metric-name ErrorRate \
  --dimensions Name=ServiceName,Value=<service-name>

aws cloudwatch list-metrics --namespace AWS/ApplicationSignals \
  --metric-name CallCount \
  --dimensions Name=ServiceName,Value=<service-name>

# Raw metric values for the last 15 minutes
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationSignals \
  --metric-name Latency \
  --dimensions Name=ServiceName,Value=<service-name> Name=Environment,Value=prod \
  --start-time $(date -u +%FT%TZ --date='15 min ago') \
  --end-time $(date -u +%FT%TZ) \
  --period 60 --statistics p95,Average
```

## Step 8: Create the SLO (CloudFormation)

```bash
cat > /tmp/availability-slo.yaml <<'EOF'
AWSTemplateFormatVersion: '2010-09-09'
Description: Application Signals availability SLO for payments-api
Resources:
  PaymentsApiAvailabilitySLO:
    Type: AWS::ApplicationSignals::ServiceLevelObjective
    Properties:
      Name: payments-api-availability-slo
      Description: 99.9% successful requests over 28 days rolling
      EvaluationType: PeriodBased
      Goal:
        Interval:
          RollingInterval:
            DurationUnit: DAY
            Duration: 28
          BurnRates:
            - RollupInterval: MINUTE
            - RollupInterval: HOUR
        AttainmentGoal: 0.999
        WarningThreshold: 0.995
      RequestBasedSliConfig:
        MetricThreshold: 200
        GoodRequestsMetric:
          MetricStat:
            Metric:
              Namespace: AWS/ApplicationSignals
              MetricName: CallCount
              Dimensions:
                - Name: ServiceName
                  Value: payments-api
                - Name: Environment
                  Value: prod
            Period: 60
            Stat: Sum
        TotalRequestsMetric:
          MetricStat:
            Metric:
              Namespace: AWS/ApplicationSignals
              MetricName: CallCount
              Dimensions:
                - Name: ServiceName
                  Value: payments-api
                - Name: Environment
                  Value: prod
            Period: 60
            Stat: Sum
Outputs:
  SLOId:
    Value: !Ref PaymentsApiAvailabilitySLO
EOF

aws cloudformation deploy \
  --stack-name payments-api-slo \
  --template-file /tmp/availability-slo.yaml \
  --capabilities CAPABILITY_IAM \
  --region <region>
```

## Step 9: Create the burn-rate alarms

```bash
SLO_ID=$(aws application-signals list-service-level-objectives \
  --query 'ServiceLevelObjectives[?Name==`payments-api-availability-slo`].Id' \
  --output text)

# Fast burn — 5-minute window, 14.4x threshold = 2% of budget in 5 min
aws cloudwatch put-metric-alarm \
  --alarm-name payments-api-slo-burn-fast \
  --namespace AWS/ApplicationSignals \
  --metric-name BurnRate \
  --dimensions Name=SLOId,Value=${SLO_ID} Name=RollupInterval,Value=MINUTE \
  --period 300 --evaluation-periods 1 \
  --threshold 14.4 \
  --comparison-operator GreaterThanThreshold \
  --treat-missing-data noData \
  --alarm-actions arn:aws:sns:<region>:<account-id>:oncall-page

# Medium burn — 1-hour window, 6x threshold = 10% of budget in 1 hour
aws cloudwatch put-metric-alarm \
  --alarm-name payments-api-slo-burn-medium \
  --namespace AWS/ApplicationSignals \
  --metric-name BurnRate \
  --dimensions Name=SLOId,Value=${SLO_ID} Name=RollupInterval,Value=HOUR \
  --period 3600 --evaluation-periods 1 \
  --threshold 6 \
  --comparison-operator GreaterThanThreshold \
  --treat-missing-data noData \
  --alarm-actions arn:aws:sns:<region>:<account-id>:oncall-page

# Slow burn — 6-hour window, 3x threshold = 10% of budget in 6 hours
aws cloudwatch put-metric-alarm \
  --alarm-name payments-api-slo-burn-slow \
  --namespace AWS/ApplicationSignals \
  --metric-name BurnRate \
  --dimensions Name=SLOId,Value=${SLO_ID} Name=RollupInterval,Value=HOUR \
  --period 21600 --evaluation-periods 1 \
  --threshold 3 \
  --comparison-operator GreaterThanThreshold \
  --treat-missing-data noData \
  --alarm-actions arn:aws:sns:<region>:<account-id>:oncall-ticket
```

## Step 10: Final verification

```bash
# Service appears in Application Signals service list
aws application-signals list-services --region <region>

# SLO created and active
aws application-signals list-service-level-objectives --region <region>

# Burn-rate alarms created
aws cloudwatch describe-alarms --alarm-name-prefix payments-api-slo

# X-Ray traces are flowing
aws xray get-trace-summaries \
  --start-time $(date -u +%s --date='10 min ago') \
  --end-time $(date -u +%s) \
  --filter-expression 'service.id = "payments-api"'

# RED metrics published to CloudWatch
aws cloudwatch list-metrics --namespace AWS/ApplicationSignals \
  --dimensions Name=ServiceName,Value=payments-api
```

## Terraform equivalents

```hcl
# 1. IAM policies
resource "aws_iam_role_policy_attachment" "app_signals" {
  role       = aws_iam_role.payments_api_task.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchApplicationSignalsReportServiceAccess"
}

resource "aws_iam_role_policy_attachment" "xray_write" {
  role       = aws_iam_role.payments_api_task.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXrayWriteOnlyAccess"
}

# 2. X-Ray sampling rule
resource "aws_xray_sampling_rule" "default" {
  rule_name      = "Default"
  priority       = 10000
  fixed_rate     = 0.05
  reservoir_size = 1
  service_name   = "*"
  service_type   = "*"
  host           = "*"
  http_method    = "*"
  url_path       = "*"
  version        = 1
}

# 3. SLO
resource "aws_application_signals_service_level_objective" "availability" {
  name            = "payments-api-availability-slo"
  description     = "99.9% successful requests over 28 days rolling"
  evaluation_type = "PeriodBased"

  goal {
    interval {
      rolling_interval {
        duration_unit = "DAY"
        duration      = 28
      }
      burn_rates {
        rollup_interval = "MINUTE"
      }
      burn_rates {
        rollup_interval = "HOUR"
      }
    }
    attainment_goal   = 0.999
    warning_threshold = 0.995
  }

  request_based_sli_config {
    metric_threshold = 200
    good_requests_metric {
      metric_stat {
        metric {
          namespace   = "AWS/ApplicationSignals"
          metric_name = "CallCount"
          dimensions {
            name  = "ServiceName"
            value = "payments-api"
          }
        }
        period = 60
        stat   = "Sum"
      }
    }
  }
}
```

## Cleanup

```bash
# Detach policies (does NOT delete the role)
aws iam detach-role-policy --role-name <role-name> \
  --policy-arn arn:aws:iam::aws:policy/CloudWatchApplicationSignalsReportServiceAccess
aws iam detach-role-policy --role-name <role-name> \
  --policy-arn arn:aws:iam::aws:policy/AWSXrayWriteOnlyAccess

# Delete SLOs
aws cloudformation delete-stack --stack-name payments-api-slo

# Delete burn-rate alarms
aws cloudwatch delete-alarms --alarm-names \
  payments-api-slo-burn-fast payments-api-slo-burn-medium payments-api-slo-burn-slow

# DO NOT delete the AWS service-linked role (it auto-recreates)
```
