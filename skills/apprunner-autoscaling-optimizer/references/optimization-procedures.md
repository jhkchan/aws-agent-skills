# App Runner Optimization Procedures Reference

Load this reference when optimizing an App Runner service's autoscaling
configuration. The procedures below cover the canonical sequences for
each optimization dimension, with the CLI commands and the expected
outcome.

## Decision tree — which optimization to apply

| Observation | Optimization | Expected savings |
|---|---|---|
| Non-prod service runs 24/7 | Pause/resume outside business hours | 70-75% of compute |
| Concurrency > 2x observed peak | Increase concurrency | 10-30% of compute |
| MinSize > steady-state instances | Reduce MinSize (or set to 0) | 10-50% of compute |
| CPU < 25% AND Memory < 40% on 2/4 vCPU | Downgrade instance type | 30-50% of per-instance cost |
| CPU > 70% OR Memory > 80% | Upgrade instance type + increase concurrency | Cost neutral, latency improvement |
| NAT gateway cost > 30% of compute | Add VPC endpoints for AWS services | 20-80% of NAT cost |
| Health check interval < 5s with restarts | Increase interval to 10-15s | Reduced restart cost |
| MaxSize < peak instance count | Increase MaxSize | Prevents 5xx (no cost change) |
| Verbose logging, high traffic | Reduce log verbosity / sampling | 10-40% of log ingestion cost |

## Procedure: Concurrency tuning

**When to apply:** Concurrency setting is > 2x the observed peak concurrent
requests per instance, AND CPU/memory utilization has headroom.

**Step 1 — Measure current state:**

```bash
# Get the current auto-scaling configuration
aws apprunner describe-auto-scaling-configuration \
  --auto-scaling-configuration-arn <arn> \
  --query '{MinSize:AutoScalingConfiguration.MinSize,MaxSize:AutoScalingConfiguration.MaxSize,Concurrency:AutoScalingConfiguration.Concurrency}'

# Get instance count over the last 30 days
aws cloudwatch get-metric-statistics \
  --namespace AWS/AppRunner \
  --metric-name InstanceCount \
  --dimensions Name=ServiceId,Value=<service-id> \
  --start-time $(date -u -v-30d +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 --statistics Average,Maximum \
  --output text

# Get CPU utilization
aws cloudwatch get-metric-statistics \
  --namespace AWS/AppRunner \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceId,Value=<service-id> \
  --start-time $(date -u -v-30d +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 --statistics Average,Maximum
```

**Step 2 — Calculate new concurrency:**

```
current_concurrency = <from config>
peak_concurrent_per_instance = peak_request_rate / peak_instance_count
new_concurrency = peak_concurrent_per_instance * 1.5  (50% headroom)
```

Do NOT increase by more than 50% in one step. Gradual increases allow
monitoring for latency degradation.

**Step 3 — Create and apply new configuration:**

```bash
aws apprunner create-auto-scaling-configuration \
  --auto-scaling-configuration-name <service>-asg-v2 \
  --min-size <current-min> \
  --max-size <current-max> \
  --concurrency <new-concurrency>

aws apprunner update-service \
  --service-arn <arn> \
  --auto-scaling-configuration-arn <new-config-arn>
```

**Step 4 — Monitor for 7 days:**

```bash
# Check latency did not degrade
aws cloudwatch get-metric-statistics \
  --namespace AWS/AppRunner \
  --metric-name Latency \
  --dimensions Name=ServiceId,Value=<service-id> \
  --start-time $(date -u -v-7d +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 --statistics Average --output text

# Check 5xx did not increase
aws cloudwatch get-metric-statistics \
  --namespace AWS/AppRunner \
  --metric-name 5xxResponseCount \
  --dimensions Name=ServiceId,Value=<service-id> \
  --start-time $(date -u -v-7d +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 --statistics Sum --output text
```

**Rollback if latency p95 increases > 20%:**

```bash
aws apprunner update-service \
  --service-arn <arn> \
  --auto-scaling-configuration-arn <original-config-arn>
```

## Procedure: MinSize right-sizing

**When to apply:** MinSize > 0 and the service has periods of zero or near-
zero traffic.

```bash
# Check traffic pattern
aws cloudwatch get-metric-statistics \
  --namespace AWS/AppRunner \
  --metric-name RequestCount \
  --dimensions Name=ServiceId,Value=<service-id> \
  --start-time $(date -u -v-30d +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 --statistics Sum --output text
```

If RequestCount = 0 for significant periods:

```bash
aws apprunner create-auto-scaling-configuration \
  --auto-scaling-configuration-name <service>-asg-min0 \
  --min-size 0 \
  --max-size <current-max> \
  --concurrency <current>

aws apprunner update-service \
  --service-arn <arn> \
  --auto-scaling-configuration-arn <new-config-arn>
```

**Savings calculation:**

```
idle_hours_per_month = hours_with_zero_traffic
savings = MinSize * hourly_rate * idle_hours_per_month
```

## Procedure: Instance type downgrade

**When to apply:** CPU < 25% AND memory < 40% sustained over 30 days on
2 vCPU / 4 GB or 4 vCPU / 8 GB.

```bash
# Verify CPU and memory headroom
aws cloudwatch get-metric-statistics \
  --namespace AWS/AppRunner \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceId,Value=<service-id> \
  --start-time $(date -u -v-30d +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 86400 --statistics Average,Maximum --output text

aws cloudwatch get-metric-statistics \
  --namespace AWS/AppRunner \
  --metric-name MemoryUtilization \
  --dimensions Name=ServiceId,Value=<service-id> \
  --start-time $(date -u -v-30d +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 86400 --statistics Average,Maximum --output text
```

If peak CPU < 40% and peak memory < 60%:

```bash
aws apprunner update-service \
  --service-arn <arn> \
  --instance-configuration '{"Cpu":"1 vCPU","Memory":"2 GB"}'
```

**Savings calculation:**

```
current_hourly = current_type_rate (e.g., $0.126 for 2 vCPU/4 GB)
new_hourly = new_type_rate (e.g., $0.063 for 1 vCPU/2 GB)
avg_instances = average InstanceCount over 30 days
savings = (current_hourly - new_hourly) * avg_instances * 730
```

## Procedure: Pause/resume for non-prod

**When to apply:** Service is in a dev/staging/QA environment and is not
needed 24/7.

**Automate with EventBridge + Lambda:**

```python
# pause_lambda.py
import boto3
apprunner = boto3.client('apprunner')

def lambda_handler(event, context):
    arn = 'arn:aws:apprunner:us-east-1:111111111111:service/dev-service/abc'
    apprunner.pause_service(ServiceArn=arn)
    return {'statusCode': 200, 'body': 'Service paused'}
```

```bash
# Create EventBridge rules
aws events put-rule --name apprunner-pause-dev \
  --schedule-expression "cron(0 19 ? * MON-FRI *)"

aws events put-rule --name apprunner-resume-dev \
  --schedule-expression "cron(0 7 ? * MON-FRI *)"

# Add Lambda targets
aws events put-targets --rule apprunner-pause-dev \
  --targets '[{"Id":"1","Arn":"arn:aws:lambda:us-east-1:111111111111:function:apprunner-pause"}]'

aws events put-targets --rule apprunner-resume-dev \
  --targets '[{"Id":"1","Arn":"arn:aws:lambda:us-east-1:111111111111:function:apprunner-resume"}]'
```

**Savings calculation:**

```
weekday_paused_hours = 12 (7pm-7am) * 5 days = 60 hours/week
weekend_paused_hours = 48 hours/week
total_paused_hours_per_week = 108
total_paused_hours_per_month = 108 * 4.33 = ~468 hours
savings = MinSize * hourly_rate * 468
percentage = 468 / 730 = ~64%

With scale-to-zero during business hours:
  additional_idle_hours = (zero-traffic hours during 7am-7pm) * 5 days
  additional_savings = on-demand billing avoided
```

## Procedure: VPC endpoint for NAT cost reduction

**When to apply:** Service uses VPC connector with NAT gateway and has
significant traffic to AWS services (S3, DynamoDB, SQS, etc.).

**S3 Gateway endpoint (free, no hourly or per-GB charge):**

```bash
aws ec2 create-vpc-endpoint \
  --vpc-id <vpc-id> \
  --service-name com.amazonaws.us-east-1.s3 \
  --route-table-ids <rtb-id-1> <rtb-id-2>
```

**DynamoDB Interface endpoint ($0.010/hr + $0.01/GB):**

```bash
aws ec2 create-vpc-endpoint \
  --vpc-id <vpc-id> \
  --vpc-endpoint-type Interface \
  --service-name com.amazonaws.us-east-1.dynamodb \
  --subnet-ids <subnet-1> <subnet-2> \
  --security-group-ids <sg-id>
```

**Savings calculation (S3 example):**

```
s3_traffic_GB = 800 GB/month
nat_cost = 800 * $0.045 = $36/month (processing) + 800 * $0.045 = $36/month (transfer)
s3_endpoint_cost = $0 (Gateway endpoint is free)
savings = $72/month
```

## Procedure: Health check optimization

**When to apply:** Health check interval < 5 seconds with frequent instance
restarts.

```bash
# Check current health check config
aws apprunner describe-service \
  --service-arn <arn> \
  --query 'Service.HealthCheckConfiguration'

# Update health check configuration
aws apprunner update-service \
  --service-arn <arn> \
  --health-check-configuration '{"Protocol":"HTTP","Path":"/health","Interval":10,"Timeout":3,"HealthyThreshold":2,"UnhealthyThreshold":3}'
```

**Recommended values:**

| Parameter | Default | Recommended | Rationale |
|---|---|---|---|
| Interval | 5 | 10 | Less aggressive, fewer false positives |
| Timeout | 2 | 3 | Allow slow health endpoints |
| HealthyThreshold | 1 | 2 | Confirm stability before marking healthy |
| UnhealthyThreshold | 3 | 3 | Standard failure detection window |

## Procedure: Log cost reduction

**When to apply:** CloudWatch Logs ingestion is > $50/month.

```bash
# Check log volume
aws logs describe-metric-filters \
  --log-group-name /aws/apprunner/<service-id>

# Get log ingestion cost
aws ce get-cost-and-usage \
  --filter '{"Dimensions":{"Key":"UsageType","Values":["US:DataProcessing-Bytes"]}}' \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --time-period Start=2026-07-01,End=2026-08-01
```

**Options:**
1. Reduce log verbosity in the application (INFO instead of DEBUG)
2. Implement log sampling (log 1 in 10 requests for routine traffic)
3. Adjust the observability configuration:

```bash
aws apprunner update-service \
  --service-arn <arn> \
  --observability-configuration '{"ConfigurationSources":["CloudWatchLogs"],"CloudWatchLogs":{"Enabled":true}}'
```

## CLI quick-reference

| Goal | Command |
|---|---|
| Service details | `aws apprunner describe-service --service-arn <arn>` |
| Auto-scaling config | `aws apprunner describe-auto-scaling-configuration --auto-scaling-configuration-arn <arn>` |
| Create ASG config | `aws apprunner create-auto-scaling-configuration --auto-scaling-configuration-name <name> --min-size <n> --max-size <n> --concurrency <n>` |
| Update service | `aws apprunner update-service --service-arn <arn> --auto-scaling-configuration-arn <arn>` |
| Change instance type | `aws apprunner update-service --service-arn <arn> --instance-configuration '{"Cpu":"1 vCPU","Memory":"2 GB"}'` |
| Pause | `aws apprunner pause-service --service-arn <arn>` |
| Resume | `aws apprunner resume-service --service-arn <arn>` |
| Delete old ASG config | `aws apprunner delete-auto-scaling-configuration --auto-scaling-configuration-arn <arn>` |
| CloudWatch metrics | `aws cloudwatch get-metric-statistics --namespace AWS/AppRunner --metric-name <metric> ...` |
| Cost Explorer | `aws ce get-cost-and-usage --filter '{"Dimensions":{"Key":"Service","Values":["App Runner"]}}' ...` |
