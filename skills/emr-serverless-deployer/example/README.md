# End-to-End Example: EMR Serverless Deployment

A walkthrough showing how to use the `emr-serverless-deployer` skill
from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are deploying a production EMR Serverless Spark application for
a nightly ETL pipeline. The application requires:

- Spark release emr-7.2.0
- IAM execution role scoped for S3, Glue, CloudWatch, Secrets Manager
- Pre-initialized capacity (50 warm workers)
- Maximum capacity (200 workers burst ceiling)
- VPC access for S3 via VPC endpoint
- S3 log bucket with lifecycle policy
- CloudWatch logging
- Spark AQE enabled with tuned configuration
- Job submission with PySpark entry point and arguments
- Auto-start enabled, auto-stop after 15 minutes idle

Application: `etl-spark-prod`
Region: `us-east-1`
Account: `123456789012`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-emr-serverless
```

Then paste the application requirements.

### Option B: Natural language

```
You: "Deploy a production EMR Serverless Spark application
      etl-spark-prod in us-east-1. Release emr-7.2.0. Execution
      role EMRServerlessExecRole with S3, Glue, CloudWatch,
      Secrets Manager. Pre-initialized capacity 50 workers at
      4 vCPU / 16 GB. Maximum capacity 200 workers. VPC subnets
      subnet-aaa, subnet-bbb with sg-emr-prod. S3 logs to
      s3://emr-logs-123456789012/etl-spark-prod/. CloudWatch
      /aws/emr-serverless/etl-spark-prod. Job entry point
      s3://etl-scripts/daily_transform.py with args --source
      s3://raw-data/events/ --target s3://curated/events/.
      AQE enabled, shuffle partitions 200, KryoSerializer.
      Auto-stop 15 min. Account: 123456789012."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "deploy emr serverless spark"
```

Output:

```
[Phase: Deploy | Skills routed: emr-serverless-deployer]

Primary route: emr-serverless-deployer (score: 18)
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
APPLICATION: etl-spark-prod
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓]      Application type — Spark, release label emr-7.2.0
  [✓]      Execution role — arn:aws:iam::123456789012:role/EMRServerlessExecRole (S3, Glue, CloudWatch, Secrets Manager scoped)
  [✓]      Pre-initialized capacity — 50 workers, 4 vCPU / 16 GB each
  [✓]      Maximum capacity — 200 workers (burst ceiling)
  [✓]      VPC access — subnets subnet-aaa, subnet-bbb, security groups sg-emr-prod
  [✓]      S3 log bucket — s3://emr-logs-123456789012/etl-spark-prod/
  [✓]      CloudWatch logging — enabled, log group /aws/emr-serverless/etl-spark-prod
  [✓]      Job submission — entry point s3://etl-scripts/daily_transform.py, args --source s3://raw-data/events/ --target s3://curated/events/ --date 2026-08-11
  [✓]      Configuration overrides — spark.sql.adaptive.enabled=true, spark.sql.shuffle.partitions=200, KryoSerializer
  [✓]      Tags — Environment=production, Application=etl-spark
VERIFICATION_COMMANDS:
  aws emr-serverless get-application --application-id <app-id>
  aws iam get-role --role-name EMRServerlessExecRole
  aws s3 ls s3://emr-logs-123456789012/etl-spark-prod/
  aws logs describe-log-groups --log-group-name-prefix /aws/emr-serverless/etl-spark-prod
```

---

## Step 3 — Deployment commands

The skill generates the CLI sequence (from
`references/cli-commands-and-iac.md`):

```bash
# Step 1: IAM execution role
aws iam create-role \
  --role-name EMRServerlessExecRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "emr-serverless.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

aws iam put-role-policy \
  --role-name EMRServerlessExecRole \
  --policy-name emr-serverless-exec \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {"Effect": "Allow", "Action": ["s3:GetObject", "s3:ListBucket"], "Resource": ["arn:aws:s3:::etl-scripts", "arn:aws:s3:::etl-scripts/*", "arn:aws:s3:::raw-data", "arn:aws:s3:::raw-data/*"]},
      {"Effect": "Allow", "Action": ["s3:PutObject"], "Resource": ["arn:aws:s3:::curated/*", "arn:aws:s3:::emr-logs-123456789012/*"]},
      {"Effect": "Allow", "Action": ["glue:GetTable", "glue:GetDatabase", "glue:GetPartitions"], "Resource": "*"},
      {"Effect": "Allow", "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"], "Resource": "arn:aws:logs:us-east-1:123456789012:log-group:/aws/emr-serverless/*"},
      {"Effect": "Allow", "Action": ["secretsmanager:GetSecretValue"], "Resource": "arn:aws:secretsmanager:us-east-1:123456789012:secret:etl/*"}
    ]
  }'

# Step 2: S3 log bucket
aws s3api create-bucket --bucket emr-logs-123456789012 --region us-east-1

# Step 3: Create the application
APP_ID=$(aws emr-serverless create-application \
  --name etl-spark-prod \
  --release-label emr-7.2.0 \
  --type SPARK \
  --initial-capacity '[{"workerType": {"cpu": "4 vCPU", "memory": "16 GB", "disk": "20 GB"}, "initialCount": 50}]' \
  --maximum-capacity '{"cpu": "800 vCPU", "memory": "3200 GB", "disk": "4000 GB"}' \
  --network-configuration '{"subnetIds": ["subnet-aaa", "subnet-bbb"], "securityGroupIds": ["sg-emr-prod"]}' \
  --auto-start-configuration '{"enabled": true}' \
  --auto-stop-configuration '{"enabled": true, "idleTimeoutMinutes": 15}' \
  --tags Environment=production,Application=etl-spark \
  --query 'applicationId' --output text)

# Step 4: Start the application
aws emr-serverless start-application --application-id "$APP_ID"

# Step 5: Submit the Spark job
aws emr-serverless start-job-run \
  --application-id "$APP_ID" \
  --execution-role-arn arn:aws:iam::123456789012:role/EMRServerlessExecRole \
  --job-driver '{
    "sparkSubmit": {
      "entryPoint": "s3://etl-scripts/daily_transform.py",
      "entryPointArguments": ["--source", "s3://raw-data/events/", "--target", "s3://curated/events/", "--date", "2026-08-11"],
      "sparkSubmitParameters": "--conf spark.sql.shuffle.partitions=200 --conf spark.sql.adaptive.enabled=true --conf spark.executor.memoryOverhead=2g"
    }
  }' \
  --configuration-overrides '{
    "monitoringConfiguration": {
      "s3MonitoringConfiguration": {"logUri": "s3://emr-logs-123456789012/etl-spark-prod/"},
      "cloudWatchLoggingConfiguration": {"enabled": true, "logGroupName": "/aws/emr-serverless/etl-spark-prod", "logStreamNamePrefix": "job"}
    },
    "applicationConfiguration": [
      {"classification": "spark-defaults", "properties": {"spark.sql.adaptive.enabled": "true", "spark.sql.shuffle.partitions": "200", "spark.serializer": "org.apache.spark.serializer.KryoSerializer"}}
    ]
  }' \
  --name daily-transform-2026-08-11
```

---

## Step 4 — Post-deployment verification

```bash
# Application status and config
aws emr-serverless get-application --application-id "$APP_ID"

# Job runs
aws emr-serverless list-job-runs --application-id "$APP_ID"

# Specific job status
aws emr-serverless get-job-run --application-id "$APP_ID" --job-run-id "<job-id>"

# Execution role
aws iam get-role --role-name EMRServerlessExecRole

# S3 logs
aws s3 ls s3://emr-logs-123456789012/etl-spark-prod/

# CloudWatch log groups
aws logs describe-log-groups --log-group-name-prefix /aws/emr-serverless/etl-spark-prod
```

---

## What the skill catches that a naive deployment misses

| Configuration | Naive deployment | Skill output | Why the skill is right |
|---|---|---|---|
| Execution role trust | `elasticmapreduce.amazonaws.com` | `emr-serverless.amazonaws.com` | Wrong trust principal causes AccessDeniedException on first S3 call. |
| Pre-initialized capacity | Not configured | 50 warm workers | Cold start (60-90s) is unacceptable for frequent queries. |
| VPC access | Often omitted | Subnets + security groups | Required for private S3 VPC endpoint enforcement and private resources. |
| CloudWatch logging | Not configured | Enabled with log group | Without it, job failures are invisible. |
| AQE | Disabled (default) | Enabled | AQE coalesces shuffle partitions dynamically. Always enable. |
| S3 log lifecycle | Never Expire | Glacier after 30d, expire 365d | Log storage costs balloon without lifecycle rules. |
| Auto-stop | Default 15 min | 15 min (batch) / 60 min (interactive) | Tuning auto-stop to the workload saves cost. |
| Execution role scoping | `AdministratorAccess` | Scoped S3/Glue/CloudWatch/Secrets | Broad role is a privilege escalation vector for arbitrary code. |

---

## Related artifacts

- **Skill definition:** `skills/emr-serverless-deployer/SKILL.md`
- **Deployment CLI commands:** `skills/emr-serverless-deployer/references/cli-commands-and-iac.md`
- **Execution and capacity guide:** `skills/emr-serverless-deployer/references/execution-and-capacity-guide.md`
- **Slash command:** `commands/aws/deploy-emr-serverless.md`
- **Eval suite:** `skills/emr-serverless-deployer/evals/evals.json`
- **Legacy test cases:** `skills/emr-serverless-deployer/eval/test-cases.yaml`
