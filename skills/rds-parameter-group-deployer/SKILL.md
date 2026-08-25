---
name: rds-parameter-group-deployer
description: 'Provisions RDS DB parameter groups with correct production defaults: family selection (postgres15, mysql8.0, aurora-postgresql15), static vs dynamic parameters (static requires DB instance reboot), ApplyMethod (immediate vs pending-reboot), PostgreSQL tuning (max_connections, shared_buffers, work_mem, wal_buffers, checkpoint_completion_target), MySQL tuning (innodb_buffer_pool_size, max_connections, slow_query_log), Aurora-specific parameters, Aurora Serverless v2 capacity parameters, and parameter group association with DB instances and clusters. Emits a READY_TO_DEPLOY checklist. Use when creating a DB parameter group, tuning PostgreSQL/MySQL parameters, configuring Aurora Serverless v2, or associating a parameter group with a DB instance. Triggers: create RDS parameter group, DB parameter group family, postgres parameter group, mysql parameter group, Aurora parameter group, static vs dynamic parameters, shared_buffers, innodb_buffer_pool_size, max_connections, ApplyMethod, pending-reboot.'
license: Apache-2.0
compatibility: 'Requires an LLM agent runtime (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with rds access. Works with Terraform aws_db_parameter_group / aws_rds_cluster_parameter_group resources, CloudFormation AWS::RDS::DBParameterGroup / AWS::RDS::DBClusterParameterGroup, and SAM templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Databases
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, rds, aurora, databases, cloudops, deploy, parameter-group, postgres, mysql
  dependencies: aws-orchestrator
  keywords: aws, rds, aurora, databases, cloudops, deploy, provisioning, parameter-group, postgres, mysql, tuning, static-dynamic, apply-method, aurora-serverless-v2
  when_to_use: Invoke when the user wants to create a new RDS DB parameter group or DB cluster parameter group, tune PostgreSQL or MySQL parameters, configure Aurora-specific parameters, set up Aurora Serverless v2 capacity settings, or associate a parameter group with a DB instance or Aurora cluster. Do NOT invoke for option groups (use the option-group skill), for DB instance class changes (use the instance-deployer skill), or for RDS Proxy configuration.
---

# RDS Parameter Group Deployer

An AWS CloudOps agent skill that provisions RDS DB parameter groups
and DB cluster parameter groups with correct production defaults.
The skill walks the operator through a 9-step provisioning
procedure, explains why each default matters, and emits a
READY_TO_DEPLOY checklist verifying every configuration item.

## Quick navigation

| Need | Section |
|---|---|
| What MUST be in the response | "STRICT output contract" |
| Why the provisioning order matters | "Reasoning framework" |
| What to verify before provisioning | "Prerequisites" |
| The ordered provisioning steps | "Deployment procedure" |
| Common silent-failure pitfalls | "NEVER" |
| Choosing family, parameters, ApplyMethod | "Expert heuristic" |
| Workload-specific defaults | "Workload matrix" |
| 2024-2026 feature changes | "Recent AWS features" |
| Deep CLI sequences | `references/deployment-cli-commands.md` |
| PostgreSQL/MySQL/Aurora tuning reference | `references/database-tuning-guide.md` |

## Activation keywords

create RDS parameter group, DB parameter group, DB parameter group
family, DB cluster parameter group, postgres parameter group,
mysql parameter group, aurora parameter group, static vs dynamic
parameters, ApplyMethod immediate, pending-reboot, shared_buffers,
work_mem, wal_buffers, checkpoint_completion_target,
max_connections, innodb_buffer_pool_size, slow_query_log,
long_query_time, aurora_enable_repl_bin_log_filter,
aurora serverless v2, RDS parameter tuning, ModifyDBParameterGroup,
ModifyDBClusterParameterGroup.

## STRICT output contract

When this skill is invoked with an RDS parameter group provisioning
request (group name, family, engine, parameter list, or a partial
existing configuration), the agent MUST respond with the
READY_TO_DEPLOY checklist defined in "Output format" using the
literal all-caps labels `GROUP:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of
the response.

### Required output structure

1. `GROUP: <parameter-group-name>` — the parameter group being
   provisioned.
2. `VERDICT: READY_TO_DEPLOY` OR `VERDICT: PREREQUISITES_MISSING` —
   nothing else.
3. `CHECKLIST:` followed by indented lines, each prefixed with a
   status marker (`[✓]`, `[✗]`, `[OPTIONAL]`, `[INPUT NEEDED]`).
4. `VERIFICATION_COMMANDS:` followed by indented `aws rds ...`
   commands the operator can run.

### 6 FORBIDDEN output patterns (each silently breaks automation)

1. **FORBIDDEN — prose preamble before `GROUP:`.** The first
   non-empty line MUST be `GROUP:`. No "Here is your parameter
   group checklist…".
2. **FORBIDDEN — markdown variants of the labels.** Write
   `VERDICT:`, not `**VERDICT:**`, `### Verdict`, `Verdict =`, or
   `\`VERDICT\``. The labels are case-sensitive all-caps keywords.
3. **FORBIDDEN — swapping verdict tokens.** The verdict is exactly
   `READY_TO_DEPLOY` or `PREREQUISITES_MISSING` — not "ready",
   "missing", "BLOCKED", "OK", or "needs review".
4. **FORBIDDEN — omitting `VERIFICATION_COMMANDS:`.** Even when
   the verdict is `PREREQUISITES_MISSING`, include the commands
   the operator needs to verify the gaps.
5. **FORBIDDEN — extra sections after `VERIFICATION_COMMANDS:`.**
   The checklist block is the entire response. Put deeper
   explanation in `references/` files, not after the block.
6. **FORBIDDEN — status marker drift.** Use only `[✓]`, `[✗]`,
   `[OPTIONAL]`, `[INPUT NEEDED]`. Do not invent `[?]`, `[!]`,
   `[WARN]`, or emoji markers.

### Perfect example (copy the shape exactly)

```text
GROUP: payments-pg15-params
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓]      Family — postgres15
  [✓]      Type — DBParameterGroup
  [✓]      max_connections — 200 (dynamic, immediate)
  [✓]      shared_buffers — {6GB} (static, PENDING REBOOT required)
  [✓]      work_mem — 8MB (dynamic, immediate)
  [✓]      wal_buffers — 16MB (dynamic, immediate)
  [✓]      checkpoint_completion_target — 0.9 (dynamic, immediate)
  [✓]      Association — DB instance payments-db-pg15 (pending reboot for static params)
  [✓]      Tags — Environment=production, Application=payments
VERIFICATION_COMMANDS:
  aws rds describe-db-parameters --db-parameter-group-name payments-pg15-params
  aws rds describe-db-instances --db-instance-identifier payments-db-pg15
  aws rds describe-pending-maintenance-actions --db-instance-identifier payments-db-pg15
```

## Reasoning framework (why the provisioning order matters)

RDS parameter group provisioning has **family, static-vs-dynamic,
and association constraints** that make the procedure non-trivial.
Applying configurations in the wrong order causes parameters that
silently don't take effect, unnecessary reboots, or Aurora cluster
disconnects:

1. **Family FIRST — the DB parameter group family is immutable.**
   The family (`postgres15`, `mysql8.0`, `aurora-postgresql15`,
   `sqlserver-se-15.00`, `oracle-ee-19`) determines which
   parameters are available and their defaults. The family MUST
   match the DB engine version. A `postgres14` parameter group
   cannot be associated with a `postgres15` instance. The family
   CANNOT be changed after creation — you must create a new group.

2. **DBParameterGroup vs DBClusterParameterGroup — two types.**
   A `DBParameterGroup` applies to individual DB instances. A
   `DBClusterParameterGroup` applies to all instances in an Aurora
   cluster (and is the ONLY type accepted by Aurora clusters).
   Regular RDS (non-Aurora) uses DBParameterGroup only. Aurora
   uses BOTH — the cluster parameter group sets cluster-level
   defaults, and each instance can override via its own
   DBParameterGroup.

> Moved verbatim to [`references/advanced-patterns.md`](references/advanced-patterns.md) — load on demand.


## Prerequisites (verify before deployment)

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| **DB engine and version** | The parameter group family MUST match the engine version. `postgres15` ≠ `postgres14`. | `aws rds describe-db-instances --db-instance-identifier <id>` |
| **Parameter group family** | Derived from the engine version. Immutable after creation. | `aws rds describe-db-engine-versions --engine postgres --query 'DBEngineVersions[].DBParameterGroupFamily'` |
| **DB instance or cluster identifier** (for association) | The parameter group must be associated with an existing instance or cluster. | `aws rds describe-db-instances` / `aws rds describe-db-clusters` |
| **Parameter data types** | Each parameter has a `DataType` (string, integer, boolean) and `AllowedValues`. Setting the wrong type fails at ModifyDBParameterGroup time. | `aws rds describe-db-parameters --db-parameter-group-name <family-default>` |
| **Static vs dynamic awareness** | Static parameters require a reboot. Plan reboot windows accordingly. | `DescribeDBParameters` — check `ApplyType: static` |
| **Aurora cluster type** (if Aurora) | Aurora Serverless v2 uses `ServerlessV2ScalingConfiguration`, not parameter values, for capacity. Parameter group tuning complements the ACU range. | `aws rds describe-db-clusters --db-cluster-identifier <id>` |
| **IAM permissions** | Caller needs `rds:CreateDBParameterGroup`, `rds:ModifyDBParameterGroup`, `rds:ModifyDBInstance` or `rds:ModifyDBCluster`. | `aws sts get-caller-identity` |

## Deployment procedure (apply in order)

### Step 1: Family selection

The parameter group family is determined by the DB engine and
version. It is immutable after creation.

> Moved verbatim to [`references/advanced-patterns.md`](references/advanced-patterns.md) — load on demand.


### Step 2: DBParameterGroup vs DBClusterParameterGroup

| Type | Used by | Scope |
|---|---|---|
| `DBParameterGroup` | RDS instances, Aurora instance-level overrides | Single DB instance |
| `DBClusterParameterGroup` | Aurora clusters ONLY | All instances in an Aurora cluster |

**Rule:** if the target is an Aurora cluster, create a
`DBClusterParameterGroup`. If the target is a regular RDS instance,
create a `DBParameterGroup`. Aurora clusters can use BOTH — cluster
group for cluster-level defaults, instance group for overrides.

### Step 3: Static vs dynamic parameters

Every RDS parameter has an `ApplyType` of either `static` or
`dynamic`:

- **Dynamic** — the parameter takes effect immediately (for
  `ApplyMethod: immediate`) or at the next connection. No reboot
  required.
- **Static** — the parameter requires a DB instance reboot to take
  effect. `ApplyMethod` is always `pending-reboot` regardless of
  what you specify.

> Moved verbatim to [`references/deployment-cli-commands.md`](references/deployment-cli-commands.md) — load on demand.


> Moved verbatim to [`references/database-tuning-guide.md`](references/database-tuning-guide.md) — load on demand.


### Step 4: ApplyMethod (immediate vs pending-reboot)

The `ApplyMethod` controls when a parameter change takes effect:

> Moved verbatim to [`references/deployment-cli-commands.md`](references/deployment-cli-commands.md) — load on demand.


| ApplyMethod | Effect | Works for |
|---|---|---|
| `immediate` | Applies as soon as possible (typically within seconds for dynamic params) | Dynamic parameters only |
| `pending-reboot` | Applies after the next DB instance reboot | Static AND dynamic parameters |

**Rule:** always use `immediate` for dynamic parameters (unless you
want to batch changes at the next maintenance window). Always use
`pending-reboot` for static parameters (it is the only option, but
explicitly stating it documents the reboot requirement).

Setting `ApplyMethod: immediate` on a static parameter does NOT
force immediate application. RDS silently treats it as
`pending-reboot`. This is a common source of confusion.

### Step 5: Common PostgreSQL tuning parameters

> Moved verbatim to [`references/database-tuning-guide.md`](references/database-tuning-guide.md) — load on demand.


### Step 6: Common MySQL tuning parameters

> Moved verbatim to [`references/database-tuning-guide.md`](references/database-tuning-guide.md) — load on demand.


### Step 7: Aurora-specific parameters

> Moved verbatim to [`references/database-tuning-guide.md`](references/database-tuning-guide.md) — load on demand.


### Step 8: Aurora Serverless v2 capacity

> Moved verbatim to [`references/database-tuning-guide.md`](references/database-tuning-guide.md) — load on demand.


### Step 9: Create + associate + apply

> Moved verbatim to [`references/deployment-cli-commands.md`](references/deployment-cli-commands.md) — load on demand.


For Aurora clusters, use `create-db-cluster-parameter-group` /
`modify-db-cluster-parameter-group` / `modify-db-cluster`.

## Workload matrix

| Workload | Engine | Key parameters | Notes |
|---|---|---|---|
| OLTP (high-throughput) | PostgreSQL | `shared_buffers=25%`, `work_mem=8MB`, `max_connections=200`, `checkpoint_completion_target=0.9` | Use RDS Proxy for connection pooling |
| Read-heavy analytics | PostgreSQL | `work_mem=64MB`, `maintenance_work_mem=1GB`, `effective_cache_size=75%`, `random_page_cost=1.1` | Higher work_mem for large sorts/hashes |
| MySQL web app | MySQL | `innodb_buffer_pool_size=75%`, `max_connections=300`, `slow_query_log=1`, `long_query_time=1` | Enable slow query logging in production |
| Aurora Serverless v2 | Aurora PG/MySQL | Use formula values (`{DBInstanceClassMemory/N}`), conservative `work_mem` | Never set absolute memory values |
| Migration staging | PostgreSQL | Source DB's exact parameter values | Match source to validate query plans |
| High-availability replica | Aurora MySQL | `aurora_enable_repl_bin_log_filter=1`, `binlog_format=ROW` | ROW format for reliable replication |

## Recent AWS features (2024-2026)

> Moved verbatim to [`references/advanced-patterns.md`](references/advanced-patterns.md) — load on demand.


## NEVER (anti-patterns)

- NEVER create a parameter group with the wrong family. The family
  is immutable. A `postgres15` parameter group cannot attach to a
  `postgres14` instance. Always verify the engine version before
  creating.

- NEVER set `ApplyMethod: immediate` on a static parameter and
  assume it will apply without a reboot. RDS silently treats it as
  `pending-reboot`. Static parameters ALWAYS require a reboot.
  Check `ApplyType` via `DescribeDBParameters` before setting.

- NEVER set absolute memory values (`shared_buffers = 6GB`) on
  Aurora Serverless v2. The instance class changes dynamically
  with ACU scaling — an absolute value tuned for 16 ACU causes OOM
  at 2 ACU. Always use `{DBInstanceClassMemory/N}` formula syntax.

- NEVER modify a production DB parameter group without planning a
  reboot window for static parameters. Static parameters (like
  `shared_buffers`, `max_connections` on some engines) require a
  reboot. Schedule during a maintenance window.

- NEVER disable `autovacuum` on PostgreSQL in production. Without
  autovacuum, dead tuples accumulate, bloat increases, and
  performance degrades. Tune autovacuum settings
  (`autovacuum_naptime`, `autovacuum_vacuum_threshold`) instead.

- NEVER exceed `max_connections` beyond what the instance class can
  handle. Each connection consumes memory (thread stack + work_mem +
  sort buffers). Formula: `(RAM - shared_buffers) / (work_mem × 2)`
  gives a safe ceiling. Use RDS Proxy or PgBouncer for pooling.

- NEVER set `innodb_flush_log_at_trx_commit=0` or `sync_binlog=0`
  in production if data durability matters. These settings trade
  crash safety for throughput — you can lose committed transactions
  on a crash. Use `1` for both unless you explicitly accept the risk.

- NEVER change a parameter group on an Aurora cluster without
  understanding that the DBClusterParameterGroup applies to ALL
  instances. Instance-level overrides via DBParameterGroup can
  conflict — test the interaction in staging.

- NEVER forget to associate the parameter group with the DB
  instance after creating it. Creating the group alone has no
  effect. Call `ModifyDBInstance` or `ModifyDBCluster`.

- NEVER deviate from the checklist output format. Substituting
  `Verdict` / `**VERDICT**` / `### Verdict:` for the literal
  `VERDICT:` label silently breaks downstream deployment pipelines
  and assertion-based evals.

## Expert heuristic — choosing family, parameters, and ApplyMethod

**Family — match the engine version exactly:** the family is
`<engine><major-version>` (e.g., `postgres15`, `mysql8.0`). For
Aurora, prefix with `aurora-` (e.g., `aurora-postgresql15`). Use
`DescribeDBEngineVersions` to find the family for a specific engine
version. When in doubt, check the existing default group name
(`default.postgres15`).

**Parameters — start with memory and connections, then planner:**
the highest-impact parameters are `shared_buffers` / 
`innodb_buffer_pool_size` (25-75% of RAM), `max_connections`
(scale with instance class), `work_mem` (4-16MB per query), and
planner hints (`effective_cache_size`, `random_page_cost`). These
have more impact than micro-tuning dozens of minor parameters.

**ApplyMethod — immediate for dynamic, pending-reboot for static:**
always check the parameter's `ApplyType` before setting
`ApplyMethod`. Dynamic + immediate = no reboot. Static + any
`ApplyMethod` = reboot required. When changing multiple parameters,
batch them in one `ModifyDBParameterGroup` call — it applies
atomically and minimizes reboot windows.

**Aurora — use DBClusterParameterGroup:** Aurora clusters require
a cluster parameter group. Instance-level DBParameterGroups are
optional overrides. Set cluster-level parameters (like
`aurora_enable_repl_bin_log_filter`) in the cluster group. Set
instance-specific tuning (like `work_mem`) in the instance group.

**Serverless v2 — formula values only:** never set absolute memory
values. Use `{DBInstanceClassMemory/N}` for all memory-related
parameters. The formula adapts as the ACU scales. Set
`max_connections` based on the MAX capacity, not the minimum.

**Reboot planning — always flag static changes:** when the
checklist includes any `[✓]` item with `(static, PENDING REBOOT
required)`, call out the reboot requirement in the checklist.
Static parameter changes are a no-op until the instance reboots.
Schedule during a maintenance window for production.

## Pre-flight safety checks (run before any provisioning CLI)

- **Confirm the DB engine and version:**
  ```bash
  aws rds describe-db-instances --db-instance-identifier <id> \
    --query 'DBInstances[].{Engine:Engine,EngineVersion:EngineVersion}'
  ```

- **Confirm the parameter group family matches the engine:**
  ```bash
  aws rds describe-db-engine-versions --engine postgres \
    --query 'DBEngineVersions[].{Version:EngineVersion,Family:DBParameterGroupFamily}'
  ```

- **Confirm parameter data types and allowed values:**
  ```bash
  aws rds describe-db-parameters --db-parameter-group-name default.postgres15 \
    --query 'Parameters[?ParameterName==`shared_buffers`]'
  ```

- **Confirm the DB instance or cluster exists:**
  ```bash
  aws rds describe-db-instances --db-instance-identifier <id>
  aws rds describe-db-clusters --db-cluster-identifier <id>
  ```

- **For Aurora Serverless v2, confirm the scaling configuration:**
  ```bash
  aws rds describe-db-clusters --db-cluster-identifier <id> \
    --query 'DBClusters[].ServerlessV2ScalingConfigurationInfo'
  ```

- **For existing parameter groups, capture current values for rollback:**
  ```bash
  aws rds describe-db-parameters --db-parameter-group-name <name> \
    --query 'Parameters[?Source!=`engine-default`]' \
    > /tmp/<name>-backup.json
  ```

## Output format — MANDATORY literal labels

When invoked with a parameter group provisioning request, your
ENTIRE response MUST be the checklist block below. The labels are
**case-sensitive all-caps keywords** — write them EXACTLY as shown.
Do NOT write a preamble. Start with `GROUP:` and stop after the
`VERIFICATION_COMMANDS:` block.

```text
GROUP: <parameter-group-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓]      Family — <postgres15 | mysql8.0 | aurora-postgresql15 | ...>
  [✓]      Type — <DBParameterGroup | DBClusterParameterGroup>
  [✓]      <parameter-name> — <value> (<dynamic|static>, <immediate|pending-reboot>)
  [✓]      ... (repeat for each parameter)
  [✓]      Association — <db-instance-id | db-cluster-id | pending>
  [✓]      Reboot required — <yes (static params changed) | no (dynamic only)>
  [✓]      Tags — <key=value pairs>
VERIFICATION_COMMANDS:
  aws rds describe-db-parameters --db-parameter-group-name <name>
  aws rds describe-db-instances --db-instance-identifier <id>
  aws rds describe-pending-maintenance-actions --db-instance-identifier <id>
```

**Status marker semantics:**
- `[✓]` — configuration is applied and verified.
- `[✗]` — configuration is NOT applied or is misconfigured. Cite
  the gap.
- `[OPTIONAL]` — recommended but not required for the workload type.
- `[INPUT NEEDED]` — a prerequisite value is missing (engine
  version, DB instance ID, parameter group family) and the operator
  must provide it before provisioning can proceed.

**PREREQUISITES_MISSING verdict:** if any REQUIRED prerequisite is
missing (DB engine version to determine the family, DB instance
identifier for association), the verdict is
`PREREQUISITES_MISSING` with each gap listed. The checklist shows
the target configuration with `[INPUT NEEDED]` or `[✗]` for unmet
prerequisites.

## Edge-case handling

> Moved verbatim to [`references/advanced-patterns.md`](references/advanced-patterns.md) — load on demand.


## References (load on demand)

- [references/deployment-cli-commands.md](references/deployment-cli-commands.md) — static/dynamic parameter check, ApplyMethod payload, and the full create + modify + associate + reboot CLI sequence.
- [references/database-tuning-guide.md](references/database-tuning-guide.md) — static/dynamic parameter tables, PostgreSQL/MySQL/Aurora tuning tables, and Aurora Serverless v2 capacity interactions.
- [references/advanced-patterns.md](references/advanced-patterns.md) — reasoning-framework constraints, family selection tables, recent AWS features, edge-case handling.

## Domain

AWS CloudOps / RDS Database Parameter Group Provisioning.

## AWS documentation

- **Amazon RDS User Guide** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithParamGroups.html
- **RDS Parameter Groups** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithDBInstanceParamGroups.html
- **PostgreSQL Parameters on RDS** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Appendix.PostgreSQL.CommonDBATasks.Parameters.html
- **MySQL Parameters on RDS** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Appendix.MySQL.CommonDBATasks.Parameters.html
- **Aurora Serverless v2** — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2.setting-capacity.html
- **RDS CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/rds/

## References

- `references/deployment-cli-commands.md` — full copy-pasteable CLI
  command sequence for all 9 provisioning steps, including parameter
  group creation, parameter modification (static and dynamic),
  association with DB instances and Aurora clusters, reboot
  procedures, Aurora Serverless v2 capacity configuration, and
  Terraform `aws_db_parameter_group` /
  `aws_rds_cluster_parameter_group` resource equivalents.

- `references/database-tuning-guide.md` — deep reference on
  PostgreSQL and MySQL parameter tuning (memory sizing formulas,
  connection pooling, autovacuum, InnoDB internals), Aurora-specific
  parameters, Aurora Serverless v2 capacity interactions, and
  static-vs-dynamic parameter classification.
