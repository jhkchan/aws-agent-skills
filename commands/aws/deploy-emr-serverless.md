---
description: Provision a production-grade Amazon EMR Serverless Spark or Hive application with pre-initialized capacity, VPC access, execution role, and job submission.
nl_triggers:
  - "create emr serverless"
  - "provision emr serverless"
  - "emr serverless spark application"
  - "emr serverless hive application"
  - "emr serverless pre-initialized capacity"
  - "emr serverless execution role"
  - "emr serverless job submission"
  - "emr serverless vpc access"
  - "emr serverless spark connect"
  - "emr serverless interactive endpoints"
  - "deploy serverless spark"
  - "deploy serverless hive"
  - "emr serverless configuration overrides"
routes_to: emr-serverless-deployer
---

# /aws:deploy-emr-serverless

Activate the `emr-serverless-deployer` skill and produce a
deployment plan for a production-grade Amazon EMR Serverless Spark
or Hive application.

## What it does

Reads a deployment specification (application type, release label,
execution role, pre-initialized capacity, maximum capacity, VPC
subnets, security groups, S3 log bucket, CloudWatch logging, job
entry point, arguments, configuration overrides, interactive
endpoints) and produces an ordered deployment plan with:

1. Application-first ordering — the application is the container
   for all jobs. Without it, no job can be submitted.
2. Execution role gate — validates that an IAM role trusting
   `emr-serverless.amazonaws.com` exists with scoped S3, Glue,
   CloudWatch, and Secrets Manager permissions. NEVER
   `AdministratorAccess`.
3. Capacity configuration — pre-initialized capacity (warm workers
   for immediate start) and maximum capacity (burst ceiling).
4. VPC access — subnets and security groups for private-resource
   jobs (RDS, Redshift private, internal APIs).
5. S3 log bucket — stdout/stderr and Spark event log storage with
   lifecycle policy.
6. CloudWatch logging — structured logging for job observability.
7. Job submission — Spark (entry point + arguments + spark-submit
   parameters) or Hive (query + init script + Tez parameters).
8. Configuration overrides — Spark AQE, shuffle partitions, memory
   tuning, KryoSerializer.
9. Interactive endpoints (optional) — Spark Connect for notebooks
   and IDEs.
10. Auto-start / auto-stop — application lifecycle management for
    cost control.
11. Verification — post-deployment describe commands for all
    resources.

Emits a deterministic deployment plan per application:

```text
APPLICATION: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [x] Application type selected (Spark / Hive)
  [x] Execution role scoped (S3, Glue, CloudWatch, Secrets Manager)
  [x] Pre-initialized capacity configured (warm workers)
  [x] Maximum capacity set (burst ceiling)
  [x] VPC access configured (if private resources)
  [x] S3 log bucket with lifecycle
  [x] CloudWatch logging enabled
  [x] Job submission with entry point and overrides
  ...
VERIFICATION_COMMANDS:
  <ordered list of aws emr-serverless commands>
```

## When to invoke

Provide a deployment spec and ask any of:

- "create an EMR Serverless Spark application"
- "deploy a serverless Spark ETL pipeline"
- "submit a Hive job to EMR Serverless"
- "configure Spark Connect on EMR Serverless"
- "set up pre-initialized capacity for EMR Serverless"
- "configure VPC access for EMR Serverless"

A bare application name + type + "deploy EMR Serverless" also
routes here via the orchestrator.

## Inputs

- **Required:** application_name, type (SPARK or HIVE), release_label,
  execution_role_arn, job_entry_point (for Spark) or hive_query
  (for Hive).
- **Recommended:** s3_log_bucket, cloudwatch_log_group,
  pre_initialized_capacity (worker count, CPU, memory),
  maximum_capacity (burst ceiling).
- **Optional:** vpc_subnets, security_groups (for private resources),
  configuration_overrides (AQE, shuffle partitions, serializer),
  interactive_endpoint (Spark Connect), auto_start, auto_stop_timeout,
  custom_image_uri, tags.

## Outputs

- One VERDICT block per application (READY_TO_DEPLOY or
  PREREQUISITES_MISSING).
- CHECKLIST with all deployment dimensions validated.
- VERIFICATION_COMMANDS with ordered `aws emr-serverless`,
  `aws iam`, `aws s3`, and `aws logs` commands.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 1 Deploy specialist for EMR Serverless).
- `/aws:audit-emr-cluster` for post-deployment security and cost
  auditing of provisioned EMR clusters.
- `/aws:troubleshoot-glue-job` for Glue job troubleshooting (related
  but separate service).
