# IAM Roles and Stop Conditions — FIS Template Deployer

Deep reference on FIS IAM role configuration (trust policy, permission
scoping via Condition on resource tags, per-action permission matrix,
network agent pass-role), stop conditions (CloudWatch alarm auto-abort
mechanics, alarm state transitions, recommended thresholds), and common
permission pitfalls. Loaded on demand by the skill — kept out of the
main SKILL.md body so the provisioning procedure stays scannable.

## FIS IAM role fundamentals

### Trust policy

The FIS service role must trust `fis.amazonaws.com` to assume it:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "fis.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

Without this trust policy, FIS cannot assume the role and the experiment
fails to start with an opaque "FIS could not assume the role" error.

### Permission scoping via Condition on resource tags

The safest FIS role scopes permissions to resources that have the
explicit opt-in tag (e.g., `FIS_Target=enabled`). This prevents FIS
from affecting resources that were not explicitly tagged for chaos
testing.

**Example: EC2 stop-instances scoped to tagged resources:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:StopInstances",
        "ec2:StartInstances",
        "ec2:DescribeInstances"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:ResourceTag/FIS_Target": "enabled"
        }
      }
    }
  ]
}
```

**Why this matters:** without the `Condition` block, the role can stop
ANY EC2 instance in the account (over-permissive). If a target filter
is misconfigured, FIS could stop production instances. The `Condition`
ensures FIS can only act on resources that are explicitly tagged.

### Per-action permission matrix

| Action | Required IAM permissions |
|---|---|
| `aws:ec2:stop-instances` | `ec2:StopInstances`, `ec2:StartInstances`, `ec2:DescribeInstances` |
| `aws:ec2:terminate-instances` | `ec2:TerminateInstances`, `ec2:DescribeInstances` |
| `aws:ecs:drain-container-instances` | `ecs:ListContainerInstances`, `ecs:UpdateContainerInstancesState`, `ecs:DescribeContainerInstances` |
| `aws:lambda:invoke` | `lambda:InvokeFunction` |
| `aws:network:disrupt-connectivity` | `ec2:CreateNetworkInterface`, `ec2:DeleteNetworkInterface`, `ec2:DescribeNetworkInterfaces`, `ec2:CreateNetworkInterfacePermission`, `iam:PassRole` |
| `aws:rds:failover-db-cluster` | `rds:FailoverDBCluster`, `rds:DescribeDBClusters` |
| `aws:s3:pause-bucket-access` | `s3:PutBucketAcl` (or equivalent bucket-modification permission) |
| `aws:cloudwatch:put-metric-data` | `cloudwatch:PutMetricData` |

### Network agent IAM pass-role

The `aws:network:disrupt-connectivity` action requires the FIS network
agent — a network interface injected into the target VPC. The FIS role
must have `iam:PassRole` permission to pass the network agent role:

```json
{
  "Effect": "Allow",
  "Action": "iam:PassRole",
  "Resource": "arn:aws:iam::123456789012:role/FISNetworkAgentRole"
}
```

The network agent role itself must have a trust policy allowing the FIS
service role to assume it, plus EC2 network interface permissions.

### Common permission pitfalls

1. **Missing trust policy.** The role does not trust
   `fis.amazonaws.com`. FIS cannot assume the role. Fix: add the trust
   policy shown above.

2. **Over-permissive role.** The role grants `ec2:*` on `*`. This
   violates least privilege. Fix: scope permissions via `Condition` on
   resource tags.

3. **Missing action-specific permission.** The role has
   `ec2:DescribeInstances` but not `ec2:StopInstances`. The experiment
   fails at start. Fix: add the missing permission per the matrix
   above.

4. **IAM propagation delay.** The role was just created or its policy
   was just updated. IAM changes can take up to 30 seconds to propagate.
   Wait before starting the experiment.

5. **Missing `iam:PassRole` for network actions.** The
   `aws:network:disrupt-connectivity` action fails because the FIS role
   cannot pass the network agent role. Fix: add `iam:PassRole` for the
   network agent role ARN.

## Stop conditions deep dive

### How stop conditions work

A stop condition is a CloudWatch alarm that, when it transitions to
ALARM state during the experiment, triggers FIS to:

1. Immediately abort all running actions.
2. Roll back each action (e.g., restart stopped instances, restore
   bucket access, remove the network agent).
3. Set the experiment state to `aborted`.
4. Record which alarm fired and when in the experiment report.

**Critical:** stop conditions trigger ONLY when the alarm transitions
to ALARM state. If the alarm is already in ALARM state before the
experiment starts, it does NOT trigger a stop. If the alarm never
transitions to ALARM during the experiment, the experiment runs to
completion.

### Stop condition structure

```json
"stopConditions": [
  {
    "source": "aws:cloudwatch:alarm",
    "value": "arn:aws:cloudwatch:us-east-1:123456789012:alarm:FIS-CPU-High"
  }
]
```

The `source` field identifies the type of stop condition (currently
only `aws:cloudwatch:alarm` is supported). The `value` field is the
CloudWatch alarm ARN.

### Recommended stop condition alarms

Choose alarms that represent "the system is degraded beyond acceptable
limits." Common choices:

| Alarm type | Metric example | Threshold example |
|---|---|---|
| CPU utilization | `CPUUtilization` (AWS/EC2) | `> 90%` for 1 minute |
| Error rate | `5xxErrorRate` (Application ELB) | `> 5%` for 1 minute |
| Latency | `TargetResponseTime` (Application ELB) | `> 2000ms` for 1 minute |
| Health check | `HealthyHostCount` (Application ELB) | `< 1` for 1 minute |
| Database lag | `AuroraReplicaLag` (AWS/RDS) | `> 5000ms` for 1 minute |
| Queue depth | `ApproximateNumberOfMessagesVisible` (AWS/SQS) | `> 10000` for 5 minutes |

### Creating the alarm before the template

The CloudWatch alarm MUST exist before the experiment template is
created. Template creation fails with `ResourceNotFoundException` if
the alarm ARN does not exist.

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "FIS-CPU-High" \
  --metric-name "CPUUtilization" \
  --namespace "AWS/EC2" \
  --statistic "Average" \
  --period 60 \
  --threshold 90.0 \
  --comparison-operator "GreaterThanThreshold" \
  --dimensions "Name=AutoScalingGroupName,Value=my-asg" \
  --evaluation-periods 1 \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:fis-alerts" \
  --region us-east-1
```

### Verifying the alarm exists

```bash
aws cloudwatch describe-alarms \
  --alarm-names "FIS-CPU-High" \
  --region us-east-1 \
  --query 'MetricAlarms[0].{Name:AlarmName,ARN:AlarmArn,State:StateValue}'
```

### Multiple stop conditions

You can specify multiple stop conditions. FIS aborts the experiment if
ANY of them fires:

```json
"stopConditions": [
  {
    "source": "aws:cloudwatch:alarm",
    "value": "arn:aws:cloudwatch:us-east-1:123456789012:alarm:FIS-CPU-High"
  },
  {
    "source": "aws:cloudwatch:alarm",
    "value": "arn:aws:cloudwatch:us-east-1:123456789012:alarm:FIS-Error-Rate-High"
  },
  {
    "source": "aws:cloudwatch:alarm",
    "value": "arn:aws:cloudwatch:us-east-1:123456789012:alarm:FIS-Latency-High"
  }
]
```

## Terraform examples

### FIS experiment template (Terraform)

```hcl
resource "aws_fis_experiment_template" "stop_instance" {
  description = "Stop 1 EC2 instance for 5 minutes to test HA"
  role_arn    = aws_iam_role.fis_experiment.arn

  action {
    name       = "stop-instance"
    action_id  = "aws:ec2:stop-instances"
    parameter {
      key   = "startAfter"
      value = "5m"
    }
    target {
      key   = "Instances"
      value = "target-instances"
    }
  }

  target {
    name           = "target-instances"
    resource_type  = "aws:ec2:instance"
    selection_mode = "COUNT(1)"

    resource_tag {
      key   = "FIS_Target"
      value = "enabled"
    }
    resource_tag {
      key   = "Environment"
      value = "staging"
    }
  }

  stop_condition {
    source = "aws:cloudwatch:alarm"
    value  = aws_cloudwatch_metric_alarm.fis_cpu_high.arn
  }

  log_configuration {
    log_schema_version = 1
    cloudwatch_logs_log_group {
      log_group = aws_cloudwatch_log_group.fis_logs.name
    }
  }

  tags = {
    Environment     = "staging"
    ExperimentType  = "HA-Test"
  }
}
```

### FIS IAM role (Terraform)

```hcl
resource "aws_iam_role" "fis_experiment" {
  name = "FISExperimentRole"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "fis.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "fis_permissions" {
  name = "FISExperimentPermissions"
  role = aws_iam_role.fis_experiment.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ec2:StopInstances",
          "ec2:StartInstances",
          "ec2:DescribeInstances"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "aws:ResourceTag/FIS_Target" = "enabled"
          }
        }
      },
      {
        Effect = "Allow"
        Action = ["cloudwatch:DescribeAlarms"]
        Resource = "*"
      }
    ]
  })
}
```

### CloudWatch alarm (Terraform)

```hcl
resource "aws_cloudwatch_metric_alarm" "fis_cpu_high" {
  alarm_name          = "FIS-CPU-High"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  statistic           = "Average"
  period              = 60
  threshold           = 90.0
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.app.name
  }

  alarm_actions = [aws_sns_topic.fis_alerts.arn]
}
```
