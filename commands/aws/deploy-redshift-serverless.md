---
description: Provision a production-grade Amazon Redshift Serverless namespace and workgroup with KMS encryption, usage limits, Data API, and cross-Region snapshots.
nl_triggers:
  - "create redshift serverless"
  - "provision redshift serverless"
  - "redshift serverless namespace"
  - "redshift serverless workgroup"
  - "redshift serverless RPU capacity"
  - "redshift serverless Data API"
  - "redshift serverless usage limits"
  - "redshift serverless cost controls"
  - "redshift serverless cross-region snapshots"
  - "redshift serverless enhanced VPC routing"
  - "redshift serverless query editor v2"
  - "deploy serverless data warehouse"
  - "redshift serverless KMS encryption"
routes_to: redshift-serverless-deployer
---

# /aws:deploy-redshift-serverless

Activate the `redshift-serverless-deployer` skill and produce a
deployment plan for a production-grade Amazon Redshift Serverless
namespace and workgroup.

## What it does

Reads a deployment specification (namespace name, database name,
admin credentials, KMS key, IAM roles, VPC security groups, subnet
group, base RPU capacity, public access, enhanced VPC routing,
Data API, query editor v2, usage limits, scheduled snapshots,
cross-Region snapshot copy) and produces an ordered deployment
plan with:

1. Namespace-first ordering — the namespace owns the database,
   admin credentials, KMS key, IAM roles, and VPC security groups.
   A workgroup cannot exist without a namespace.
2. Encryption gate — validates that a customer-managed KMS key
   (CMK) is provided for production. The AWS-owned default key
   cannot be audited, rotated, or used for cross-Region snapshots.
3. Admin credential strategy — Secrets Manager-managed
   (recommended, auto-rotation) vs manual password (rotate within
   90 days).
4. VPC networking — subnet group spanning 3+ AZs, security group
   inbound on port 5439, enhanced VPC routing for COPY/UNLOAD
   traffic compliance.
5. Workgroup compute — base capacity RPU (8-512 in multiples of 8),
   public access (disabled for production), enhanced VPC routing,
   Data API, config-parameters.
6. Usage limits — daily and monthly RPU-hour caps with
   breach-action (log, emit-metric, disable). NEVER `disable` on
   production without a runbook.
7. Data API — enabled via config-parameter for Lambda / Step
   Functions / EventBridge query execution without JDBC/ODBC.
8. Query editor v2 — IAM policy association for managed web UI
   access.
9. Snapshots — scheduled automated snapshots with configurable
   interval and retention.
10. Cross-Region snapshot copy — separate destination-Region CMK,
    snapshot copy grant, DR failover procedure.
11. Verification — post-deployment describe commands for all
    resources.

Emits a deterministic deployment plan per workgroup:

```text
WORKGROUP: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [x] Namespace created with DB name, admin credentials, KMS
  [x] Workgroup created with base RPU, subnet group, config
  [x] Usage limits (daily + monthly) configured
  [x] Data API enabled
  [x] Snapshots and cross-Region copy configured
  ...
VERIFICATION_COMMANDS:
  <ordered list of aws redshift-serverless commands>
```

## When to invoke

Provide a deployment spec and ask any of:

- "create a Redshift Serverless namespace"
- "deploy a serverless data warehouse"
- "configure Redshift Serverless usage limits"
- "set up cross-Region snapshots for Redshift Serverless"
- "enable the Data API on Redshift Serverless"
- "configure enhanced VPC routing for Redshift Serverless"

A bare namespace + workgroup name + "deploy Redshift Serverless"
also routes here via the orchestrator.

## Inputs

- **Required:** namespace_name, db_name, admin_user, base_capacity
  (RPU), subnet_group (3+ AZs), security_group (inbound 5439).
- **Recommended:** kms_key_alias (CMK for production), secrets_manager_secret
  (admin password), namespace_iam_role (COPY/UNLOAD/S3/Glue access).
- **Optional:** usage_limits (daily/monthly RPU-hours, breach_action),
  enhanced_vpc_routing, enable_data_api, query_editor_v2_policy,
  snapshot_schedule, cross_region_snapshot_copy (destination_region,
  destination_kms_key), log_exports, concurrency_scaling.

## Outputs

- One VERDICT block per workgroup (READY_TO_DEPLOY or
  PREREQUISITES_MISSING).
- CHECKLIST with all deployment dimensions validated.
- VERIFICATION_COMMANDS with ordered `aws redshift-serverless`,
  `aws kms`, `aws secretsmanager`, and `aws ec2` commands.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 1 Deploy specialist for Redshift Serverless).
- `/aws:audit-redshift-cluster` for post-deployment security and cost
  auditing of provisioned Redshift clusters.
- `/aws:optimize-redshift-cluster` for cost optimization of existing
  Redshift workloads.
