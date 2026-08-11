---
name: emr-serverless-deployer
description: 'Deploys Amazon EMR Serverless applications with production-grade configuration: application creation (release label, type: Spark or Hive), capacity configuration (pre-initialized capacity for warm starts, maximum capacity for burst limits), VPC access (subnets, security groups for private resources), IAM execution role (S3, Glue, CloudWatch scoped), job submission (entry point, arguments, configuration overrides), interactive endpoints (Spark Connect, Jupyter), and latest features (Spark Connect remote sessions, interactive endpoints for notebooks, automated start/stop, Lake Formation integration, gang scheduling). Emits a READY_TO_DEPLOY checklist with every configuration item verified. Use when creating an EMR Serverless application, deploying a Spark or Hive job, validating a configuration, or generating deployment CLI and IaC templates. Triggers: EMR Serverless, serverless Spark, serverless Hive, pre-initialized capacity, Spark Connect, interactive endpoints, job submission.'
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: 'Requires an LLM agent runtime (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with emr-serverless, s3, iam, ec2, logs, and glue access. Works with Terraform aws_emrserverless_* resources, CloudFormation AWS::EMRServerless::* resources, and the AWS Console EMR Serverless wizard.'
keywords:
- aws
- emr
- emr-serverless
- cloudops
- deploy
- provisioning
- analytics
- spark
- hive
- pre-initialized-capacity
- spark-connect
- interactive-endpoints
- job-submission
- execution-role
- vpc-access
tags:
- aws
- emr
- emr-serverless
- cloudops
- deploy
- analytics
- spark
- hive
dependencies:
- aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: Analytics
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags:
  - aws
  - emr
  - emr-serverless
  - cloudops
  - deploy
  - analytics
  - spark
  - hive
  dependencies:
  - aws-orchestrator
  keywords:
  - create emr serverless
  - deploy emr serverless
  - emr serverless spark application
  - emr serverless hive application
  - emr serverless pre-initialized capacity
  - emr serverless execution role
  - emr serverless job submission
  - emr serverless vpc access
  - emr serverless spark connect
  - emr serverless interactive endpoints
  when_to_use: Invoke when the user wants to create a new EMR Serverless application, deploy a serverless Spark or Hive workload, validate an existing EMR Serverless configuration against best practices, generate deployment CLI commands or IaC templates, or troubleshoot an EMR Serverless deployment failure caused by missing prerequisites (execution role, VPC subnets, S3 log bucket). Do NOT invoke for provisioned EMR clusters (use emr-cluster-deployer), Glue jobs (use glue-job-troubleshooter), or Athena (use athena-query-optimizer).
---

# EMR Serverless Deployer

An AWS CloudOps agent skill that deploys Amazon EMR Serverless
applications with correct production defaults. Emits a
READY_TO_DEPLOY checklist verifying every configuration item.

## Quick navigation

| Need | Section |
|---|---|
| What MUST be in the response | "STRICT output contract" |
| Why application-before-job order matters | "Reasoning framework" |
| What to verify before deploying | "Prerequisites" |
| The ordered deployment steps | "Deployment procedure" |
| Common silent-failure pitfalls | "NEVER" |
| Application-type decision matrix | "Workload matrix" |
| 2024-2026 feature changes | "Recent AWS features" |
| Deep CLI sequences | `references/cli-commands-and-iac.md` |
| Execution roles, VPC, capacity, full NEVER | `references/execution-and-capacity-guide.md` |

## STRICT output contract

When this skill is invoked with an EMR Serverless deployment request,
the agent MUST respond with the READY_TO_DEPLOY checklist defined in
"Output format" using the literal all-caps labels `APPLICATION:`,
`VERDICT:`, `CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface
the checklist with prose, headings, or disclaimers — emit the block
as the first lines.

### Required output structure

1. `APPLICATION: <application-name>` — the EMR Serverless application
   being deployed.
2. `VERDICT: READY_TO_DEPLOY` OR `VERDICT: PREREQUISITES_MISSING`.
3. `CHECKLIST:` followed by indented lines with status markers
   (`[✓]`, `[✗]`, `[OPTIONAL]`, `[INPUT NEEDED]`).
4. `VERIFICATION_COMMANDS:` followed by indented
   `aws emr-serverless ...` commands.

### FORBIDDEN output patterns

- **No prose preamble before `APPLICATION:`** — first non-empty line
  MUST be `APPLICATION:`.
- **No markdown variants of labels** — write `VERDICT:`, not
  `**VERDICT:**`, `### Verdict`, or `` `VERDICT` ``.
- **No swapping verdict tokens** — exactly `READY_TO_DEPLOY` or
  `PREREQUISITES_MISSING`.
- **No omitting `VERIFICATION_COMMANDS:`** — include even when
  PREREQUISITES_MISSING.
- **No extra sections after `VERIFICATION_COMMANDS:`** — the
  checklist block is the entire response.
- **No status marker drift** — use only `[✓]`, `[✗]`, `[OPTIONAL]`,
  `[INPUT NEEDED]`.

### Perfect example (copy the shape exactly)

```text
APPLICATION: etl-spark-prod
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓]      Application type — Spark, release label emr-7.2.0
  [✓]      Execution role — arn:aws:iam::123456789012:role/EMRServerlessExecRole (S3, Glue, CloudWatch, Secrets Manager scoped)
  [✓]      Pre-initialized capacity — 50 workers, 4 vCPU / 16 GB each, Spark driver 2 vCPU / 8 GB
  [✓]      Maximum capacity — 200 workers (burst ceiling)
  [✓]      VPC access — subnets subnet-aaa, subnet-bbb, security groups sg-emr-prod
  [✓]      S3 log bucket — s3://emr-logs-123456789012/etl-spark-prod/
  [✓]      CloudWatch logging — enabled, log group /aws/emr-serverless/etl-spark-prod
  [✓]      Job submission — entry point s3://etl-scripts/daily_transform.py, args --source s3://raw-data/ --target s3://curated/
  [✓]      Configuration overrides — spark.sql.shuffle.partitions=200, spark.executor.memoryOverhead=2g
  [✓]      Tags — Environment=production, Application=etl-spark
  [OPTIONAL] Interactive endpoint — Spark Connect for notebooks (not configured)
VERIFICATION_COMMANDS:
  aws emr-serverless get-application --application-id <app-id>
  aws iam get-role --role-name EMRServerlessExecRole
  aws s3 ls s3://emr-logs-123456789012/etl-spark-prod/
  aws logs describe-log-groups --log-group-name-prefix /aws/emr-serverless/etl-spark-prod
```

## Reasoning framework (why the application-before-job order matters)

1. **Application FIRST** — an EMR Serverless application is the
   container for all Spark/Hive jobs. It defines the release label,
   type, execution role, capacity, and VPC access. Without an
   application you cannot submit a job.
2. **Execution role** — the IAM role the application assumes at
   runtime for S3 reads/writes, Glue catalog access, CloudWatch
   logging, and Secrets Manager. Without it, the job fails with
   `AccessDeniedException` on the first S3 operation.
3. **Capacity configuration** — pre-initialized capacity keeps workers
   warm for immediate job start (no cold start). Maximum capacity is
   the burst ceiling — jobs that exceed it are queued or fail.
4. **VPC access (if private resources)** — if the job reads from RDS,
   Redshift (private), or internal APIs, VPC subnets and security
   groups are REQUIRED. Without them, the job cannot reach private
   resources.
5. **S3 log bucket** — EMR Serverless streams stdout/stderr and Spark
   event logs to S3. Without a log bucket, job failures are invisible.
6. **Job submission LAST** — the entry point (S3 path to the
   PySpark/Scala/Hive script), arguments, and configuration overrides
   are submitted AFTER the application is CREATED and STARTED.

## Prerequisites (verify before deployment)

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| **IAM execution role** | Trust `emr-serverless.amazonaws.com`. Scope for S3/Glue/CloudWatch/Secrets Manager. NEVER `AdministratorAccess`. | `aws iam get-role --role-name <role>` |
| **S3 log bucket** | Stores stdout/stderr and Spark event logs. MUST exist before job submission. | `aws s3 ls s3://<bucket>/` |
| **S3 script bucket** | Stores the entry-point PySpark/Scala/Hive script. MUST exist with the script. | `aws s3 ls s3://<scripts>/<script>` |
| **VPC subnets (if private resources)** | At least 2 private subnets across AZs for HA. Required if job accesses RDS/Redshift/internal APIs. | `aws ec2 describe-subnets --subnet-ids <ids>` |
| **Security groups (if VPC access)** | Inbound from EMR Serverless ENIs. Outbound to S3/Glue VPC endpoints. | `aws ec2 describe-security-groups --group-ids <sg-ids>` |
| **Release label** | EMR release version (e.g., `emr-7.2.0`). Determines Spark/Hive versions. Use the latest stable. | `aws emr-serverless list-release-labels` |
| **Service quota** | Default capacity (RPUs) per Region per account. Request increase BEFORE production. | `aws service-quotas get-service-quota --service-code emr-serverless --quota-code L-XXXXXXXX` |
| **Glue database (if catalog integration)** | Source/target Glue database and tables MUST exist for catalog-mode jobs. | `aws glue get-database --name <db>` |
| **Application release label compatibility** | Spark/Hive version in the release label MUST match the job's compiled dependencies. | Check EMR release notes for the release label. |

## Deployment procedure (apply in order)

### Step 1: IAM execution role

The execution role is assumed by the EMR Serverless application for
all runtime AWS API calls (S3 reads/writes, Glue catalog access,
CloudWatch logging, Secrets Manager). Without it, the job fails on
the first S3 operation.

```bash
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
      {
        "Effect": "Allow",
        "Action": ["s3:GetObject", "s3:ListBucket"],
        "Resource": ["arn:aws:s3:::etl-scripts", "arn:aws:s3:::etl-scripts/*", "arn:aws:s3:::raw-data", "arn:aws:s3:::raw-data/*"]
      },
      {
        "Effect": "Allow",
        "Action": ["s3:PutObject"],
        "Resource": ["arn:aws:s3:::curated/*", "arn:aws:s3:::emr-logs-123456789012/*"]
      },
      {
        "Effect": "Allow",
        "Action": ["glue:GetTable", "glue:GetDatabase", "glue:GetPartitions", "glue:CreateTable", "glue:UpdateTable"],
        "Resource": "*"
      },
      {
        "Effect": "Allow",
        "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
        "Resource": "arn:aws:logs:<region>:<account-id>:log-group:/aws/emr-serverless/*"
      },
      {
        "Effect": "Allow",
        "Action": ["secretsmanager:GetSecretValue"],
        "Resource": "arn:aws:secretsmanager:<region>:<account-id>:secret:etl/*"
      }
    ]
  }'
```

Rules:
- **Trust `emr-serverless.amazonaws.com`** — NOT `elasticmapreduce.amazonaws.com`
  (that is the provisioned EMR principal).
- **NEVER use `AdministratorAccess`** — scope the role to the specific
  S3 buckets, Glue databases, and Secrets Manager secrets the job needs.
- **CloudWatch Logs permissions** — required for structured logging.

### Step 2: S3 log bucket

```bash
aws s3api create-bucket \
  --bucket emr-logs-123456789012 \
  --region us-east-1

# Block public access (recommended)
aws s3api put-public-access-block \
  --bucket emr-logs-123456789012 \
  --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

# Lifecycle rule to transition logs to Glacier after 30 days
aws s3api put-bucket-lifecycle-configuration \
  --bucket emr-logs-123456789012 \
  --lifecycle-configuration '{
    "Rules": [{
      "ID": "log-archive",
      "Status": "Enabled",
      "Filter": {"Prefix": ""},
      "Transitions": [{"Days": 30, "StorageClass": "GLACIER"}],
      "Expiration": {"Days": 365}
    }]
  }'
```

### Step 3: Create the application

```bash
aws emr-serverless create-application \
  --name etl-spark-prod \
  --release-label emr-7.2.0 \
  --type SPARK \
  --initial-capacity '[
    {
      "workerType": {
        "cpu": "4 vCPU",
        "memory": "16 GB",
        "disk": "20 GB"
      },
      "initialCount": 50,
      "workerTypeConfiguration": {
        "driver": {"cpu": "2 vCPU", "memory": "8 GB"},
        "executor": {"cpu": "4 vCPU", "memory": "16 GB"}
      }
    }
  ]' \
  --maximum-capacity '{
    "cpu": "800 vCPU",
    "memory": "3200 GB",
    "disk": "4000 GB"
  }' \
  --network-configuration '{
    "subnetIds": ["subnet-aaa", "subnet-bbb"],
    "securityGroupIds": ["sg-emr-prod"]
  }' \
  --auto-start-configuration '{"enabled": true}' \
  --auto-stop-configuration '{"enabled": true, "idleTimeoutMinutes": 15}' \
  --image-configuration '{
    "imageUri": "123456789012.dkr.ecr.us-east-1.amazonaws.com/emr-serverless:7.2.0-custom"
  }' \
  --tags Environment=production,Application=etl-spark
```

Parameters:
- **release-label** — the EMR release version (e.g., `emr-7.2.0`).
  Determines the Spark and Hive versions. Use the latest stable unless
  compatibility requires otherwise.
- **type** — `SPARK` or `HIVE`. Spark for ETL/ML; Hive for
  schema-on-read and legacy HiveQL pipelines.
- **initial-capacity** — pre-initialized workers kept warm for
  immediate job start. Eliminates cold-start latency (60-90s).
- **maximum-capacity** — the burst ceiling. Jobs that need more
  workers are queued (if auto-scaling) or fail.
- **network-configuration** — VPC subnets and security groups. Required
  if the job accesses private resources (RDS, Redshift private,
  internal APIs).
- **auto-start** — application starts automatically when a job is
  submitted. Recommended for production.
- **auto-stop** — application stops after `idleTimeoutMinutes` of no
  activity. Saves cost. Default 15 minutes.
- **image-configuration** — custom Docker image from ECR for
  additional libraries (pandas, scikit-learn, custom JARs). Optional.

### Step 4: Start the application

```bash
APP_ID=$(aws emr-serverless create-application ... --query 'applicationId' --output text)

aws emr-serverless start-application --application-id "$APP_ID"
```

Wait for the application to reach `STARTED` state:

```bash
aws emr-serverless get-application --application-id "$APP_ID" \
  --query 'application.state' --output text
# Should return 'STARTED'
```

### Step 5: Configure pre-initialized capacity (warm workers)

Pre-initialized capacity keeps workers warm so the first job starts
immediately (no 60-90s cold start). This is the ONLY way to get
sub-minute job start latency.

```bash
aws emr-serverless update-application \
  --application-id "$APP_ID" \
  --initial-capacity '[
    {
      "workerType": {
        "cpu": "4 vCPU",
        "memory": "16 GB",
        "disk": "20 GB"
      },
      "initialCount": 50
    }
  ]'
```

Rules:
- **Pre-initialized capacity is billed even when idle.** Set
  `initialCount` based on the minimum sustained workload.
- **Pair with auto-stop** — if auto-stop triggers (idle for 15 min),
  pre-initialized capacity is released. When a new job starts, the
  application re-starts and re-initializes workers (cold start).
- **NEVER set `initialCount` higher than needed.** Each warm worker
  is billed at the hourly rate whether or not it runs a job.

### Step 6: Job submission (Spark)

```bash
aws emr-serverless start-job-run \
  --application-id "$APP_ID" \
  --execution-role-arn arn:aws:iam::123456789012:role/EMRServerlessExecRole \
  --job-driver '{
    "sparkSubmit": {
      "entryPoint": "s3://etl-scripts/daily_transform.py",
      "entryPointArguments": [
        "--source", "s3://raw-data/events/",
        "--target", "s3://curated/events/",
        "--date", "2026-08-11"
      ],
      "sparkSubmitParameters": "--conf spark.sql.shuffle.partitions=200 --conf spark.executor.memoryOverhead=2g --conf spark.sql.adaptive.enabled=true"
    }
  }' \
  --configuration-overrides '{
    "monitoringConfiguration": {
      "s3MonitoringConfiguration": {
        "logUri": "s3://emr-logs-123456789012/etl-spark-prod/"
      },
      "managedPersistentAppUI": "ENABLED",
      "cloudWatchLoggingConfiguration": {
        "enabled": true,
        "logGroupName": "/aws/emr-serverless/etl-spark-prod",
        "logStreamNamePrefix": "job"
      }
    },
    "applicationConfiguration": [
      {
        "classification": "spark-defaults",
        "properties": {
          "spark.sql.shuffle.partitions": "200",
          "spark.sql.adaptive.enabled": "true",
          "spark.sql.adaptive.coalescePartitions.enabled": "true",
          "spark.executor.memoryOverhead": "2g"
        }
      }
    ]
  }' \
  --name daily-transform-2026-08-11 \
  --tags Environment=production,Pipeline=daily-transform
```

### Step 7: Job submission (Hive)

```bash
aws emr-serverless start-job-run \
  --application-id "$APP_ID" \
  --execution-role-arn arn:aws:iam::123456789012:role/EMRServerlessExecRole \
  --job-driver '{
    "hive": {
      "query": "SELECT COUNT(*) FROM sales WHERE dt = '\''2026-08-11'\''",
      "initScriptFileS3Path": "s3://etl-scripts/hive-init.sql",
      "parameters": "--hiveconf hive.execution.engine=tez --hiveconf tez.grouping.min-size=268435456"
    }
  }' \
  --configuration-overrides '{
    "monitoringConfiguration": {
      "s3MonitoringConfiguration": {"logUri": "s3://emr-logs-123456789012/hive-app/"},
      "cloudWatchLoggingConfiguration": {"enabled": true}
    }
  }' \
  --name hive-sales-count-2026-08-11
```

### Step 8: Configuration overrides (Spark tuning)

Configuration overrides are applied at the application level and can
be overridden per-job via `sparkSubmitParameters`.

| Override | Default | Production | Why |
|---|---|---|---|
| `spark.sql.shuffle.partitions` | 200 | 200-400 | Tune to data volume. Too low = OOM; too high = scheduling overhead. |
| `spark.sql.adaptive.enabled` | false | true | AQE coalesces shuffle partitions dynamically. Always enable. |
| `spark.executor.memoryOverhead` | 10% of executor memory | 2g | Off-heap memory for Python UDFs, broadcasts. |
| `spark.sql.adaptive.skewJoin.enabled` | false | true | Handles skewed join keys without manual salting. |
| `spark.serializer` | JavaSerializer | KryoSerializer | 10x faster serialization for complex objects. |
| `spark.sql.parquet.compression.codec` | snappy | snappy | Snappy for speed, gzip for size. |

### Step 9: VPC access (private resources)

If the job reads from RDS, Redshift (private), or internal APIs, VPC
access is REQUIRED.

```bash
aws emr-serverless update-application \
  --application-id "$APP_ID" \
  --network-configuration '{
    "subnetIds": ["subnet-aaa", "subnet-bbb"],
    "securityGroupIds": ["sg-emr-prod"]
  }'
```

Rules:
- **Use PRIVATE subnets.** EMR Serverless workers do not need public IPs.
- **Span at least 2 AZs** (3 for production HA).
- **Security group outbound** must allow the database port (e.g., 5432
  for Postgres, 3306 for MySQL) and 443 for S3/Glue VPC endpoints.
- **NAT Gateway is NOT required** for S3/Glue access — use VPC gateway
  endpoints. NAT is only needed for external API calls.
- **NEVER deploy without VPC access if the job reads from private RDS.**
  The job will fail with `ConnectionTimeoutException`.

### Step 10: Interactive endpoints (Spark Connect, notebooks)

Spark Connect allows remote Spark sessions from notebooks (Jupyter,
Zeppelin), IDEs (Databricks Connect, IntelliJ), and applications
without running a full Spark driver locally.

```bash
aws emr-serverless create-interactive-endpoint \
  --application-id "$APP_ID" \
  --execution-role-arn arn:aws:iam::123456789012:role/EMRServerlessExecRole \
  --release-label emr-7.2.0 \
  --configuration-overrides '{
    "monitoringConfiguration": {
      "s3MonitoringConfiguration": {"logUri": "s3://emr-logs-123456789012/interactive/"},
      "cloudWatchLoggingConfiguration": {"enabled": true}
    }
  }'
```

Rules:
- **Interactive endpoints are billed per-second** while active. Set
  auto-stop to 15 minutes idle.
- **Spark Connect uses a thin client protocol** — the driver runs on
  the EMR Serverless cluster, not locally. Ideal for laptop-based
  exploration.
- **Jupyter Enterprise Gateway** is the backend for notebook-style
  interactive sessions. Configured via the `managedEndpoints` option.

### Step 11: Verification

```bash
aws emr-serverless get-application --application-id "$APP_ID"
aws emr-serverless list-job-runs --application-id "$APP_ID"
aws emr-serverless get-job-run --application-id "$APP_ID" --job-run-id "<job-id>"
aws iam get-role --role-name EMRServerlessExecRole
aws s3 ls s3://emr-logs-123456789012/etl-spark-prod/
aws logs describe-log-groups --log-group-name-prefix /aws/emr-serverless/etl-spark-prod
```

## Latest EMR Serverless features (2024-2026)

- **Spark Connect (2024-2026):** remote Spark sessions via thin client
  protocol. Enables interactive data exploration from notebooks and
  IDEs without running a local Spark driver. The driver runs on the
  EMR Serverless cluster.
- **Interactive endpoints (2024-2026):** managed endpoints for Jupyter
  Enterprise Gateway and Spark Connect. Billed per-second while active.
  Pair with auto-stop for cost control.
- **Automated application start/stop (2024-2025):** auto-start when a
  job is submitted; auto-stop after configurable idle timeout. Saves
  cost for non-24/7 workloads.
- **Lake Formation integration (2024-2026):** fine-grained access
  control (column-level, row-level) on Glue tables via Lake Formation.
  The execution role needs `lakeformation:GetDataAccess`.
- **Gang scheduling (2024-2025):** all workers for a job are scheduled
  simultaneously or the job waits. Eliminates partial allocation
  deadlocks for large Spark jobs.
- **Custom images (2024-2025):** custom Docker images from ECR for
  additional libraries (pandas, scikit-learn, custom JARs). Pin the
  image tag — NEVER use `latest`.
- **Blueprints (2024-2026):** reusable application templates for
  common Spark/Hive patterns. Reduces setup time for teams.
- **Application snapshots (2024-2026):** save and restore application
  state (including loaded libraries and initialized JVMs) to reduce
  cold-start time for recurring jobs.

## Workload matrix

| Workload | Type | Pre-init capacity | Max capacity | VPC access | Interactive |
|---|---|---|---|---|---|
| **Nightly ETL (Spark)** | Spark | 50 workers | 200 workers | Yes (S3 via VPC endpoint) | No |
| **Ad-hoc analytics (Spark Connect)** | Spark | 10 workers | 100 workers | Yes | Yes (Spark Connect) |
| **Hive batch (legacy)** | Hive | 0 (cold start OK) | 50 workers | No | No |
| **Streaming (Structured Streaming)** | Spark | 20 workers | 50 workers | Yes | No |
| **ML training** | Spark | 100 workers | 300 workers | Yes (S3 models) | No |
| **Notebook exploration** | Spark | 5 workers | 30 workers | Yes | Yes (Jupyter) |
| **Dev/test** | Spark | 0 (cold start OK) | 10 workers | No | No |

## NEVER (top 5 — full list of 12 in references)

- NEVER submit a job to an application that has no execution role
  configured. The job fails immediately with `AccessDeniedException`
  on the first S3 operation. The execution role is the #1
  prerequisite for EMR Serverless.
- NEVER use `AdministratorAccess` on the execution role. Scope to the
  specific S3 buckets, Glue databases, and Secrets Manager secrets the
  job needs. EMR Serverless jobs run arbitrary code — a broad role is
  a privilege escalation vector.
- NEVER deploy a Spark application that reads from private RDS without
  VPC access configured. The job fails with `ConnectionTimeoutException`
  after the configured socket timeout (default 60s). This is the #1
  silent-failure pitfall for database-connected Spark jobs.
- NEVER set pre-initialized capacity higher than needed. Each warm
  worker is billed at the hourly rate whether or not it runs a job.
  Start at the minimum sustained workload and scale up based on
  observed cold-start frequency.
- NEVER use `:latest` on the custom image tag. EMR Serverless pulls
  the image at application start — a new push silently changes what
  runs. Pin to a version tag or SHA digest. #1 reproducibility breaker.

## Expert heuristic — sizing, capacity, and interactive strategy

- **Pre-initialized capacity decision:** set `initialCount` to the
  number of workers needed for the minimum sustained workload. For
  nightly ETL that runs for 2 hours, pre-initialized capacity is a
  waste — use cold start (60-90s is acceptable). For ad-hoc analytics
  with frequent queries, pre-initialized capacity eliminates cold-start
  latency.
- **The 3x burst rule:** set maximum capacity to 3x the pre-initialized
  capacity. This gives headroom for bursty workloads without
  unbounded cost.
- **Spark Connect vs JDBC:** use Spark Connect for interactive
  exploration from notebooks/IDEs (thin client, driver on cluster).
  Use JDBC for BI tools that need a persistent connection (Tableau,
  Looker via Spark Thrift Server).
- **Auto-stop tuning:** 15 minutes is the default. For interactive
  workloads, set to 60 minutes (users take breaks). For batch, set to
  5 minutes (job finishes, application should stop immediately).
- **Hive vs Spark SQL:** use Spark SQL for all new workloads — it is
  3-10x faster than Hive on Tez for the same query. Use Hive only for
  legacy HiveQL pipelines that are too complex to migrate.
- **AQE (Adaptive Query Execution):** ALWAYS enable
  `spark.sql.adaptive.enabled=true`. It dynamically coalesces shuffle
  partitions, converts sort-merge joins to broadcast joins, and
  handles skew. There is no reason to disable it in production.
- **Log lifecycle:** S3 logs transition to Glacier after 30 days and
  expire after 365 days. CloudWatch Logs set to 30-day retention.
  NEVER leave logs at default (Never Expire) — costs balloon.

## Pre-flight safety checks (run before any deployment CLI)

- **Confirm execution role exists and trusts `emr-serverless.amazonaws.com`.**
- **Confirm S3 log bucket exists and is not public.**
- **Confirm S3 script bucket has the entry-point script.**
- **Confirm VPC subnets exist (if VPC access needed).**
- **Confirm security group outbound allows S3/Glue VPC endpoints.**
- **Confirm release label is the latest stable.**
- **Confirm service quota for capacity is sufficient.**
- **Confirm Glue database and tables exist (if catalog integration).**
- **For custom images, confirm ECR image exists and is pinned to a tag.**
- **For existing applications, capture current config for rollback.**

Full CLI sequences for all checks in `references/execution-and-capacity-guide.md`.

## Output format — MANDATORY literal labels

When invoked with an EMR Serverless deployment request, your ENTIRE
response MUST be the checklist block below. The labels are
**case-sensitive all-caps keywords**. Do NOT write a preamble. Start
with `APPLICATION:` and stop after the `VERIFICATION_COMMANDS:` block.

```text
APPLICATION: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓]      Application type — Spark | Hive, release label <release>
  [✓]      Execution role — <role-arn> (<scoped-permissions>)
  [✓]      Pre-initialized capacity — <count> workers, <cpu> / <memory> each
  [✓]      Maximum capacity — <max-workers> workers (burst ceiling)
  [✓]      VPC access — subnets <subnet-ids>, security groups <sg-ids>
  [✓]      S3 log bucket — s3://<bucket>/<prefix>/
  [✓]      CloudWatch logging — enabled, log group <log-group>
  [✓]      Job submission — entry point <s3-path>, args <args>
  [✓]      Configuration overrides — <spark-conf-overrides>
  [✓]      Tags — <tags>
  [OPTIONAL] Interactive endpoint — Spark Connect | Jupyter (configured | not configured)
VERIFICATION_COMMANDS:
  aws emr-serverless get-application --application-id <app-id>
  aws iam get-role --role-name <exec-role>
  aws s3 ls s3://<log-bucket>/<prefix>/
  aws logs describe-log-groups --log-group-name-prefix /aws/emr-serverless/<name>
```

**Status marker semantics:**
- `[✓]` — applied and verified.
- `[✗]` — NOT applied or misconfigured. Cite the gap.
- `[OPTIONAL]` — recommended but not required.
- `[INPUT NEEDED]` — prerequisite value missing; operator must provide.

**PREREQUISITES_MISSING verdict:** if any REQUIRED prerequisite is
missing (execution role, S3 log bucket, S3 entry-point script, VPC
subnets for private-resource workloads), the verdict is
`PREREQUISITES_MISSING`.

## Domain

AWS CloudOps / EMR Serverless Analytics Compute Provisioning.

## Edge-case handling

- **Cross-account S3 access:** the execution role needs `s3:GetObject`
  on the cross-account bucket AND the bucket policy in the other
  account must grant your execution role. EMR Serverless does NOT
  support cross-account IAM role assumption within a job.
- **Custom image updates:** when updating a custom image, the
  application must be stopped and restarted to pull the new image.
  Running jobs are NOT interrupted; new jobs use the new image.
- **Pre-initialized capacity with auto-stop:** when auto-stop triggers
  (idle for `idleTimeoutMinutes`), pre-initialized capacity is released.
  A new job re-starts the application and re-initializes workers
  (cold start 60-90s). To avoid this, set auto-stop timeout longer
  than the expected gap between jobs.
- **Lake Formation column-level access:** the execution role needs
  `lakeformation:GetDataAccess` and the Lake Formation admin must
  grant column-level permissions to the role. Without it, the job
  sees all columns (security risk) or none (AccessDenied).
- **Gang scheduling for large jobs:** jobs with > 100 workers may
  partially allocate and deadlock if gang scheduling is disabled.
  Enable gang scheduling via `--configuration-overrides` with
  `spark.scheduler.gang.enabled=true`.
- **Spark Connect session isolation:** each Spark Connect session runs
  in the same application but with isolated SparkContext. Resource
  contention is possible if multiple sessions run heavy queries
  simultaneously. Use separate applications for teams that need
  guaranteed resources.
- **Hive to Spark migration:** HiveQL queries can run on Spark SQL
  with minimal changes. Common gotchas: `CLUSTER BY` (not supported
  in Spark SQL), `TRANSFORM` (different syntax), and SerDe
  differences for custom formats. Test before migrating.

## AWS documentation

- **EMR Serverless Developer Guide** — https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/emr-serverless.html
- **CreateApplication API** — https://docs.aws.amazon.com/emr-serverless/latest/APIReference/API_CreateApplication.html
- **StartJobRun API** — https://docs.aws.amazon.com/emr-serverless/latest/APIReference/API_StartJobRun.html
- **EMR Serverless Execution Role** — https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/getting-started.html
- **Spark Connect on EMR Serverless** — https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/interactive-endpoints-spark-connect.html
- **Interactive Endpoints** — https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/interactive-endpoints.html
- **Pre-initialized Capacity** — https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/using-preinitialized-capacity.html
- **VPC Access** — https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/vpc-access.html
- **EMR Serverless CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/emr-serverless/

## References

- `references/cli-commands-and-iac.md` — full copy-pasteable CLI command
  sequence for all 11 deployment steps, including execution role
  creation, S3 log bucket setup, application creation with capacity
  and VPC config, application start, pre-initialized capacity, Spark
  and Hive job submission, configuration overrides, interactive
  endpoints, and Terraform / CloudFormation equivalents.

- `references/execution-and-capacity-guide.md` — deep reference on
  execution role scoping, VPC networking, pre-initialized capacity
  tuning, maximum capacity burst strategy, Spark Connect interactive
  endpoints, Spark/Hive configuration overrides, full NEVER list,
  edge-case handling, and pre-flight safety CLI.
