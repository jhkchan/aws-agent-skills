# IAM, Logging, and Verification Procedures — FIS

Reference procedures for the FIS execution role, experiment logging
targets, and verification commands. Stored here so the main skill
body stays scannable.

## 1. FIS execution role — trust policy

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "fis.amazonaws.com"},
    "Action": "sts:AssumeRole",
    "Condition": {"StringEquals": {"sts:ExternalId": "<ACCOUNT_ID>"}}
  }]
}
```

The optional `ExternalId` condition prevents confused-deputy use of
the role from other accounts. Recommended when the role is assumable
across Organization member accounts.

## 2. FIS execution role — least-privilege permission policy

Pattern: scope each action's API by tag condition; grant
`cloudwatch:DescribeAlarms` only on the configured stop-condition
alarm ARNs; grant SSM only to the documents and instances used.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "FisEc2Actions",
      "Effect": "Allow",
      "Action": [
        "ec2:StopInstances",
        "ec2:StartInstances"
      ],
      "Resource": "arn:aws:ec2:<REGION>:<ACCOUNT_ID>:instance/*",
      "Condition": {
        "StringEquals": {"aws:ResourceTag/fis-target": "true"}
      }
    },
    {
      "Sid": "FisEc2Describe",
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeInstances",
        "ec2:DescribeInstanceStatus"
      ],
      "Resource": "*"
    },
    {
      "Sid": "FisEcsActions",
      "Effect": "Allow",
      "Action": [
        "ecs:StopTask",
        "ecs:DescribeTasks",
        "ecs:ListTasks"
      ],
      "Resource": "*"
    },
    {
      "Sid": "FisRdsFailover",
      "Effect": "Allow",
      "Action": [
        "rds:FailoverDBCluster",
        "rds:DescribeDBClusters"
      ],
      "Resource": "arn:aws:rds:<REGION>:<ACCOUNT_ID>:cluster:<CLUSTER_NAME>"
    },
    {
      "Sid": "FisSsmCommands",
      "Effect": "Allow",
      "Action": [
        "ssm:SendCommand",
        "ssm:GetCommandInvocation",
        "ssm:CancelCommand"
      ],
      "Resource": [
        "arn:aws:ssm:<REGION>::document/AWS-RunShellScript",
        "arn:aws:ec2:<REGION>:<ACCOUNT_ID>:instance/*"
      ]
    },
    {
      "Sid": "FisCloudWatchStopConditions",
      "Effect": "Allow",
      "Action": "cloudwatch:DescribeAlarms",
      "Resource": "arn:aws:cloudwatch:<REGION>:<ACCOUNT_ID>:alarm:fis-stop-*"
    },
    {
      "Sid": "FisLogging",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:<REGION>:<ACCOUNT_ID>:log-group:/aws/fis/*:*"
    }
  ]
}
```

## 3. S3 logging bucket policy

Grant the FIS service principal write access. The principal varies
slightly by region; the safest is the FIS logging account canonical
ID for the region (see the FIS user guide for the per-region ID list).
A simpler pattern uses the service principal directly:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "delivery.logs.amazonaws.com"},
    "Action": "s3:PutObject",
    "Resource": "arn:aws:s3:::fis-logs-<ACCOUNT_ID>/experiments/*",
    "Condition": {
      "StringEquals": {"s3:x-amz-acl": "bucket-owner-full-control"},
      "ArnLike": {"aws:SourceArn": "arn:aws:logs:<REGION>:<ACCOUNT_ID>:*"}
    }
  }]
}
```

## 4. CloudWatch Logs log group

```bash
aws logs create-log-group \
  --log-group-name /aws/fis/<EXPERIMENT_NAME> \
  --retention-in-days 30
```

The log group MUST exist before the experiment starts. FIS does not
create it. Without it, log delivery silently fails — the experiment
runs but no log streams are produced.

## 5. CloudWatch alarm for stop condition

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name fis-stop-error-rate \
  --metric-name ApplicationErrorRate \
  --namespace CWAgent \
  --statistic Average \
  --period 10 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --treat-missing-data notBreaching \
  --alarm-description "Halt FIS experiment if app error rate exceeds 5%"
```

Key fields:
- `--period 10` (10 seconds) and `--evaluation-periods 1` = sub-minute
  detection. FIS polls alarm state every few seconds; the alarm's
  period is the floor on detection latency.
- `--treat-missing-data notBreaching` = missing data does NOT trigger
  the alarm. Use `breaching` if you want the alarm to fire on data
  gaps (safer for FIS — fails closed).
- Confirm the alarm transitions OK -> ALARM under load before relying
  on it as a stop condition.

## 6. Create role + policy

```bash
# Trust policy
aws iam create-role \
  --role-name fis-execution-role \
  --assume-role-policy-document file://fis-trust-policy.json

# Inline permission policy
aws iam put-role-policy \
  --role-name fis-execution-role \
  --policy-name fis-execution-policy \
  --policy-document file://fis-permission-policy.json
```

## 7. Create experiment template

```bash
aws fis create-experiment-template \
  --description "<intent sentence>" \
  --role-arn arn:aws:iam::<ACCOUNT_ID>:role/fis-execution-role \
  --targets file://targets.json \
  --actions file://actions.json \
  --stop-conditions file://stop-conditions.json \
  --log-configuration file://log-config.json \
  --budget-duration PT5M
```

`actions.json` is a JSON object keyed by action name. `targets.json`
is a JSON object keyed by target id. `stop-conditions.json` is a JSON
array of `{source, value}` pairs.

## 8. Verify the template

```bash
aws fis get-experiment-template --id <TEMPLATE_ID>
```

Confirm every field is present. Pay attention to:
- `targets[*].resourceTags` — matches only eligible resources?
- `actions[*].roleArn` — present and least-privilege?
- `stopConditions[*].value` — alarm ARNs are well-formed?
- `logConfiguration` — both S3 and CloudWatch Logs configured?

## 9. Dry-run via start + immediate stop

```bash
EXP_ID=$(aws fis start-experiment \
  --experiment-template-id <TEMPLATE_ID> \
  --client-token $(date +%s) \
  --query 'experiment.id --output text)

sleep 15

aws fis stop-experiment --id $EXP_ID

aws fis get-experiment --id $EXP_ID \
  --query 'experiment.experimentTemplate'
```

A dry-run confirms IAM permissions, target resolution, and stop
condition evaluation without running the fault to its natural end.
Always dry-run in a non-production account first; the same template
ID can be re-deployed to production after verification.

## 10. Force-trigger the stop condition (validation)

```bash
# Set the alarm to ALARM manually by injecting a metric
aws cloudwatch set-alarm-state \
  --alarm-name fis-stop-error-rate \
  --state-value ALARM \
  --state-reason "Manual trigger for FIS stop-condition validation"

# Start a 60s experiment
EXP_ID=$(aws fis start-experiment \
  --experiment-template-id <TEMPLATE_ID> \
  --query 'experiment.id' --output text)

# Experiment should halt within 30-60s
aws fis get-experiment --id $EXP_ID --query 'experiment.state'

# Reset alarm
aws cloudwatch set-alarm-state \
  --alarm-name fis-stop-error-rate \
  --state-value OK \
  --state-reason "Reset after validation"
```

If the experiment runs to budget despite the alarm being ALARM, the
FIS role lacks `cloudwatch:DescribeAlarms` on the alarm ARN — the
silent stop-condition no-op. Fix the role policy and re-validate.

## 11. SSM rollback commands (network actions)

For network actions where the SSM agent may be offline at action end,
have the manual rollback commands staged:

```bash
# Remove tc qdisc (latency/loss/bandwidth)
tc qdisc del dev eth0 root

# Remove iptables rules (blackhole)
iptables -D INPUT -s <DB_IP> -j DROP

# Flush all (emergency)
iptables -F
```

Run via SSM Run Command on the target instance, or via Session
Manager if SSH is unavailable.

### Step 5 — Create IAM execution role with least privilege
**Trust policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "fis.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

**Permission policy (least privilege):**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["ec2:StopInstances", "ec2:StartInstances"],
      "Resource": "*",
      "Condition": {"StringEquals": {"aws:ResourceTag/fis-target": "true"}}
    },
    {
      "Effect": "Allow",
      "Action": ["cloudwatch:DescribeAlarms"],
      "Resource": "arn:aws:cloudwatch:<region>:<account>:alarm:<ALARM_NAME>"
    },
    {
      "Effect": "Allow",
      "Action": ["ssm:SendCommand", "ssm:GetCommandInvocation"],
      "Resource": ["arn:aws:ssm:<region>::document/AWS-RunShellScript",
                   "arn:aws:ec2:<region>:<account>:instance/*"]
    },
    {
      "Effect": "Allow",
      "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
      "Resource": "arn:aws:logs:<region>:<account>:log-group:/aws/fis/<exp>:*"
    }
  ]
}
```

**Common mistake:** granting `ec2:StopInstances` on `Resource: "*"`
without the tag condition. The condition is the second line of
defense — if the target filter is misconfigured, the IAM condition
still blocks the action on non-FIS resources.

### Step 6 — Configure experiment logging (S3 / CloudWatch Logs)
**S3 logging:**
```json
"logConfiguration": {
  "logSchemaVersion": 2,
  "cloudWatchLogsConfiguration": {"logGroupArn": "arn:aws:logs:<region>:<account>:log-group:/aws/fis/<exp>"},
  "s3Configuration": {"bucketName": "fis-experiment-logs-<account>", "prefix": "experiments/<exp>/"},
  "logsSchemaVersion": 2
}
```

The S3 bucket MUST grant `s3:PutObject` to the FIS service principal
(`service-role/fis.amazonaws.com` or the FIS logging account). The
CloudWatch log group MUST exist before the experiment starts.

**Common mistake:** referencing a log group that does not exist. FIS
does not create it; logging silently fails.
