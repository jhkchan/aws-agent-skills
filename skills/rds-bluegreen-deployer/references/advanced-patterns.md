# RDS Blue/Green Deployer — advanced patterns (moved from SKILL.md)

Loaded on demand — content moved verbatim from SKILL.md (progressive disclosure; nothing deleted).

## Configuration dependency graph (novel heuristic) (moved from SKILL.md)

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

## Expert heuristic: the 2x cost window (moved from SKILL.md)

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

## Expert heuristic: what changes go in green vs blue (moved from SKILL.md)

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

## Expert heuristic: switchover downtime characteristics (moved from SKILL.md)

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

## Step 10 — Blue/Green limitations (moved from SKILL.md)

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

## Step 12 — Recent features (moved from SKILL.md)

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

