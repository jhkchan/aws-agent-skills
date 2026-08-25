---
name: rds-bluegreen-deployer
description: 'Deploys Amazon RDS Blue/Green Deployments with production defaults: blue/green creation (create-blue-green-deployment — source to staging clone), switchover (1-minute downtime via DNS update), traffic rerouting, switchover timeout configuration, green environment validation, database changes in green (major version upgrade, parameter group changes, schema changes), replication from blue to green (logical replication), delete green after successful switch, Aurora MySQL/PostgreSQL support, Blue/Green limitations (engine version constraints, storage type, read replica topology), monitoring during green validation (CloudWatch Enhanced Monitoring), application connection string update. Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating an RDS blue/green deployment, performing. Triggers: create blue green deployment, rds blue green switchover, zero downtime database upgrade, aurora blue green, rds major version upgrade green, green environment validation, switch over blue green.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with RDS access. Works with Terraform aws_rds_blue_green_deployment resource and CloudFormation AWS::RDS::BlueGreenDeployment templates.'
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
  tags: aws, rds, blue-green, cloudops, deploy, databases, aurora, switchover, zero-downtime, upgrades
  dependencies: aws-orchestrator
  keywords: aws, rds, blue green, blue/green deployment, cloudops, deploy, zero downtime, switchover, aurora, major version upgrade, parameter group, schema change, green environment, staging clone, dns switch
  when_to_use: Invoke when the user wants to create an RDS Blue/Green Deployment, perform a zero-downtime database upgrade (major version, parameter group, or schema changes), switch over a blue/green deployment, validate the green environment before switchover, delete a green environment after successful switchover, or understand Blue/Green limitations. Do NOT invoke for standard RDS modifications without Blue/Green (use modify-db-instance directly), Aurora Global Database failover, or Multi-AZ failover.
---

# RDS Blue/Green Deployer

An AWS CloudOps agent skill that deploys Amazon RDS Blue/Green
Deployments with correct defaults. The skill walks the operator
through blue/green creation (source to staging clone), database
changes in the green environment (major version upgrade, parameter
changes, schema changes), green validation, switchover (1-minute
downtime via DNS update), application connection string implications,
and green cleanup, captures upgrade decisions, explains why each
default matters, and emits a READY_TO_DEPLOY checklist with copy-
pasteable verification commands.

## Activation keywords

create blue green deployment, RDS blue green switchover, zero downtime
database upgrade, Aurora blue green, RDS major version upgrade green,
green environment validation, switch over blue green.

## STRICT output contract

When this skill is invoked with an RDS Blue/Green Deployment request
(create a blue/green deployment, perform zero-downtime upgrade,
switchover, validate green, delete green, or a partial configuration),
the agent MUST respond with the READY_TO_DEPLOY checklist defined in
the "Output format" section using the literal all-caps labels
`BLUE_GREEN:`, `VERDICT:`, `CHECKLIST:`, and `VERIFICATION_COMMANDS:`.
Do NOT preface the checklist with prose, headings, or disclaimers —
emit the block as the first lines of the response. This contract is
what assertion-based evals and downstream deployment pipelines rely
on; deviating from the literal labels breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before deploying |
| Step 1 — Blue/Green model (source to staging clone) | Core deployment model |
| Step 2 — Engine and version support | Aurora MySQL/PostgreSQL, RDS MySQL/PostgreSQL |
| Step 3 — Create the blue/green deployment | Creation step |
| Step 4 — Database changes in green | Major version, parameter, schema changes |
| Step 5 — Green environment validation | Pre-switchover validation |
| Step 6 — Switchover (1-minute downtime) | DNS-based traffic rerouting |
| Step 7 — Switchover timeout configuration | Timeout control |
| Step 8 — Application connection string update | DNS/CNAME implications |
| Step 9 — Delete green after successful switch | Cleanup |
| Step 10 — Blue/Green limitations | Engine version, storage, topology constraints |
| Step 11 — Monitoring during green validation | CloudWatch metrics |
| Step 12 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/switchover-and-dns.md | Switchover + DNS detail |
| references/green-validation-and-changes.md | Validation + changes detail |

## Mindset

**One-line takeaway:** Blue/Green creates a full staging clone
(green) of your production database (blue), replicates changes from
blue to green, lets you make destructive changes (major version
upgrade, parameter changes) in green without touching production,
validates green, then switches traffic in about 1 minute via a DNS
update. The green environment is a full clone — it costs 2x during
validation.

Three misconceptions dominate RDS Blue/Green misdesign at deployment
time:

- **"Blue/Green is zero-downtime."** It is near-zero-downtime. The
  switchover takes approximately 1 minute, during which existing
  connections are briefly dropped and re-established. Applications
  MUST use connection retry logic. The DNS switch is transparent to
  applications that resolve the endpoint at connection time, but
  long-lived connections will break and need reconnect.

- **"I can make changes in blue while green is being created."** You
  should NOT. The green environment is a point-in-time clone of blue.
  Changes made to blue after green creation are replicated via logical
  replication, but DDL changes (schema changes) in blue during the
  Blue/Green lifecycle can break replication. Make changes ONLY in
  green. Blue stays untouched until switchover.

- **"Green is free — it is just a staging copy."** Green is a FULL
  clone — complete instance/storage/IO. You pay 2x database costs
  during the entire Blue/Green lifecycle. Delete green promptly after
  successful switchover to stop the duplicate billing. The cost is the
  trade-off for zero-downtime upgrades.

## Configuration dependency graph (novel heuristic)

The configuration dependency graph and cross-dependency gotchas moved verbatim to
[references/advanced-patterns.md](references/advanced-patterns.md).

## Expert heuristic: the 2x cost window

The 2x cost window timeline and key implication moved verbatim to
[references/advanced-patterns.md](references/advanced-patterns.md).

## Expert heuristic: what changes go in green vs blue

The green-vs-blue change matrix moved verbatim to
[references/advanced-patterns.md](references/advanced-patterns.md).

## Expert heuristic: switchover downtime characteristics

Switchover downtime phase breakdown and retry guidance moved verbatim to
[references/advanced-patterns.md](references/advanced-patterns.md).

## Prerequisites (verify before deploying)

Before emitting deployment commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Source DB (blue) exists | Blue/Green clones an existing DB | `aws rds describe-db-instances --db-instance-identifier <id>` |
| Engine supports Blue/Green | Not all engines/versions support it | Check supported engines (Aurora MySQL, Aurora PostgreSQL, RDS MySQL, RDS PostgreSQL) |
| DB is not RDS Custom | RDS Custom does NOT support Blue/Green | Check `--db-instance-class` is not `custom-*` |
| No pending maintenance actions | Pending maintenance can interfere | `aws rds describe-pending-maintenance-actions` |
| Blue DB is AVAILABLE | Must be healthy before cloning | `aws rds describe-db-instances` — Status = available |
| Major version upgrade path supported | Green upgrade must be a valid path | Check AWS docs for supported upgrade paths |
| Application has retry logic | Switchover causes brief connection drops | Verify application connection retry configuration |
| Switchover timeout decided | Controls how long switchover can run | Decide timeout (default 300 seconds) |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Blue/Green model (source to staging clone)

Blue/Green Deployment creates a staging environment (green) that is a
full clone of the production environment (blue). Changes are made to
green while blue continues to serve production traffic.

| Component | Blue (production) | Green (staging) |
|---|---|---|
| Role | Active production DB | Full clone of blue |
| Traffic | Serves all application traffic | No traffic (isolated) |
| Changes | FROZEN (no changes during lifecycle) | ALL changes go here |
| Replication | Source (writes replicated to green) | Destination (receives blue's changes) |
| Cost | Normal | Additional (2x total during lifecycle) |

**The green environment includes:**
- Primary DB instance (clone of blue primary)
- All read replicas (cloned from blue's read replicas)
- Parameter groups (copied from blue)
- Option groups (copied from blue)
- Subnet groups and security groups (separate from blue)

## Step 2 — Engine and version support

| Engine | Blue/Green Support | Major Version Upgrade in Green |
|---|---|---|
| Aurora MySQL | Yes (all supported versions) | Yes (e.g., 5.7 → 8.0) |
| Aurora PostgreSQL | Yes (all supported versions) | Yes (e.g., 12 → 14, 13 → 15) |
| RDS MySQL | Yes (MySQL 5.7, 8.0) | Yes (5.7 → 8.0) |
| RDS PostgreSQL | Yes (PostgreSQL 12 and later) | Yes (12 → 13, 13 → 14, etc.) |
| RDS Custom | NO | N/A — use standard modify-db-instance |
| Other engines (SQL Server, Oracle, etc.) | NO | N/A |

**Critical:** Blue/Green is supported ONLY for Aurora MySQL, Aurora
PostgreSQL, RDS MySQL, and RDS PostgreSQL. Other engines (SQL Server,
Oracle, MariaDB, Db2) do NOT support Blue/Green Deployments.

## Step 3 — Create the blue/green deployment

```bash
# Create a Blue/Green Deployment
BG_ID=$(aws rds create-blue-green-deployment \
  --blue-green-deployment-name "bg-prod-upgrade-2026" \
  --source arn:aws:rds:us-east-1:123456789012:db:prod-mysql-db \
  --target-engine-version "8.0" \
  --target-db-parameter-group-name "prod-mysql80-params" \
  --region us-east-1 \
  --query 'BlueGreenDeploymentIdentifier' --output text)

echo "Blue/Green Deployment ID: $BG_ID"
```

**Key parameters:**
- `--source`: ARN of the blue DB instance or Aurora cluster
- `--target-engine-version`: The new engine version for green (e.g.,
  "8.0" for MySQL 8.0 upgrade)
- `--target-db-parameter-group-name`: New parameter group for green
  (must match the target engine version)
- `--target-db-cluster-parameter-group-name`: For Aurora clusters

**Creation time:** The green environment is provisioned as a full
clone. Creation time depends on database size (minutes for small DBs,
hours for multi-TB databases).

**Verify creation:**

```bash
aws rds describe-blue-green-deployments \
  --blue-green-deployment-identifier "$BG_ID" \
  --query 'BlueGreenDeployments[0].{Status:Status,Green:Target}' \
  --region us-east-1
# Expected: Status = "PROVISIONING" → "AVAILABLE" → "SWITCHOVER_IN_PROGRESS" → "SWITCHOVER_COMPLETED"
```

## Step 4 — Database changes in green

After green is AVAILABLE, make changes ONLY in green. Blue stays
frozen.

### Major version upgrade in green

The `--target-engine-version` at creation time specifies the major
version for green. The upgrade happens during green provisioning.
After green is AVAILABLE, it runs the target version.

```bash
# Verify green is running the target version
aws rds describe-db-instances \
  --db-instance-identifier "green-prod-mysql-db" \
  --query 'DBInstances[0].{Engine:Engine,EngineVersion:EngineVersion,Status:DBInstanceStatus}' \
  --region us-east-1
# Expected: EngineVersion = "8.0" (the target)
```

### Parameter group changes in green

Parameter-group change CLI for green moved verbatim to
[references/green-validation-and-changes.md](references/green-validation-and-changes.md).

### Schema changes (DDL) in green

Green-only DDL execution example and the never-run-DDL-on-blue warning moved verbatim to
[references/green-validation-and-changes.md](references/green-validation-and-changes.md).

## Step 5 — Green environment validation

Before switchover, validate green thoroughly. This is the most
important step — it is your last chance to catch issues before green
becomes production.

| Validation | What to check | How |
|---|---|---|
| Engine version | Green runs target version | `describe-db-instances` on green |
| Data freshness | Replication lag is near-zero | Check CloudWatch `ReplicaLag` or Blue/Green status |
| Schema correctness | DDL changes applied successfully | Query green for expected schema |
| Query performance | No regression vs blue | Run representative queries on green |
| Parameter changes | Parameters applied correctly | `describe-db-parameters` on green |
| Application tests | App works against green | Point a staging app at green endpoint |
| Connections | Green accepts connections | Test connect to green endpoint |

**Check replication lag:**

```bash
aws rds describe-blue-green-deployments \
  --blue-green-deployment-identifier "$BG_ID" \
  --query 'BlueGreenDeployments[0].Status' \
  --region us-east-1
# Status should be "AVAILABLE" (not "PROVISIONING" or "UPGRADING")
```

**Run validation queries on green:**

```bash
# Connect to GREEN endpoint (verify schema changes applied)
mysql -h green-prod-mysql-db.cluster-xxx.us-east-1.rds.amazonaws.com \
  -u admin -p \
  -e "SELECT COUNT(*) FROM information_schema.columns WHERE table_name='orders' AND column_name='status_code';"
# Expected: 1 (column exists)
```

## Step 6 — Switchover (1-minute downtime)

Switchover reroutes traffic from blue to green by updating the DNS
endpoints. The blue endpoint and green endpoint are swapped.

```bash
# Initiate switchover
aws rds switchover-blue-green-deployment \
  --blue-green-deployment-identifier "$BG_ID" \
  --switchover-timeout 300 \
  --region us-east-1
```

**What happens during switchover:**
1. Replication from blue to green is stopped.
2. Any remaining replicated changes are applied to green.
3. Endpoints are swapped: the blue CNAME now points to green (new
   production), and the green CNAME now points to blue (former
   production).
4. Applications reconnecting use the new endpoint automatically.

**Switchover takes approximately 1 minute.** Applications with
connection retry logic experience a sub-second blip. Applications
without retry logic may see 1-60 seconds of errors.

**Verify switchover:**

```bash
aws rds describe-blue-green-deployments \
  --blue-green-deployment-identifier "$BG_ID" \
  --query 'BlueGreenDeployments[0].{Status:Status,SwitchoverTime:SwitchoverConfigured}' \
  --region us-east-1
# Expected: Status = "SWITCHOVER_COMPLETED"
```

## Step 7 — Switchover timeout configuration

Switchover timeout CLI and size-based timeout guidance moved verbatim to
[references/switchover-and-dns.md](references/switchover-and-dns.md).

## Step 8 — Application connection string update

The endpoint/CNAME swap walkthrough and app-attention list moved verbatim to
[references/switchover-and-dns.md](references/switchover-and-dns.md).

## Step 9 — Delete green after successful switch

After switchover, the former blue is now the new green. It continues
running (and billing). Delete it to stop the 2x cost.

```bash
# Delete the Blue/Green Deployment (cleans up the former blue / new green)
aws rds delete-blue-green-deployment \
  --blue-green-deployment-identifier "$BG_ID" \
  --delete-target \
  --region us-east-1
```

**Critical:** `--delete-target` deletes the former blue database
(now the new green after switchover). This is the standard cleanup.
If you want to keep the former blue as a fallback, omit
`--delete-target` and delete manually later.

**Verify deletion:**

```bash
aws rds describe-blue-green-deployments \
  --blue-green-deployment-identifier "$BG_ID" \
  --region us-east-1 2>&1
# Expected: BlueGreenDeployment NotFound (deleted successfully)
```

## Step 10 — Blue/Green limitations

The Blue/Green limitations table and engine-support caveat moved verbatim to
[references/advanced-patterns.md](references/advanced-patterns.md).

## Step 11 — Monitoring during green validation

Green-validation CloudWatch metrics table and monitoring CLI moved verbatim to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

## Step 12 — Recent features

Recent AWS feature notes (2023-2026) moved verbatim to
[references/advanced-patterns.md](references/advanced-patterns.md).

## NEVER do these things

1. **NEVER make DDL changes in blue during the Blue/Green lifecycle.**
   Blue is frozen. DDL in blue breaks logical replication to green.
   Make ALL changes in green only.

2. **NEVER skip green validation.** Always validate green (engine
   version, data freshness, schema, query performance, application
   tests) before switchover. Validation is the last chance to catch
   issues before green becomes production.

3. **NEVER assume switchover is truly zero-downtime.** Switchover
   takes ~1 minute. Applications MUST have connection retry logic.
   Long-lived connections will break and need to reconnect.

4. **NEVER leave green running after switchover without deleting.**
   After switchover, the former blue becomes the new green and
   continues billing. Delete it (with `--delete-target`) to stop the
   2x cost.

5. **NEVER use Blue/Green for unsupported engines.** Only Aurora
   MySQL/PostgreSQL and RDS MySQL/PostgreSQL support Blue/Green. SQL
   Server, Oracle, MariaDB, and Db2 do NOT. RDS Custom does NOT.

6. **NEVER initiate switchover with high replication lag.** High
   replication lag means green is not in sync with blue. Wait for lag
   to drop to near-zero before switching. High lag during switchover
   increases downtime.

7. **NEVER attempt to skip more than one major version in a single
   Blue/Green.** Unsupported upgrade paths fail at green creation.
   Upgrade incrementally (e.g., 12→13, then 13→14 in a second Blue/
   Green lifecycle).

8. **NEVER forget the switchover timeout.** The default (300 seconds)
   may be too short for large databases. Set an appropriate timeout
   based on database size to avoid rollback during switchover.

9. **NEVER point applications at the green endpoint directly.**
   Applications should use the blue endpoint CNAME. After switchover,
   the CNAME follows to green automatically. Pointing at green
   directly defeats the purpose of the DNS switch.

10. **NEVER create a Blue/Green Deployment without verifying pending
    maintenance actions.** Pending maintenance on blue can interfere
    with green provisioning and switchover. Resolve pending
    maintenance before creating the Blue/Green Deployment.

## Output format

```text
BLUE_GREEN: <blue-db-id> → <green-db-id> (<bg-deployment-id>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Source DB (blue): <db-id> (<engine> <engine-version>)
  [✓|✗] Engine support: Supported (<engine>) | Unsupported (<engine>)
  [✓|✗] Blue status: AVAILABLE | <other-status>
  [✓|✗] Blue/Green deployment: <bg-id> — AVAILABLE
  [✓|✗] Green environment: <green-db-id> (<target-engine-version>)
  [✓|✗] Major version upgrade: <from-version> → <to-version> (in green)
  [✓|✗] Parameter group change: <pg-name> (applied to green)
  [✓|✗] Schema changes: <list> (applied to green)
  [✓|✗] Green validation: PASSED | PENDING
  [✓|✗] Replication (blue → green): ACTIVE, lag < 1s | lag <value>
  [✓|✗] Switchover timeout: <seconds> seconds
  [✓|✗] Application retry logic: Configured | NOT configured (risk)
  [✓|✗] Endpoint strategy: CNAME auto-follow (no app change needed)
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws rds describe-blue-green-deployments --blue-green-deployment-identifier <bg-id> --region <region>
  aws rds describe-db-instances --db-instance-identifier <green-db-id> --region <region>
```

### Worked example — Aurora MySQL major version upgrade via Blue/Green

```text
BLUE_GREEN: prod-mysql-db → green-prod-mysql-db (bg-prod-upgrade-2026)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Source DB (blue): prod-mysql-db (aurora-mysql 5.7.mysql_aurora.2.11.0)
  [✓] Engine support: Supported (aurora-mysql)
  [✓] Blue status: AVAILABLE
  [✓] Blue/Green deployment: bg-prod-upgrade-2026 — AVAILABLE
  [✓] Green environment: green-prod-mysql-db (8.0.mysql_aurora.3.04.0)
  [✓] Major version upgrade: 5.7 → 8.0 (in green)
  [✓] Parameter group change: prod-mysql80-params (applied to green)
  [✓] Schema changes: ALTER TABLE orders ADD status_code INT (applied to green)
  [✓] Green validation: PASSED (engine version confirmed, schema verified, query performance within baseline)
  [✓] Replication (blue → green): ACTIVE, lag < 1s
  [✓] Switchover timeout: 300 seconds
  [✓] Application retry logic: Configured (connection pool with retry)
  [✓] Endpoint strategy: CNAME auto-follow (no app change needed)
  [✓] Tags: Environment=production, Upgrade=mysql57-to-80
VERIFICATION_COMMANDS:
  aws rds describe-blue-green-deployments --blue-green-deployment-identifier bg-prod-upgrade-2026 --region us-east-1
  aws rds describe-db-instances --db-instance-identifier green-prod-mysql-db --region us-east-1
```

## Error handling

Failure modes and their fixes (green creation, replication lag, switchover
timeout, post-switchover app errors, 2x billing) moved verbatim to [references/error-handling.md](references/error-handling.md).

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — configuration dependency graph, 2x cost window, green-vs-blue change matrix, switchover downtime characteristics, limitations table, recent AWS features (moved from this file)
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — Step 11 green-validation CloudWatch metrics and monitoring CLI (moved from this file)
- [references/error-handling.md](references/error-handling.md) — failure modes: green creation fails, replication lag, switchover timeout, application errors after switchover, green left running (moved from this file)
- [references/switchover-and-dns.md](references/switchover-and-dns.md) — switchover + DNS detail; extended with Step 7 timeout configuration and Step 8 connection-string update
- [references/green-validation-and-changes.md](references/green-validation-and-changes.md) — green validation and database-changes detail; extended with the Step 4 parameter-group and schema-change (DDL) procedures

## Domain

AWS CloudOps / Amazon RDS Blue/Green Deployments & Zero-Downtime
Database Upgrades.

## AWS documentation

- **RDS Blue/Green Deployments** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/blue-green-deployments.html
- **Creating a Blue/Green Deployment** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/blue-green-deployments-creating.html
- **Switching over a Blue/Green Deployment** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/blue-green-deployments-switching-over.html
- **Deleting a Blue/Green Deployment** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/blue-green-deployments-deleting.html
- **Blue/Green limitations** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/blue-green-deployments-limitations.html
- **Aurora Blue/Green** — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/blue-green-deployments.html
- **RDS major version upgrades** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_UpgradeDBInstance.Upgrading.html
- **CloudWatch RDS metrics** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Overview.Monitoring.html
