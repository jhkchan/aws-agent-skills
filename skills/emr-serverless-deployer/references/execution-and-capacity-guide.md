# Execution and Capacity Guide — EMR Serverless Deployer

Deep reference on execution role scoping, VPC networking,
pre-initialized capacity tuning, maximum capacity burst strategy,
Spark Connect interactive endpoints, Spark/Hive configuration
overrides, the full NEVER list, edge-case handling, and pre-flight
safety CLI.

## Execution role scoping

### Trust policy

The execution role MUST trust `emr-serverless.amazonaws.com`. NOT
`elasticmapreduce.amazonaws.com` (that is the provisioned EMR
principal). Mixing them produces `AccessDeniedException`.

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "emr-serverless.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

### Permission scoping matrix

| Workload | Required permissions |
|---|---|
| **S3 read (source data)** | `s3:GetObject`, `s3:ListBucket` on source bucket |
| **S3 write (curated + logs)** | `s3:PutObject` on target + log bucket |
| **Glue catalog (read)** | `glue:GetTable`, `glue:GetDatabase`, `glue:GetPartitions` |
| **Glue catalog (write)** | `glue:CreateTable`, `glue:UpdateTable`, `glue:DeleteTable` |
| **CloudWatch Logs** | `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents` |
| **Secrets Manager (DB creds)** | `secretsmanager:GetSecretValue` on secret ARN |
| **KMS (if encrypted S3)** | `kms:Decrypt`, `kms:GenerateDataKey` on CMK |
| **Lake Formation (fine-grained)** | `lakeformation:GetDataAccess` |

**NEVER use `AdministratorAccess` on the execution role.** EMR
Serverless jobs run arbitrary code — a broad role is a privilege
escalation vector.

### Cross-account S3 access

For cross-account S3 buckets:
1. Your execution role needs `s3:GetObject` on the cross-account bucket
   ARN.
2. The cross-account bucket policy must grant your execution role ARN.
3. EMR Serverless does NOT support cross-account IAM role assumption
   within a job — the execution role is the sole identity.

## VPC networking deep dive

### When VPC access is required

| Resource type | VPC access needed? |
|---|---|
| **S3 (public bucket)** | No — S3 is accessed via AWS public endpoints |
| **S3 (via VPC endpoint)** | Yes — if you enforce VPC endpoint policy |
| **Glue Data Catalog** | No — Glue is a public service |
| **RDS / Aurora (private)** | Yes — REQUIRED |
| **Redshift (private)** | Yes — REQUIRED |
| **Internal APIs (private ALB)** | Yes — REQUIRED |
| **DynamoDB** | No — DynamoDB is a public service |
| **Secrets Manager** | No — via public endpoint or VPC endpoint |

### Security group rules

| Direction | Port | Source / Destination | Purpose |
|---|---|---|---|
| Outbound | 443 | S3 VPC endpoint | S3 reads/writes (if VPC endpoint enforced) |
| Outbound | 443 | Glue VPC endpoint | Glue catalog access |
| Outbound | 5432 | RDS SG | Postgres read/write |
| Outbound | 3306 | MySQL SG | MySQL read/write |
| Outbound | 443 | Internal ALB | Internal API calls |

**NEVER deploy without VPC access if the job reads from private RDS.**
The job fails with `ConnectionTimeoutException` after the configured
socket timeout (default 60s).

### NAT Gateway vs VPC endpoints

- **NAT Gateway is NOT required for S3/Glue** — use VPC gateway
  endpoints (free, faster).
- **NAT Gateway IS required** for external API calls (third-party
  REST APIs, package repositories).
- **NEVER rely on NAT for S3** — NAT bandwidth is shared and costs
  $0.045/GB processed. VPC endpoint is free.

## Pre-initialized capacity tuning

### The warm-cold decision

| Scenario | Pre-initialized capacity? | Why |
|---|---|---|
| **Nightly batch (2h window)** | No | Cold start (60-90s) is negligible vs 2h runtime |
| **Frequent ad-hoc queries (every 5 min)** | Yes | Cold start on every query = unacceptable latency |
| **Streaming (Structured Streaming)** | Yes | Stream must not restart with cold start |
| **ML training (2h, once a week)** | No | Cold start is negligible |
| **Notebook exploration (interactive)** | Yes | Users expect instant response |

### Cost model

- **Pre-initialized workers are billed at the hourly rate** whether or
  not they run a job.
- **Cold start (no pre-init)** — billed only for job duration.
- **Break-even:** if the gap between jobs is < 15 minutes (auto-stop
  timeout), pre-initialized capacity saves money by avoiding cold
  start re-initialization.

### Capacity sizing heuristics

| Workload | Worker count | CPU / Memory | Driver |
|---|---|---|---|
| **Small ETL (< 100 GB)** | 5-10 | 4 vCPU / 16 GB | 2 vCPU / 8 GB |
| **Medium ETL (100 GB - 1 TB)** | 20-50 | 4 vCPU / 16 GB | 4 vCPU / 16 GB |
| **Large ETL (1-10 TB)** | 50-200 | 8 vCPU / 32 GB | 8 vCPU / 32 GB |
| **ML training** | 50-100 | 8 vCPU / 32 GB + GPU | 8 vCPU / 32 GB |
| **Streaming** | 10-30 | 4 vCPU / 16 GB | 4 vCPU / 16 GB |

## Maximum capacity burst strategy

### The 3x burst rule

Set maximum capacity to **3x the pre-initialized capacity**. This
gives headroom for bursty workloads without unbounded cost.

| Pre-initialized | Maximum | Rationale |
|---|---|---|
| 10 workers | 30 workers | Small ad-hoc |
| 50 workers | 150 workers | Standard ETL |
| 100 workers | 300 workers | Heavy ETL |

### When a job exceeds maximum capacity

- If the job requests more workers than the maximum, it is **queued**
  (workers become available as others finish) or **fails** (if the
  minimum required workers exceeds the maximum).
- Monitor the `ResourceAllocated` vs `ResourceRequested` CloudWatch
  metrics to detect capacity bottlenecks.

## Spark Connect interactive endpoints

### What Spark Connect enables

- **Remote Spark sessions** from notebooks (Jupyter, Zeppelin), IDEs
  (Databricks Connect, IntelliJ), and applications without running a
  local Spark driver.
- **Thin client protocol** — the driver runs on the EMR Serverless
  cluster. The client only sends the query plan.
- **Session isolation** — each session runs in the same application
  but with an isolated SparkContext.

### Connecting from a client

```python
# PySpark Spark Connect client
from pyspark.sql.connect import SparkSession

spark = SparkSession.builder \
    .remote("sc://<endpoint-host>:443") \
    .getOrCreate()

df = spark.read.parquet("s3://curated/events/")
df.groupBy("event_type").count().show()
```

```bash
# spark-shell (Scala)
spark-shell --remote sc://<endpoint-host>:443
```

### Cost control for interactive endpoints

- **Interactive endpoints are billed per-second** while active.
- **Auto-stop** — set idle timeout to 60 minutes for interactive
  workloads (users take breaks). For batch, 5 minutes.
- **Separate applications for teams** — resource contention is
  possible if multiple sessions run heavy queries simultaneously.

## Spark configuration overrides

### The always-enable list

| Override | Value | Why |
|---|---|---|
| `spark.sql.adaptive.enabled` | `true` | AQE coalesces shuffle partitions dynamically |
| `spark.sql.adaptive.coalescePartitions.enabled` | `true` | Reduces small files after shuffle |
| `spark.sql.adaptive.skewJoin.enabled` | `true` | Handles skewed join keys without salting |
| `spark.serializer` | `KryoSerializer` | 10x faster serialization |
| `spark.sql.parquet.compression.codec` | `snappy` | Speed-optimized compression |

### Memory tuning

| Spark config | Formula | Example (16 GB executor) |
|---|---|---|
| `spark.executor.memory` | 75% of worker memory | 12g |
| `spark.executor.memoryOverhead` | max(2g, 15% of executor memory) | 2g |
| `spark.memory.fraction` | 0.6 (default 0.6) | 0.6 |
| `spark.memory.storageFraction` | 0.5 (default 0.5) | 0.5 |

### Shuffle partition tuning

| Data volume | `spark.sql.shuffle.partitions` |
|---|---|
| < 100 GB | 100-200 |
| 100 GB - 1 TB | 200-400 |
| 1-10 TB | 400-1000 |
| > 10 TB | 1000-2000 |

With AQE enabled, the exact number matters less — AQE coalesces
dynamically. But starting too low causes OOM; too high causes
scheduling overhead.

## Full NEVER list (12 items)

1. NEVER submit a job to an application without an execution role.
2. NEVER use `AdministratorAccess` on the execution role.
3. NEVER deploy a Spark app that reads from private RDS without VPC access.
4. NEVER set pre-initialized capacity higher than needed.
5. NEVER use `:latest` on the custom image tag.
6. NEVER trust `elasticmapreduce.amazonaws.com` in the execution role.
7. NEVER leave S3 logs at default (Never Expire) lifecycle.
8. NEVER disable AQE in production.
9. NEVER set auto-stop timeout to 0 (application never stops, infinite cost).
10. NEVER submit a Hive job to a Spark application (type mismatch).
11. NEVER forget CloudWatch logging configuration — job failures are invisible.
12. NEVER use the same application for production and dev/test workloads.

## Edge-case handling

### Custom image updates

When updating a custom image, the application must be stopped and
restarted to pull the new image. Running jobs are NOT interrupted;
new jobs use the new image.

### Pre-initialized capacity with auto-stop

When auto-stop triggers (idle for `idleTimeoutMinutes`),
pre-initialized capacity is released. A new job re-starts the
application and re-initializes workers (cold start 60-90s). To avoid
this, set auto-stop timeout longer than the expected gap between
jobs.

### Lake Formation column-level access

The execution role needs `lakeformation:GetDataAccess` and the Lake
Formation admin must grant column-level permissions to the role.
Without it, the job sees all columns (security risk) or none
(AccessDenied).

### Gang scheduling for large jobs

Jobs with > 100 workers may partially allocate and deadlock if gang
scheduling is disabled. Enable gang scheduling via
`--configuration-overrides` with `spark.scheduler.gang.enabled=true`.

### Hive to Spark migration

HiveQL queries can run on Spark SQL with minimal changes. Common
gotchas: `CLUSTER BY` (not supported in Spark SQL), `TRANSFORM`
(different syntax), and SerDe differences for custom formats. Test
before migrating.

## Pre-flight safety CLI

```bash
# 1. Execution role trust policy
aws iam get-role --role-name <exec-role> \
  --query 'Role.AssumeRolePolicyDocument.Statement[?Principal.Service==`emr-serverless.amazonaws.com`]'

# 2. S3 log bucket
aws s3 ls s3://<log-bucket>/

# 3. Entry-point script
aws s3 ls s3://<script-bucket>/<entry-point>

# 4. VPC subnets
aws ec2 describe-subnets --subnet-ids <subnet-ids>

# 5. Security group outbound
aws ec2 describe-security-groups --group-ids <sg-ids> \
  --query 'SecurityGroups[0].IpPermissionsEgress'

# 6. Release label
aws emr-serverless list-release-labels

# 7. Service quota
aws service-quotas get-service-quota \
  --service-code emr-serverless \
  --quota-code L-XXXXXXXX

# 8. Glue database (if catalog integration)
aws glue get-database --name <db-name>

# 9. Custom image (if used)
aws ecr describe-images --repository-name emr-serverless --image-ids imageTag=<tag>

# 10. Existing application config (for rollback)
aws emr-serverless get-application --application-id <app-id> > /tmp/app-backup.json
```
