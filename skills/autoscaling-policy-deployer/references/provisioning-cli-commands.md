# Provisioning CLI Commands Reference

Supplementary reference for the Auto Scaling Policy Deployer skill.
Copy-pasteable AWS CLI v2 commands organized by provisioning step.

## Pre-flight: verify ASG state

```bash
# ASG exists with sensible capacity bounds
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names <ASG> \
  --query 'AutoScalingGroups[].[AutoScalingGroupName,MinSize,MaxSize,DesiredCapacity,HealthCheckType,VPCZoneIdentifier,LaunchTemplate.{TemplateId:LaunchTemplateId,Version:Version}]'

# Multi-AZ check (VPCZoneIdentifier must contain >= 2 subnet IDs)
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names <ASG> \
  --query 'AutoScalingGroups[].VPCZoneIdentifier' --output text | tr ',' '\n' | wc -l

# Service-linked role exists
aws iam get-role --role-name AWSServiceRoleForAutoScaling \
  --query 'Role.Arn' --output text

# Account ID for ARN construction
aws sts get-caller-identity --query Account --output text
```

## Step 3: target tracking

```bash
# CPU-based (default recommendation)
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name <ASG> --policy-name cpu-target-50 \
  --policy-type TargetTrackingScaling \
  --target-tracking-configuration '{"PredefinedMetricSpecification":{"PredefinedMetricType":"ASGAverageCPUUtilization"},"TargetValue":50.0,"ScaleOutCooldown":60,"ScaleInCooldown":300}'

# ALB-based (retrieve ResourceLabel first)
aws elbv2 describe-target-groups --names <TG_NAME> --query 'TargetGroups[].TargetGroupArn' --output text
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name <ASG> --policy-name alb-req-per-target \
  --policy-type TargetTrackingScaling \
  --target-tracking-configuration '{"PredefinedMetricSpecification":{"PredefinedMetricType":"ALBRequestCountPerTarget","ResourceLabel":"app/<ALB>/<TG>"},"TargetValue":1000.0}'

# Custom metric (verify metric emits data first)
aws cloudwatch get-metric-statistics \
  --namespace AWS/SQS --metric-name ApproximateNumberOfMessagesVisible \
  --dimensions Name=QueueName,Value=my-queue \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ) --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 --statistics Average --query 'Datapoints | length'

aws autoscaling put-scaling-policy \
  --auto-scaling-group-name <ASG> --policy-name sqs-backlog-per-instance \
  --policy-type TargetTrackingScaling \
  --target-tracking-configuration '{"CustomizedMetricSpecification":{"MetricName":"ApproximateNumberOfMessagesVisible","Namespace":"AWS/SQS","Dimensions":[{"Name":"QueueName","Value":"my-queue"}],"Statistic":"Average"},"TargetValue":100.0}'
```

## Step 4: step scaling

```bash
# CloudWatch alarm FIRST
aws cloudwatch put-metric-alarm \
  --alarm-name <ASG>-sqs-depth-high \
  --metric-name ApproximateNumberOfMessagesVisible --namespace AWS/SQS \
  --statistic Average --period 60 --evaluation-periods 2 --threshold 500 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=QueueName,Value=my-queue \
  --treat-missing-data breaching \
  --alarm-actions arn:aws:autoscaling:<region>:<account>:scalingPolicy:<id>:autoScalingGroupName/<ASG>:policyName/sqs-step-scaling-out

# Step scaling policy references the alarm via alarm-actions
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name <ASG> --policy-name sqs-step-scaling-out \
  --policy-type StepScaling --adjustment-type PercentChangeInCapacity \
  --metric-aggregation-type Average \
  --step-adjustments \
    MetricIntervalLowerBound=0,MetricIntervalUpperBound=100,ScalingAdjustment=20 \
    MetricIntervalLowerBound=100,MetricIntervalUpperBound=500,ScalingAdjustment=50 \
    MetricIntervalLowerBound=500,ScalingAdjustment=100
```

## Step 5: scheduled scaling

```bash
aws autoscaling put-scheduled-update-group-action \
  --auto-scaling-group-name <ASG> \
  --scheduled-action-name business-hours-scale-up \
  --recurrence "0 9 * * Mon-Fri" \
  --min-size 3 --desired-capacity 5 --max-size 10 \
  --time-zone "America/New_York"

aws autoscaling put-scheduled-update-group-action \
  --auto-scaling-group-name <ASG> \
  --scheduled-action-name off-hours-scale-down \
  --recurrence "0 19 * * Mon-Fri" \
  --min-size 1 --desired-capacity 1 --max-size 10 \
  --time-zone "America/New_York"
```

## Step 6: warm pool

```bash
aws autoscaling put-warm-pool \
  --auto-scaling-group-name <ASG> \
  --pool-state Stopped --min-size 2 \
  --instance-reuse-policy '{"ReuseOnScaleIn": true}'
```

## Step 7: instance refresh

```bash
aws autoscaling start-instance-refresh \
  --auto-scaling-group-name <ASG> --strategy Rolling \
  --preferences '{"MinHealthyPercentage":50,"InstanceWarmup":300,"CheckpointPercentages":[50,100],"CheckpointDelay":300,"SkipMatching":true}'
```

## Step 8: advanced features

```bash
# Capacity rebalance (Spot-backed ASGs only)
aws autoscaling update-auto-scaling-group --auto-scaling-group-name <ASG> --capacity-rebalance

# Predictive scaling
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name <ASG> --policy-name predictive-cpu \
  --policy-type PredictiveScaling \
  --predictive-scaling-configuration '{"MetricSpecifications":[{"TargetValue":40.0,"PredefinedMetricPairSpecification":{"PredefinedMetricType":"ASGCPUUtilization","ResourceLabel":""}}],"Mode":"ForecastAndScale","SchedulingBufferTime":300,"MaxCapacityBreachBehavior":"IncreaseMaxCapacity","MaxCapacityBuffer":10}'

# Mixed Instances Policy (create-time)
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name <ASG> \
  --mixed-instances-policy file://mip.json \
  --min-size 2 --max-size 10 --desired-capacity 4 \
  --vpc-zone-identifier "subnet-abc,subnet-def,subnet-ghi"
```

## Step 9: verification

```bash
# All policies attached
aws autoscaling describe-policies --auto-scaling-group-names <ASG>

# Scheduled actions
aws autoscaling describe-scheduled-actions --auto-scaling-group-name <ASG>

# Warm pool
aws autoscaling describe-warm-pool --auto-scaling-group-name <ASG>

# Instance refreshes (active + history)
aws autoscaling describe-instance-refreshes --auto-scaling-group-name <ASG>

# Capacity rebalance + MIP
aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names <ASG> \
  --query 'AutoScalingGroups[].{CapRebal:CapacityRebalance,MIP:MixedInstancesPolicy.InstancesDistribution.SpotAllocationStrategy}'

# CloudWatch alarms with dual-policy detection
aws cloudwatch describe-alarms --alarm-name-prefix <ASG>

# Predictive scaling forecast non-empty
aws autoscaling describe-scaling-policies --auto-scaling-group-names <ASG> \
  --query 'ScalingPolicies[?PolicyType==`PredictiveScaling`].{Name:PolicyName,Mode:PredictiveScalingConfiguration.Mode,Forecast:PredictiveScalingConfiguration.MetricSpecifications}'

# Metric emits live datapoints
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 --metric-name CPUUtilization \
  --dimensions Name=AutoScalingGroupName,Value=<ASG> \
  --start-time $(date -u -v-24H +%Y-%m-%dT%H:%M:%SZ) --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 --statistics Average --query 'Datapoints | length'
```

## Rollback

```bash
# Delete a scaling policy
aws autoscaling delete-policy --auto-scaling-group-name <ASG> --policy-name <NAME>

# Delete a scheduled action
aws autoscaling delete-scheduled-action --auto-scaling-group-name <ASG> --scheduled-action-name <NAME>

# Delete warm pool
aws autoscaling delete-warm-pool --auto-scaling-group-name <ASG>

# Cancel instance refresh (pauses but does not revert already-replaced instances)
aws autoscaling cancel-instance-refresh --auto-scaling-group-name <ASG>

# Roll back an instance refresh (reverts to previous template)
aws autoscaling rollback-instance-refresh --auto-scaling-group-name <ASG>

# Disable capacity rebalance
aws autoscaling update-auto-scaling-group --auto-scaling-group-name <ASG> --no-capacity-rebalance
```

## 9-step procedure — Step 1: confirm ASG baseline (CLI)

```bash
aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names <ASG> \
  --query 'AutoScalingGroups[].[AutoScalingGroupName,MinSize,MaxSize,DesiredCapacity,HealthCheckType,VPCZoneIdentifier,LaunchTemplate.LaunchTemplateId]'
```

## 9-step procedure — Step 3: target tracking (CLI)

```bash
# Predefined CPU metric (recommended default)
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name <ASG> --policy-name cpu-target-50 \
  --policy-type TargetTrackingScaling \
  --target-tracking-configuration '{
    "PredefinedMetricSpecification": {"PredefinedMetricType": "ASGAverageCPUUtilization"},
    "TargetValue": 50.0, "ScaleOutCooldown": 60, "ScaleInCooldown": 300
  }'

# ALB RequestCountPerTarget (include ResourceLabel from Target Group)
#   "PredefinedMetricType": "ALBRequestCountPerTarget",
#   "ResourceLabel": "app/<ALB>/<TG>", "TargetValue": 1000.0

# Custom metric (e.g., SQS queue depth — verify Dimensions match emitted metric)
#   "CustomizedMetricSpecification": {
#     "MetricName": "ApproximateNumberOfMessagesVisible",
#     "Namespace": "AWS/SQS",
#     "Dimensions": [{"Name": "QueueName", "Value": "my-queue"}],
#     "Statistic": "Average"
#   }, "TargetValue": 100.0
```

## 9-step procedure — Step 4: step scaling (CLI)

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name <ASG>-sqs-depth-high \
  --metric-name ApproximateNumberOfMessagesVisible --namespace AWS/SQS \
  --statistic Average --period 60 --evaluation-periods 2 --threshold 500 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=QueueName,Value=my-queue \
  --treat-missing-data breaching --alarm-actions <POLICY_ARN>

aws autoscaling put-scaling-policy \
  --auto-scaling-group-name <ASG> --policy-name sqs-step-scaling-out \
  --policy-type StepScaling --adjustment-type PercentChangeInCapacity \
  --metric-aggregation-type Average \
  --step-adjustments \
    MetricIntervalLowerBound=0,MetricIntervalUpperBound=100,ScalingAdjustment=20 \
    MetricIntervalLowerBound=100,MetricIntervalUpperBound=500,ScalingAdjustment=50 \
    MetricIntervalLowerBound=500,ScalingAdjustment=100
```

## 9-step procedure — Step 5: scheduled scaling (CLI)

```bash
aws autoscaling put-scheduled-update-group-action \
  --auto-scaling-group-name <ASG> \
  --scheduled-action-name business-hours-scale-up \
  --recurrence "0 9 * * Mon-Fri" \
  --min-size 3 --desired-capacity 5 --max-size 10 \
  --time-zone "America/New_York"
```

## 9-step procedure — Step 6: warm pool (CLI)

```bash
aws autoscaling put-warm-pool \
  --auto-scaling-group-name <ASG> \
  --pool-state Stopped \
  --min-size 2 \
  --instance-reuse-policy '{"ReuseOnScaleIn": true}'
```

## 9-step procedure — Step 7: instance refresh (CLI)

```bash
aws autoscaling start-instance-refresh \
  --auto-scaling-group-name <ASG> \
  --strategy Rolling \
  --preferences '{
    "MinHealthyPercentage": 50,
    "InstanceWarmup": 300,
    "CheckpointPercentages": [50, 100],
    "CheckpointDelay": 300
  }'
```

## 9-step procedure — Step 8a: capacity rebalance (CLI)

```bash
aws autoscaling update-auto-scaling-group \
  --auto-scaling-group-name <ASG> \
  --capacity-rebalance
```

## 9-step procedure — Step 8b: predictive scaling (CLI)

```bash
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name <ASG> \
  --policy-name predictive-cpu-forecast \
  --policy-type PredictiveScaling \
  --predictive-scaling-configuration '{
    "MetricSpecifications": [{
      "TargetValue": 40.0,
      "PredefinedMetricPairSpecification": {
        "PredefinedMetricType": "ASGCPUUtilization",
        "ResourceLabel": ""
      }
    }],
    "Mode": "ForecastAndScale",
    "SchedulingBufferTime": 300,
    "MaxCapacityBreachBehavior": "IncreaseMaxCapacity",
    "MaxCapacityBuffer": 10
  }'
```

## 9-step procedure — Step 8c: Mixed Instances Policy (CLI)

```bash
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name <ASG> \
  --mixed-instances-policy '{
    "LaunchTemplate": {
      "LaunchTemplateSpecification": {
        "LaunchTemplateName": "my-template",
        "Version": "$Default"
      },
      "Overrides": [
        {"InstanceType": "m5.large"},
        {"InstanceType": "m5a.large"},
        {"InstanceType": "m4.large"}
      ]
    },
    "InstancesDistribution": {
      "OnDemandPercentageAboveBaseCapacity": 50,
      "SpotAllocationStrategy": "capacity-optimized",
      "SpotInstancePools": 3
    }
  }' \
  --min-size 2 --max-size 10 --desired-capacity 4 \
  --vpc-zone-identifier "subnet-abc,subnet-def,subnet-ghi"
```
