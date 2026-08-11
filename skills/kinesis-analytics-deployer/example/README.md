# End-to-End Example: Kinesis Data Analytics Deployment

A walkthrough showing how to use the `kinesis-analytics-deployer` skill
from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are deploying a production Managed Service for Apache Flink
application for real-time fraud detection. The application requires:

- Flink runtime FLINK-1_19
- IAM service execution role scoped for Kinesis read, Kinesis write,
  S3 code retrieval, and CloudWatch logging
- Source: Kinesis Data Stream transactions (4 shards, starting LATEST)
- Destination: Kinesis Data Stream alerts
- Checkpointing at 60-second intervals for stateful recovery
- Parallelism 4 (matching the 4-shard source stream)
- Application snapshots enabled
- CloudWatch logging
- Application code pinned to a versioned S3 key

Application: `fraud-detection-flink`
Region: `us-east-1`
Account: `123456789012`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-kinesis-analytics
```

Then paste the application requirements.

### Option B: Natural language

```
You: "Deploy a production Kinesis Data Analytics Flink application
      fraud-detection-flink in us-east-1. Runtime FLINK-1_19.
      Execution role KDAExecutionRole with Kinesis GetRecords on
      transactions, Kinesis PutRecord on alerts, S3 GetObject on
      s3://kda-apps/fraud-detection-1.0.0.jar, CloudWatch Logs.
      Source: Kinesis Data Stream transactions, 4 shards, ACTIVE,
      starting LATEST. Destination: Kinesis Data Stream alerts.
      Checkpointing 60000 ms, min pause 5000 ms. Parallelism 4,
      parallelismPerKPU 1. Snapshots enabled. Log group
      /aws/kinesis-analytics/fraud-detection-flink. Account:
      123456789012."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "deploy kinesis data analytics flink"
```

Output:

```
[Phase: Deploy | Skills routed: kinesis-analytics-deployer]

Primary route: kinesis-analytics-deployer (score: 18)
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
APPLICATION: fraud-detection-flink
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓]      Runtime environment — FLINK-1_19, application mode STREAMING
  [✓]      Service execution role — arn:aws:iam::123456789012:role/KDAExecutionRole (Kinesis read, Kinesis write, S3 code, CloudWatch Logs)
  [✓]      Source — Kinesis Data Stream arn:aws:kinesis:us-east-1:123456789012:stream/transactions, starting position LATEST
  [✓]      Destination — Kinesis Data Stream arn:aws:kinesis:us-east-1:123456789012:stream/alerts
  [✓]      Application code — s3://kda-apps/fraud-detection-1.0.0.jar (pinned version)
  [✓]      Checkpointing — interval 60000 ms, min pause 5000 ms, configuration CUSTOM
  [✓]      Parallelism — 4 (parallelismPerKPU 1, 5 KPUs total)
  [✓]      CloudWatch logging — enabled, log group /aws/kinesis-analytics/fraud-detection-flink
  [✓]      Application snapshots — enabled for stateful recovery
  [✓]      Tags — Environment=production, Application=fraud-detection
VERIFICATION_COMMANDS:
  aws kinesisanalyticsv2 describe-application --application-name fraud-detection-flink
  aws iam get-role --role-name KDAExecutionRole
  aws kinesis describe-stream --stream-name transactions
  aws logs describe-log-groups --log-group-name-prefix /aws/kinesis-analytics/fraud-detection-flink
```

---

## Step 3 — Deployment commands

The skill generates the CLI sequence (from
`references/cli-commands-and-iac.md`):

```bash
# Step 1: IAM service execution role
aws iam create-role \
  --role-name KDAExecutionRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "kinesisanalytics.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

aws iam put-role-policy \
  --role-name KDAExecutionRole \
  --policy-name kda-exec \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {"Effect": "Allow", "Action": ["kinesis:GetRecords", "kinesis:GetShardIterator", "kinesis:DescribeStreamSummary", "kinesis:ListShards"], "Resource": "arn:aws:kinesis:us-east-1:123456789012:stream/transactions"},
      {"Effect": "Allow", "Action": ["kinesis:PutRecord", "kinesis:PutRecords"], "Resource": "arn:aws:kinesis:us-east-1:123456789012:stream/alerts"},
      {"Effect": "Allow", "Action": ["s3:GetObject"], "Resource": "arn:aws:s3:::kda-apps/fraud-detection-1.0.0.jar"},
      {"Effect": "Allow", "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents", "logs:DescribeLogGroups"], "Resource": "arn:aws:logs:us-east-1:123456789012:log-group:/aws/kinesis-analytics/*"}
    ]
  }'

# Step 2: Confirm source stream
aws kinesis describe-stream --stream-name transactions --query 'StreamDescription.StreamStatus'
# Should return ACTIVE

# Step 3: Create the application
aws kinesisanalyticsv2 create-application \
  --application-name fraud-detection-flink \
  --runtime-environment FLINK-1_19 \
  --service-execution-role arn:aws:iam::123456789012:role/KDAExecutionRole \
  --application-configuration '{
    "ApplicationCodeConfiguration": {
      "CodeContent": {
        "S3ContentLocation": {"BucketARN": "arn:aws:s3:::kda-apps", "FileKey": "fraud-detection-1.0.0.jar"},
        "CodeContentType": "ZIPFILE"
      },
      "CodeContentType": "ZIPFILE"
    },
    "FlinkApplicationConfiguration": {
      "CheckpointConfiguration": {"ConfigurationType": "CUSTOM", "CheckpointingEnabled": true, "CheckpointInterval": 60000, "MinPauseBetweenCheckpoints": 5000},
      "ParallelismConfiguration": {"ConfigurationType": "CUSTOM", "Parallelism": 4, "ParallelismPerKPU": 1},
      "MonitoringConfiguration": {"ConfigurationType": "CUSTOM", "MetricsLevel": "APPLICATION", "LogLevel": "INFO"}
    },
    "ApplicationSnapshotConfiguration": {"SnapshotsEnabled": true}
  }' \
  --tags Environment=production,Application=fraud-detection

# Step 4: Start the application
aws kinesisanalyticsv2 start-application \
  --application-name fraud-detection-flink \
  --run-configuration '{"FlinkRunConfiguration": {"AllowNonRestoredState": false}}'
```

---

## Step 4 — Post-deployment verification

```bash
# Application status and config
aws kinesisanalyticsv2 describe-application --application-name fraud-detection-flink

# Application status only
aws kinesisanalyticsv2 describe-application --application-name fraud-detection-flink \
  --query 'ApplicationDetail.ApplicationStatus'
# Should return 'RUNNING'

# Execution role
aws iam get-role --role-name KDAExecutionRole

# Source stream
aws kinesis describe-stream --stream-name transactions

# CloudWatch log groups
aws logs describe-log-groups --log-group-name-prefix /aws/kinesis-analytics/fraud-detection-flink

# Application snapshots
aws kinesisanalyticsv2 list-application-snapshots --application-name fraud-detection-flink
```

---

## What the skill catches that a naive deployment misses

| Configuration | Naive deployment | Skill output | Why the skill is right |
|---|---|---|---|
| Execution role trust | Often omitted or wrong principal | `kinesisanalytics.amazonaws.com` | Wrong trust principal causes AccessDeniedException on first GetRecords call. |
| Parallelism | 1 (default) | 4 (matching 4 source shards) | Sub-parallelism wastes KPUs; mismatched parallelism underutilizes shards. |
| Checkpointing | DEFAULT (disabled or wrong interval) | CUSTOM, 60s interval, 5s pause | Without checkpointing, failure means full state loss and replay. |
| Application code | `fraud-detection-latest.jar` | `fraud-detection-1.0.0.jar` (pinned) | Unversioned keys change silently on new push. Reproducibility breaker. |
| CloudWatch logging | Not configured | Enabled with log group | Without it, application failures are invisible. |
| Application snapshots | Not enabled | Enabled for stateful recovery | Snapshots are the ONLY recovery mechanism for planned code updates. |
| Execution role scoping | `AdministratorAccess` | Scoped Kinesis/S3/CloudWatch | Broad role is a privilege escalation vector for arbitrary streaming code. |
| Source stream check | Not verified | describe-stream confirms ACTIVE | Silent failure if source stream does not exist or is CREATING. |

---

## Related artifacts

- **Skill definition:** `skills/kinesis-analytics-deployer/SKILL.md`
- **Deployment CLI commands:** `skills/kinesis-analytics-deployer/references/cli-commands-and-iac.md`
- **Execution and capacity guide:** `skills/kinesis-analytics-deployer/references/execution-and-capacity-guide.md`
- **Slash command:** `commands/aws/deploy-kinesis-analytics.md`
- **Eval suite:** `skills/kinesis-analytics-deployer/evals/evals.json`
- **Legacy test cases:** `skills/kinesis-analytics-deployer/eval/test-cases.yaml`
