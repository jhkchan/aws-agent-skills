---
name: mwaa-environment-deployer
description: 'Provisions Amazon Managed Workflows for Apache Airflow (MWAA) environments with production defaults: environment creation (create-environment), Airflow version selection, execution class sizing (mw1.small/medium/large), min/max workers, webserver access mode (PUBLIC_ONLY vs PRIVATE_ONLY), VPC networking (2 private subnets + 1 public subnet for MWAA), security groups, S3 bucket for DAGs (requirements.txt, plugins folder, startup script), DAG upload lifecycle, KMS encryption, CloudWatch Logs (DAG processing, scheduler, webserver, worker), Airflow configuration overrides, startup/stop time, requirements.txt version constraints and plugin ZIP management, IAM execution role. Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating an MWAA environment, configuring Airflow on AWS, sizing execution class, or managing DAGs. Triggers: MWAA environment, Managed Airflow, Airflow execution class, mw1.small, mw1.medium, mw1.large, MWAA VPC, Airflow requirements.txt, MWAA CloudWatch Logs.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with mwaa access (create-environment, get-environment, update-environment, list-environments), iam (create-role, attach-role-policy), s3 (create-bucket, put-object), kms (create-key), ec2 (describe-subnets, describe-security-groups), and cloudwatch (create-log-group). Works with Terraform aws_mwaa_environment resource and CloudFormation AWS::MWAA::Environment templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Analytics
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, mwaa, airflow, managed-airflow, analytics, deploy
  dependencies: aws-orchestrator
  keywords: aws, mwaa, airflow, managed airflow, environment, execution class, mw1.small, mw1.medium, mw1.large, dag, requirements.txt, plugins, vpc, kms, cloudwatch logs, cloudops, deploy, analytics
  when_to_use: Invoke when the user wants to create an Amazon MWAA environment, select an execution class (mw1.small/medium/large), configure VPC networking (2 private subnets + security group), set up the S3 DAG bucket with requirements.txt and plugins, configure CloudWatch Logs, define Airflow configuration overrides, manage the IAM execution role, configure KMS encryption, choose webserver access mode (PUBLIC_ONLY vs PRIVATE_ONLY), or update an existing MWAA environment. Do NOT invoke for self-managed Airflow on EC2/ECS, Amazon EMR scheduling, AWS Step Functions, or Apache Airflow on EKS.
---

# MWAA Environment Deployer

An AWS CloudOps agent skill that provisions Amazon Managed Workflows
for Apache Airflow (MWAA) environments with correct defaults. The
skill walks the operator through execution class sizing (mw1.small/
medium/large), VPC subnet requirements (2 private + 1 public for
MWAA-managed resources), webserver access mode (PUBLIC_ONLY vs
PRIVATE_ONLY), S3 DAG bucket setup (requirements.txt, plugins folder,
startup script), DAG upload lifecycle, KMS encryption, CloudWatch Logs
configuration (DAG processing, scheduler, webserver, worker), Airflow
configuration overrides, requirements.txt version constraints, plugin
ZIP management, IAM execution role scoping, and startup/stop time,
captures environment requirements and VPC readiness, explains why each
default matters, and emits a READY_TO_DEPLOY checklist with copy-
pasteable verification commands.

## Activation keywords

MWAA environment, Managed Airflow, Airflow execution class, mw1.small,
mw1.medium, mw1.large, MWAA VPC, Airflow requirements.txt, MWAA
CloudWatch Logs, MWAA webserver access, Airflow plugin ZIP, MWAA IAM
role, MWAA KMS encryption.

## STRICT output contract

When this skill is invoked with an MWAA environment provisioning
request (create an environment, configure execution class, set up VPC
networking, configure DAGs, manage requirements.txt, or a partial
configuration), the agent MUST respond with the READY_TO_DEPLOY
checklist defined in the "Output format" section using the literal
all-caps labels `MWAA_ENVIRONMENT:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels breaks
automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Execution class sizing | mw1.small/medium/large decision |
| Step 2 — VPC subnet requirements | 2 private + security group |
| Step 3 — Webserver access mode | PUBLIC_ONLY vs PRIVATE_ONLY |
| Step 4 — S3 DAG bucket setup | requirements.txt, plugins, startup |
| Step 5 — Create the environment | Provisioning step |
| Step 6 — CloudWatch Logs | DAG processing, scheduler, webserver, worker |
| Step 7 — Airflow configuration overrides | Custom Airflow config |
| Step 8 — KMS encryption and IAM role | Security |
| Step 9 — Startup/stop time | Scheduling |
| Step 10 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/vpc-and-networking.md | VPC + subnet detail |
| references/dags-and-plugins.md | DAG bucket + requirements detail |

## Mindset

**One-line takeaway:** MWAA is a managed Airflow service that runs your
DAGs without managing infrastructure. The environment needs exactly 2
private subnets in different AZs and a security group for Airflow
components. The S3 bucket holds your DAGs, requirements.txt, and
plugins. The execution class (mw1.small/medium/large) determines cost
and capacity — size by concurrent DAG count.

Three misconceptions dominate MWAA environment misdesign at provisioning
time:

- **"MWAA needs only 1 subnet."** It needs at least 2 private subnets in
  different Availability Zones. MWAA distributes its workers across AZs
  for high availability. With only 1 subnet (or 2 in the same AZ), the
  create-environment API call fails with a validation error. This is
  the #1 cause of MWAA provisioning failures.

- **"Any VPC with subnets will work."** MWAA requires specific VPC
  networking: 2 private subnets for the Airflow components (workers,
  scheduler, webserver) and a route to a NAT Gateway or VPC endpoint
  for S3 access (MWAA pulls DAGs and packages from S3). The security
  group must allow inbound 443 (webserver) and inbound 5432 (for the
  Airflow metadata database, managed by AWS). Missing the NAT Gateway
  or S3 VPC endpoint causes worker startup failures.

- **"requirements.txt is optional."** It is required if any DAG uses
  third-party Python packages. Without a requirements.txt listing the
  packages, the DAGs fail at import time with `ModuleNotFoundError`.
  The requirements.txt must use EXACT version pins (not `>=` or
  `~=`) because MWAA resolves dependencies at environment startup.
  Loose version constraints cause non-reproducible failures when
  package maintainers release breaking changes.

## Configuration dependency graph (novel heuristic)

MWAA environment configurations are NOT independent. The VPC subnets
must exist before the environment. The S3 DAG bucket must exist and
contain DAGs before the environment starts. The IAM role must have the
right permissions before create-environment. KMS encryption applies to
both the environment and CloudWatch Logs. Use this graph to sequence
provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| VPC subnets (2 private) | 2 private subnets in different AZs; security group with inbound 443 | without NAT Gateway or S3 VPC endpoint, workers cannot pull DAGs from S3 | the MWAA environment |
| S3 DAG bucket | bucket exists in same region; DAGs uploaded to /dags folder | bucket versioning recommended for DAG rollback; requirements.txt at root or /requirements path | DAG processing |
| IAM execution role | trust policy for airflow.amazonaws.com; permissions for s3, cloudwatch, sqs, kms | missing permissions cause silent worker failures (check CloudWatch Logs) | environment execution |
| KMS key | key exists; IAM role has kms:Decrypt + kms:GenerateDataKey | encryption applies to metadata DB, EBS volumes, and CloudWatch Logs | data-at-rest protection |
| Execution class (mw1.small/medium/large) | chosen at creation | class determines cost/hr and max concurrent tasks; CANNOT be changed without environment recreation | worker capacity |
| CloudWatch Logs | log groups created or auto-created by MWAA | without log configuration, troubleshooting is impossible; logs default to OFF | observability |
| requirements.txt | uploaded to S3 bucket at specified path | packages with incompatible versions cause silent startup failures; MWAA logs the error in the DAG processing log | third-party package support |
| Plugins ZIP | uploaded to S3 bucket at specified path | ZIP must be named plugins.zip and placed at the configured path | custom Airflow plugins |
| Webserver access mode | PUBLIC_ONLY or PRIVATE_ONLY | PRIVATE_ONLY requires VPC with private subnets and VPN/Direct Connect for console access | webserver reachability |

**The VPC-subnet-requirement row is the one a baseline model misses.**
A baseline model says "select a VPC and subnets." The correct heuristic
recognizes that MWAA needs EXACTLY 2 private subnets in DIFFERENT AZs,
plus a route to S3 (NAT Gateway or VPC endpoint). Missing any of these
causes a provisioning failure that is hard to debug without CloudWatch
Logs.

**Cross-dependency gotchas:**
- The S3 bucket must be in the same region as the MWAA environment.
  Cross-region S3 access causes latency and intermittent failures.
- The IAM role must have permissions to read from the S3 bucket, write
  to CloudWatch Logs, and (if encrypting) use the KMS key. Missing any
  permission causes silent failures — the environment appears to start
  but workers cannot process DAGs.
- requirements.txt version pins must be compatible with the MWAA
  Airflow version. MWAA 2.x uses Python 3.10 or 3.11 depending on the
  version. Packages compiled for a different Python version fail at
  import.
- The execution class is NOT dynamically resizable. Changing from
  mw1.small to mw1.medium requires updating the environment (takes
  20-30 minutes of downtime).
- CloudWatch Logs must be configured at creation time for all 4 log
  groups (DAG processing, scheduler, webserver, worker). Enabling logs
  after creation requires an environment update.

## Expert heuristic: VPC subnet requirements (2 private + security group)

VPC subnet heuristic detail (2 private subnets in different AZs, security group self-reference, DNS, verification): moved verbatim to [references/vpc-and-networking.md](references/vpc-and-networking.md).
The dependency-graph row above is the condensed rule.

## Expert heuristic: execution class sizing by concurrent DAG count

Execution-class sizing heuristic (DAG-count sizing ladder): moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Step 1 below holds the condensed sizing table.

## Expert heuristic: requirements.txt version constraints

requirements.txt version-constraint heuristic (pinning rules, compatibility, local-runner testing): moved verbatim to [references/dags-and-plugins.md](references/dags-and-plugins.md).
NEVER pin apache-airflow; full rules live in the reference.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| 2 private subnets in different AZs | MWAA distributes workers across AZs | `aws ec2 describe-subnets --subnet-ids <ids>` |
| Security group | MWAA needs SG for inter-component communication | `aws ec2 describe-security-groups --group-ids <sg-id>` |
| S3 DAG bucket in same region | MWAA reads DAGs from S3 in-region | `aws s3api get-bucket-location --bucket <bucket>` |
| DAGs uploaded to /dags folder | MWAA scans the /dags folder for DAG files | `aws s3 ls s3://<bucket>/dags/` |
| IAM execution role | MWAA assumes this role for all operations | `aws iam get-role --role-name <role>` |
| KMS key (if encrypting) | Encrypts metadata DB, EBS volumes, logs | `aws kms describe-key --key-id <key-id>` |
| VPC DNS resolution enabled | MWAA needs DNS for internal resolution | `aws ec2 describe-vpc-attribute --vpc-id <vpc> --attribute enableDnsSupport` |
| S3 access path (NAT or VPC endpoint) | Workers pull DAGs from S3 | Verify NAT GW or S3 VPC endpoint in route table |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Execution class sizing

| Class | Cost (us-east-1) | Max workers | Best for |
|---|---|---|---|
| mw1.small | ~$0.55/hr (~$400/mo) | 1-25 | Dev/test, < 25 concurrent DAG runs |
| mw1.medium | ~$1.10/hr (~$800/mo) | 1-50 | Production, 25-75 concurrent DAG runs |
| mw1.large | ~$2.20/hr (~$1600/mo) | 1-100 | Enterprise, 75-200+ concurrent DAG runs |

**Choosing:**
- Count peak concurrent DAG runs (not total DAGs).
- Multiply by average tasks per DAG to estimate concurrent task load.
- < 100 concurrent tasks → mw1.small; 100-500 → mw1.medium; 500+ →
  mw1.large.
- Start with mw1.small for dev/test; upgrade based on CloudWatch
  metrics (queued tasks, scheduler heartbeat delay).

**Common mistake:** choosing mw1.large for a dev environment with 5
DAGs. This wastes ~$1200/month. Start small and scale up.

## Step 2 — VPC subnet requirements

MWAA requires a specific VPC configuration:

Subnet/AZ, S3-endpoint, and NAT verification commands: moved verbatim to [references/vpc-and-networking.md](references/vpc-and-networking.md).
Run all three checks before creating the environment.

## Step 3 — Webserver access mode

| Mode | Description | Use case |
|---|---|---|
| PUBLIC_ONLY | Webserver accessible over the internet with MWAA IAM sign-in | Simplest setup; webserver has a public URL |
| PRIVATE_ONLY | Webserver accessible only from within the VPC (VPN/DX) | Compliance-sensitive environments; no public endpoint |

**PUBLIC_ONLY:** the webserver URL is publicly reachable. Access is
controlled by AWS IAM (the caller must have `airflow:CreateWebLoginToken`
permission). This is the default and simplest mode.

**PRIVATE_ONLY:** the webserver URL resolves to a private IP within the
VPC. You need a VPN, Direct Connect, or a bastion host to access it.
Required for compliance-sensitive environments (HIPAA, FedRAMP).

## Step 4 — S3 DAG bucket setup

The S3 bucket holds DAGs, requirements.txt, plugins, and the startup
script.

Bucket creation and DAG/requirements/plugins upload commands: moved verbatim to [references/dags-and-plugins.md](references/dags-and-plugins.md).
Bucket structure and requirements.txt examples live in the same reference.

## Step 5 — Create the environment

```bash
ENV_ARN=$(aws mwaa create-environment \
  --name "production-airflow" \
  --airflow-version "2.9.2" \
  --environment-class "mw1.medium" \
  --min-workers 1 \
  --max-workers 25 \
  --webserver-access-mode "PUBLIC_ONLY" \
  --source-bucket-arn arn:aws:s3:::my-mwaa-bucket \
  --dag-s3-path "dags/" \
  --requirements-s3-path "requirements.txt" \
  --plugins-s3-path "plugins/plugins.zip" \
  --execution-role-arn arn:aws:iam::123456789012:role/MwaaExecutionRole \
  --network-configuration '{"SecurityGroupIds":["sg-mwaa123"],"SubnetIds":["subnet-aaa","subnet-bbb"]}' \
  --kms-key arn:aws:kms:us-east-1:123456789012:key/abcd1234 \
  --logging-configuration '{
    "DagProcessingLogs":{"Enabled":true,"LogLevel":"INFO"},
    "SchedulerLogs":{"Enabled":true,"LogLevel":"INFO"},
    "WebserverLogs":{"Enabled":true,"LogLevel":"WARNING"},
    "WorkerLogs":{"Enabled":true,"LogLevel":"INFO"}
  }' \
  --region us-east-1 \
  --query 'EnvironmentArn' --output text)
```

Environment status monitoring commands: moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Expected: CREATING → CREATING_SNAPSHOT → AVAILABLE (or FAILED).

Environment creation takes 20-30 minutes. If it fails, check CloudWatch
and the MWAA status message.

## Step 6 — CloudWatch Logs

MWAA emits 4 categories of logs. Enable all 4 for production
environments.

| Log type | What it contains | LogLevel |
|---|---|---|
| DagProcessingLogs | DAG parsing, import errors, syntax errors | INFO |
| SchedulerLogs | Task scheduling, queue management, heartbeat | INFO |
| WebserverLogs | Web requests, authentication, UI errors | WARNING |
| WorkerLogs | Task execution, task failures, operator output | INFO |

Log groups are created at `/aws/mwaa/environment/<env-name>/<LogType>`.
**Without logs enabled, troubleshooting is impossible.** If a DAG fails
to import or a task fails silently, the only diagnostic is CloudWatch
Logs. Always enable all 4 log types at creation time.

## Step 7 — Airflow configuration overrides

Airflow configuration overrides let you customize Airflow settings
without modifying the airflow.cfg directly.

```bash
aws mwaa create-environment \
  --airflow-configuration-options '{
    "core.parallelism": "32",
    "core.dag_concurrency": "16",
    "scheduler.dag_dir_list_interval": "30"
  }' \
  ...
```

**Common overrides:**
- `core.parallelism`: max task instances running simultaneously across
  all DAGs. Do NOT exceed what the execution class supports.
- `core.dag_concurrency`: max task instances per DAG.
- `scheduler.dag_dir_list_interval`: how often (seconds) the scheduler
  scans for new DAG files.

**Common mistake:** setting `core.parallelism` higher than the execution
class supports. mw1.small supports ~10 concurrent tasks; setting
parallelism to 100 causes indefinite task queuing.

## Step 8 — KMS encryption and IAM role

**KMS encryption:** use `--kms-key <key-arn>` to encrypt the metadata
database (RDS), EBS volumes, CloudWatch Logs, and Airflow snapshots. The
IAM role must have `kms:Decrypt` and `kms:GenerateDataKey` on the key.

**IAM execution role trust policy:** must allow
`airflow.amazonaws.com` to assume the role. Minimum permissions:

- `s3:ListBucket` and `s3:GetObject` on the DAG bucket.
- `s3:GetObject` on the requirements.txt and plugins ZIP paths.
- `cloudwatch:PutMetricData` and `logs:CreateLogStream` /
  `logs:PutLogEvents` on MWAA log groups.
- `kms:Decrypt` and `kms:GenerateDataKey` on the KMS key (if encrypting).
- `sqs:SendMessage` and `sqs:ReceiveMessage` for the Celery task queue.

AWS provides a managed policy `AmazonMWAAServiceRolePolicy`. Use this
as a base and add S3 bucket-specific permissions.

## Step 9 — Startup/stop time

MWAA environments run 24/7 by default. For dev/test environments, you
can configure a startup and stop time to reduce costs.

Startup/stop schedule CLI: moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Flag semantics and cost math remain below.

- `--startup-time`: the environment starts at this time (CRON-based).
- `--shutdown-time`: the environment stops at this time.
- Times are in the environment's timezone (default: UTC).
- Only applies to non-production environments. Production environments
  should run 24/7.

**Cost savings:** a dev environment running 12 hours/day instead of
24/7 saves 50% on execution class costs (~$200/month for mw1.small).

## Step 10 — Recent features

Recent AWS features (2023-2026): moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Check before choosing Airflow version, Python 3.11, startup scripts, or PRIVATE_ONLY mode.

## NEVER do these things

1. **NEVER use only 1 subnet for MWAA.** MWAA requires 2 private
   subnets in DIFFERENT Availability Zones. With 1 subnet, the
   create-environment API call fails.

2. **NEVER use unpinned package versions in requirements.txt.** Always
   use exact version pins (`pandas==1.5.3`, not `pandas>=1.5`). Loose
   constraints cause non-reproducible failures when package maintainers
   release breaking changes.

3. **NEVER forget to enable CloudWatch Logs.** Without logs enabled at
   creation time, troubleshooting DAG failures is impossible. Enable
   all 4 log types (DagProcessing, Scheduler, Webserver, Worker).

4. **NEVER over-size the execution class for dev/test.** mw1.small is
   sufficient for < 25 concurrent DAG runs. Starting with mw1.large for
   a dev environment wastes ~$1200/month.

5. **NEVER use PUBLIC_ONLY webserver mode for compliance-sensitive
   environments.** Use PRIVATE_ONLY for HIPAA, FedRAMP, or any
   environment where the webserver must not be publicly accessible.

6. **NEVER pin apache-airflow in requirements.txt.** MWAA manages the
   Airflow version. Pinning it causes conflicts. Do NOT pin boto3 or
   botocore below the MWAA-provided version either.

7. **NEVER upload DAGs without testing them locally first.** Use the
   MWAA local runner Docker image to validate DAG syntax and imports
   before uploading. Syntax errors in DAGs cause the DAG processing
   loop to fail, affecting ALL DAGs in the environment.

8. **NEVER omit the S3 access path from the VPC.** Without a NAT
   Gateway or S3 VPC endpoint, workers cannot pull DAGs. The
   environment starts but DAGs never execute.

9. **NEVER use the same IAM role for MWAA and other services.** The
   MWAA execution role should be scoped to S3 (DAG bucket), CloudWatch
   Logs, KMS, and SQS only. Broad permissions are a security risk.

10. **NEVER change the execution class during business hours without
    planning downtime.** Updating the execution class triggers a 20-30
    minute environment update with task interruption. Schedule during
    off-hours.

## Output format

```text
MWAA_ENVIRONMENT: <env-name> (<class>, Airflow <version>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Environment name: <name>
  [✓|✗] Airflow version: <version>
  [✓|✗] Execution class: mw1.small | mw1.medium | mw1.large
  [✓|✗] Min workers: <n>, Max workers: <n>
  [✓|✗] Webserver access: PUBLIC_ONLY | PRIVATE_ONLY
  [✓|✗] VPC subnets: <subnet-1> (<az-1>), <subnet-2> (<az-2>) — private, different AZs
  [✓|✗] Security group: <sg-id> (inbound 443+5432 self, outbound 443)
  [✓|✗] S3 access path: NAT Gateway | S3 VPC endpoint | BOTH — PASS | MISSING
  [✓|✗] S3 DAG bucket: s3://<bucket> — /dags/ folder with DAGs
  [✓|✗] requirements.txt: s3://<bucket>/<path> (<package-count> packages, exact-pinned)
  [✓|✗] Plugins ZIP: s3://<bucket>/<path> | none
  [✓|✗] Startup script: s3://<bucket>/<path> | none
  [✓|✗] IAM execution role: <role-arn>
  [✓|✗] KMS key: <key-arn> | AWS-managed
  [✓|✗] CloudWatch Logs: DagProcessing=<level>, Scheduler=<level>, Webserver=<level>, Worker=<level>
  [✓|✗] Airflow config overrides: <count> overrides | none
  [✓|✗] Startup/stop time: <start>-<stop> | 24/7
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws mwaa get-environment --name <name> --region <region>
  aws mwaa list-environments --region <region>
  aws s3 ls s3://<bucket>/dags/
```

### Worked example — mw1.medium production environment

```text
MWAA_ENVIRONMENT: production-airflow (mw1.medium, Airflow 2.9.2)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Environment name: production-airflow
  [✓] Airflow version: 2.9.2
  [✓] Execution class: mw1.medium
  [✓] Min workers: 1, Max workers: 25
  [✓] Webserver access: PUBLIC_ONLY
  [✓] VPC subnets: subnet-private-a (us-east-1a), subnet-private-b (us-east-1b) — private, different AZs
  [✓] Security group: sg-mwaa123 (inbound 443+5432 self, outbound 443)
  [✓] S3 access path: S3 VPC endpoint — PASS
  [✓] S3 DAG bucket: s3://my-mwaa-bucket — /dags/ folder with 12 DAGs
  [✓] requirements.txt: s3://my-mwaa-bucket/requirements.txt (5 packages, exact-pinned)
  [✓] Plugins ZIP: s3://my-mwaa-bucket/plugins/plugins.zip
  [✓] Startup script: none
  [✓] IAM execution role: arn:aws:iam::123456789012:role/MwaaExecutionRole
  [✓] KMS key: arn:aws:kms:us-east-1:123456789012:key/abcd1234
  [✓] CloudWatch Logs: DagProcessing=INFO, Scheduler=INFO, Webserver=WARNING, Worker=INFO
  [✓] Airflow config overrides: 3 overrides (parallelism=32, dag_concurrency=16, dag_dir_list_interval=30)
  [✓] Startup/stop time: 24/7
  [✓] Tags: Environment=production, Team=data-platform
VERIFICATION_COMMANDS:
  aws mwaa get-environment --name production-airflow --region us-east-1
  aws mwaa list-environments --region us-east-1
  aws s3 ls s3://my-mwaa-bucket/dags/
```

## Error handling

Error-handling deep dives (creation FAILED, DAGs not executing, tasks queued, requirements install failures, PRIVATE_ONLY webserver): moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on FAILED verdicts or post-deploy symptoms.

## Domain

AWS CloudOps / Amazon Managed Workflows for Apache Airflow (MWAA)
Environment Provisioning and DAG Orchestration.

## AWS documentation

- **MWAA User Guide** — https://docs.aws.amazon.com/mwaa/latest/userguide/what-is-mwaa.html
- **Create an MWAA environment** — https://docs.aws.amazon.com/mwaa/latest/userguide/create-environment.html
- **Execution class sizing** — https://docs.aws.amazon.com/mwaa/latest/userguide/mwaa-environment-types.html
- **MWAA VPC requirements** — https://docs.aws.amazon.com/mwaa/latest/userguide/vpc-create.html
- **requirements.txt for MWAA** — https://docs.aws.amazon.com/mwaa/latest/userguide/working-dags-dependencies.html
- **MWAA IAM role** — https://docs.aws.amazon.com/mwaa/latest/userguide/mwaa-create-role.html
- **CloudWatch Logs for MWAA** — https://docs.aws.amazon.com/mwaa/latest/userguide/manage-logs.html
- **Airflow configuration overrides** — https://docs.aws.amazon.com/mwaa/latest/userguide/configuring-env-variables.html
- **MWAA startup/shutdown** — https://docs.aws.amazon.com/mwaa/latest/userguide/schedule-env.html
- **MWAA webserver access mode** — https://docs.aws.amazon.com/mwaa/latest/userguide/access-airflow-ui.html

## References (load on demand)

- [references/vpc-and-networking.md](references/vpc-and-networking.md) — VPC topology, subnet/AZ verification, S3 access path, security groups, webserver access modes.
- [references/dags-and-plugins.md](references/dags-and-plugins.md) — S3 DAG bucket structure, requirements.txt pinning, plugins ZIP, startup script.
- [references/advanced-patterns.md](references/advanced-patterns.md) — Execution-class sizing heuristic, recent AWS features (2023-2026).
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — Environment status monitoring and startup/stop schedule commands.
- [references/error-handling.md](references/error-handling.md) — Failure diagnosis (creation FAILED, DAG/task execution, requirements installs, webserver access).

