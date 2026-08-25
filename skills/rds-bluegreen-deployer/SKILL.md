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

Blue/Green deployment configurations are NOT independent. The green
environment must be created before changes can be made. Changes must
be validated before switchover. Switchover must complete before green
deletion. Use this graph to sequence deployment.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Blue/Green creation | source DB exists; engine supports Blue/Green; no unsupported features (e.g., RDS Custom) | green is provisioned silently; creation takes minutes to hours depending on DB size | the green staging environment |
| Replication (blue to green) | green created successfully | logical replication runs continuously; DDL on blue can break it | green stays in sync with blue |
| Database changes in green | green is AVAILABLE; replication healthy | major version upgrade in green does NOT affect blue; schema changes in green are isolated | validated changes ready for production |
| Green validation | changes applied to green; green is AVAILABLE | validation queries run against green without affecting blue | confidence that green is production-ready |
| Switchover | green validated; no replication lag; switchover timeout set | switchover takes ~1 min; DNS CNAME updated; connections briefly dropped | traffic rerouted to green (new production) |
| Application connection update | switchover completed; DNS propagated | apps using the endpoint CNAME auto-follow; apps with hardcoded IPs do NOT | applications connect to new production |
| Delete green | switchover completed successfully | old blue becomes the new green (can be deleted or kept as fallback); deleting stops 2x billing | cost optimization |

**The green-validation-before-switchover row is the one a baseline
model misses.** A naive model creates blue/green, makes changes, and
immediately switches. The correct heuristic validates green
thoroughly (run application tests, check replication lag, verify
query performance) before switchover. The procedure below forces an
explicit validation step.

**Cross-dependency gotchas:**
- Green replicates from blue via logical replication. DDL in blue
  during the lifecycle breaks replication. Make changes ONLY in green.
- Switchover swaps endpoints: the blue CNAME → green (new production),
  the green CNAME → blue. Apps using the CNAME auto-follow.
- After switchover, the former blue (new green) keeps running (2x
  billing) until explicitly deleted.
- Major version upgrades must follow a supported path. Skipping two
  major versions fails at green creation.

## Expert heuristic: the 2x cost window

The cost window is the entire Blue/Green lifecycle — from creation to
green deletion. Green is a FULL clone; you pay 2x during this window.

```text
T0: Blue/Green created → 2x billing starts
T1: Changes made to green (version upgrade, params, schema)
T2: Green validation (tests, performance checks)
T3: Switchover (~1 min downtime, DNS switch)
T4: Delete former blue → 2x billing ends
```

**Key implication:** plan the entire lifecycle before starting. Do
not leave green running for days without a switchover plan.

## Expert heuristic: what changes go in green vs blue

```text
In GREEN (before switchover):          NEVER in blue (breaks replication):
  Major version upgrade                  DDL on blue
  Parameter group changes                Modifying blue's param group
  Schema changes (DDL)                   Changing blue's option group
  Option group changes
At SWITCHOVER (automatic):              NEVER in green:
  Endpoint DNS switch                      (green is staging only)
  Connection rerouting via CNAME
```

Green is the change environment. Blue is frozen. Changes to blue
during the lifecycle break logical replication.

## Expert heuristic: switchover downtime characteristics

```text
Phase 1: Stop replication (~1-5s) — no app impact
Phase 2: Rename endpoints (DNS CNAME swap, ~1-10s)
Phase 3: Apps reconnect — long-lived connections break

Observed downtime:
  With retry + pooling: < 1 second (often unnoticeable)
  Without retry:        1-60 seconds (DNS propagation)
  Worst case:           minutes (DNS cache, no retry)
```

Ensure applications have connection retry logic BEFORE switchover.

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

Apply a different parameter group to green (specified at creation via
`--target-db-parameter-group-name`). To change parameters in green
after creation:

```bash
# Modify green's parameter group (green DB only)
aws rds modify-db-instance \
  --db-instance-identifier "green-prod-mysql-db" \
  --db-parameter-group-name "prod-mysql80-tuned-params" \
  --apply-immediately \
  --region us-east-1
```

### Schema changes (DDL) in green

Schema changes (ALTER TABLE, CREATE INDEX, etc.) are executed in
green ONLY. These changes do NOT affect blue and are replicated to
green via the logical replication stream from blue.

```bash
# Connect to green and run DDL (example: add a column)
# Use the green endpoint — NEVER the blue endpoint
mysql -h green-prod-mysql-db.cluster-xxx.us-east-1.rds.amazonaws.com \
  -u admin -p \
  -e "ALTER TABLE orders ADD COLUMN status_code INT DEFAULT 0;"
```

**Critical:** Run DDL ONLY against the green endpoint. Running DDL
against blue during the Blue/Green lifecycle breaks logical
replication and can corrupt the switchover.

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

The switchover timeout controls how long the switchover operation can
run before it is rolled back. Default is 300 seconds (5 minutes).

```bash
# Set switchover timeout (e.g., 600 seconds for large databases)
aws rds switchover-blue-green-deployment \
  --blue-green-deployment-identifier "$BG_ID" \
  --switchover-timeout 600 \
  --region us-east-1
```

**Timeout guidance:**
- Small databases (< 100 GB): 300 seconds (default) is sufficient.
- Medium databases (100 GB – 1 TB): 600 seconds.
- Large databases (> 1 TB): 1800 seconds (30 minutes).
- If switchover times out, it rolls back — blue remains production.

## Step 8 — Application connection string update

**The key benefit of Blue/Green:** applications using the RDS
endpoint CNAME do NOT need connection string changes. The DNS switch
is transparent.

```text
Before switchover:
  prod-mysql-db.cluster-xxx.us-east-1.rds.amazonaws.com → BLUE (production)
  green-prod-mysql-db.cluster-xxx.us-east-1.rds.amazonaws.com → GREEN (staging)

After switchover:
  prod-mysql-db.cluster-xxx.us-east-1.rds.amazonaws.com → GREEN (now production!)
  green-prod-mysql-db.cluster-xxx.us-east-1.rds.amazonaws.com → BLUE (now staging)

Application using prod-mysql-db endpoint: NO CHANGE NEEDED
```

**Applications that need attention:**
- Applications with hardcoded IP addresses (not using the DNS
  endpoint): MUST update the IP after DNS propagation.
- Applications with long-lived connections: MUST reconnect after
  switchover (connection retry logic handles this).
- Applications with DNS caching: flush DNS cache after switchover.

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

Blue/Green Deployments have hard limitations. A baseline model may
not surface these; they are critical for deployment planning.

| Limitation | Description | Workaround |
|---|---|---|
| Engine support | Only Aurora MySQL/PostgreSQL, RDS MySQL/PostgreSQL | Use standard modify for unsupported engines |
| RDS Custom | NOT supported | Use standard modify-db-instance |
| Storage type | Must be gp2, gp3, or io1 (not magnetic) | Migrate storage type first |
| Read replica topology | Complex topologies (cascading replicas) may not clone correctly | Simplify topology before Blue/Green |
| Cross-Region read replicas | NOT included in green clone | Recreate cross-Region replicas after switchover |
| Major version skip | Cannot skip more than one major version | Upgrade incrementally (12→13→14, not 12→14 directly if unsupported) |
| DDL on blue | Breaks logical replication | Make changes ONLY in green |
| Cost | 2x during entire lifecycle | Delete green promptly after switchover |

**The engine support limitation is the most impactful.** Many
operators assume Blue/Green works for all RDS engines. It does NOT.
SQL Server, Oracle, MariaDB, and Db2 do NOT support Blue/Green.

## Step 11 — Monitoring during green validation

During green validation, monitor key CloudWatch metrics to ensure
green is healthy and replication is lag-free.

| Metric | What it tells you | Target |
|---|---|---|
| `DatabaseConnections` (green) | Green accepts connections | > 0 during validation |
| `ReplicaLag` | Replication lag from blue to green | < 1 second (near-zero) |
| `CPUUtilization` (green) | Green CPU after changes | Within normal range |
| `FreeableMemory` (green) | Green memory after changes | Within normal range |
| `ReadLatency` / `WriteLatency` (green) | Green query performance | No regression vs blue |
| `FreeStorageSpace` (green) | Green has enough storage | > 20% free |

**Monitor via CLI:**

```bash
# Check replication status
aws rds describe-blue-green-deployments \
  --blue-green-deployment-identifier "$BG_ID" \
  --query 'BlueGreenDeployments[0].{Status:Status,Source:Source,Target:Target}' \
  --region us-east-1 --output table

# Check green DB health
aws rds describe-db-instances \
  --db-instance-identifier "green-prod-mysql-db" \
  --query 'DBInstances[0].{Status:DBInstanceStatus,Engine:Engine,EngineVersion:EngineVersion,Class:DBInstanceClass}' \
  --region us-east-1 --output table
```

## Step 12 — Recent features

**Recent AWS features (2023-2026):**

- **Blue/Green for Aurora PostgreSQL major version upgrades (2023-
  2024):** Enhanced support for PostgreSQL major version upgrades via
  Blue/Green, including version 14, 15, and 16 upgrade paths. Validation
  includes extension compatibility checks.

- **Blue/Green switchover timeout customization (2023-2024):**
  Customizable switchover timeout allows operators to control how long
  a switchover can run before rollback, accommodating large databases
  that need more time for replication drain.

- **Blue/Green for RDS PostgreSQL (2023-2024):** Extended Blue/Green
  support to RDS for PostgreSQL (in addition to Aurora PostgreSQL),
  enabling zero-downtime major version upgrades for self-managed
  PostgreSQL instances.

- **Blue/Green status API improvements (2023-2024):** Enhanced
  `describe-blue-green-deployments` API with detailed status
  transitions (PROVISIONING, AVAILABLE, SWITCHOVER_IN_PROGRESS,
  SWITCHOVER_COMPLETED, SWITCHOVER_FAILED), enabling better lifecycle
  monitoring.

- **Terraform provider support (2023-2024):** The Terraform
  `aws_rds_blue_green_deployment` resource now supports the full
  Blue/Green lifecycle including creation, switchover, and deletion
  via infrastructure-as-code.

- **Blue/Green cost visibility (2024-2025):** AWS Cost Explorer now
  tags green environment resources separately from blue, making it
  easier to track the 2x cost window and identify forgotten green
  environments left running.

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

### Green creation fails (unsupported upgrade path)
- The major version upgrade path is not supported (e.g., skipping two
  major versions). Check AWS docs for supported upgrade paths. Upgrade
  incrementally.

### Green creation fails (RDS Custom)
- RDS Custom does NOT support Blue/Green. Use standard
  `modify-db-instance` for RDS Custom databases.

### Replication lag is high
- Large transactions or heavy write load on blue can cause lag. Wait
  for lag to decrease before switchover. If lag persists, reduce write
  load on blue temporarily.

### Switchover fails (timeout)
- The switchover exceeded the timeout. It rolls back — blue remains
  production. Increase the switchover timeout and retry. Check for
  long-running transactions blocking the switchover.

### Application errors after switchover
- Applications without retry logic see connection errors. Implement
  connection retry logic. For DNS caching issues, flush the DNS cache
  on application servers.

### Blue/Green left running (2x billing)
- After switchover, the former blue (new green) continues running.
  Delete it with `delete-blue-green-deployment --delete-target` to
  stop the 2x cost.

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
