---
name: rds-instance-auditor
description: >-
  Audits AWS RDS DB instances for the seven high-impact configuration risks that
  drive data-loss and outage incidents — public accessibility (internet-exposed
  database), encryption-at-rest (immutable post-creation), deletion protection,
  Multi-AZ availability, automated-backup / PITR retention, auto minor-version
  upgrade, and Enhanced Monitoring. Emits a deterministic verdict
  (PUBLIC | UNENCRYPTED | NO_DELETION_PROTECTION | SINGLE_AZ | CONFIG_GAP | OK)
  per instance with enumerated findings and specific remediation CLI. Use when
  reviewing RDS posture, checking for internet-reachable databases, validating
  encryption enablement, auditing deletion-protection / backup coverage before
  production deployment, or hardening database instance configuration.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline metadata classification. Live-account
  audits use aws rds describe-db-instances and aws rds describe-db-clusters
  (AWS CLI v2, SSO or key-based credentials).
keywords:
  - RDS
  - DB instance
  - public accessibility
  - encryption-at-rest
  - StorageEncrypted
  - Multi-AZ
  - deletion protection
  - automated backups
  - BackupRetentionPeriod
  - minor version upgrade
  - Enhanced Monitoring
  - PITR
  - Aurora cluster scope
  - database audit
  - data loss prevention
  - PubliclyAccessible
  - DB instance hardening
tags: [rds, databases, security, availability, encryption, backups, multi-az, audit]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Databases
  verdict_shape: "PUBLIC | UNENCRYPTED | NO_DELETION_PROTECTION | SINGLE_AZ | CONFIG_GAP | OK"
  when_to_use: >-
    Reviewing an RDS DB instance configuration before production deployment,
    checking whether a database is internet-reachable, validating
    encryption-at-rest, auditing deletion-protection or backup coverage,
    verifying Multi-AZ posture, or hardening database instance configuration
    across an account.
  when_not_to_use: >-
    Aurora cluster-level posture audits (use the DBCluster block directly),
    performance-tuning or query optimization, IAM/auth analysis (password
    policies, IAM database authentication), certificate/TLS expiry checks
    (acm-certificate-expiry-auditor), KMS key-policy or rotation audits
    (kms-key-policy-auditor), or subnet/route-table reachability analysis.
    This skill classifies configuration posture from instance metadata — it
    does not perform live connectivity or penetration testing.
  activation_triggers:
    - "audit this RDS instance"
    - "is my database public"
    - "check RDS encryption"
    - "is deletion protection enabled"
    - "are automated backups on"
    - "Multi-AZ check"
    - "minor version upgrade"
    - "Enhanced Monitoring off"
    - "harden RDS instance"
    - "PubliclyAccessible true"
    - "BackupRetentionPeriod zero"
  invocation_schema: >-
    Input: either (a) an RDS DB instance configuration (describe-db-instances
    metadata), optionally paired with the DBCluster block for Aurora engines,
    OR (b) a db-instance-identifier for live-account audit. Output:
    deterministic INSTANCE/VERDICT/REASON/FINDINGS/REMEDIATION block per
    instance, where VERDICT ∈ {PUBLIC, UNENCRYPTED, NO_DELETION_PROTECTION,
    SINGLE_AZ, CONFIG_GAP, OK, ERROR}.
  invocation_example: |-
    # Minimal valid input (offline metadata classification):
    DBInstanceIdentifier: db-prod-mysql-01
    Engine: mysql
    DBInstanceStatus: available
    PubliclyAccessible: false
    StorageEncrypted: true
    KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/abc
    MultiAZ: true
    DeletionProtection: false
    BackupRetentionPeriod: 7
    AutoMinorVersionUpgrade: true
    MonitoringInterval: 60
    # For Aurora, also supply the DBCluster block:
    # DBClusterIdentifier, StorageEncrypted, DeletionProtection,
    # BackupRetentionPeriod (cluster is authoritative for these).
---

# RDS Instance Auditor

## Quick start

- **Verdict order (first match wins):** PUBLIC → UNENCRYPTED → NO_DELETION_PROTECTION → SINGLE_AZ → CONFIG_GAP → OK. Emit all dimensions in FINDINGS regardless.
- **Aurora is cluster-scoped:** for `aurora-*` engines, encryption/deletion-protection/Multi-AZ/retention live on the `DBCluster`; defer to `describe-db-clusters`.
- **Encryption is immutable:** `StorageEncrypted` cannot be toggled in place — remediation is snapshot → encrypted-copy → restore-new → cutover.

## Mindset

Audit RDS configuration metadata against seven high-impact dimensions and
emit the worst finding as the verdict, with every dimension enumerated
regardless of the headline.

## Philosophy

Three behaviours separate a senior database engineer from a generalist:

- **`PubliclyAccessible: true` is an internet-exposed database.** This is the
  single highest-impact RDS misconfiguration — a public IP on a database is an
  open invitation to credential stuffing, brute force, and exploitation of any
  auth-layer weakness. Network-layer controls (security groups) reduce but do
  not eliminate the risk; the flag itself is the verdict driver.
- **`StorageEncrypted` is immutable after creation.** Unlike S3 or EFS where
  encryption is a property toggle, an unencrypted RDS instance CANNOT be
  encrypted in place. Remediation is a migration: snapshot → encrypted copy →
  restore-new → endpoint cutover. This is why UNENCRYPTED is a high-severity
  verdict rather than a "toggle and move on" finding.
- **Aurora engines are cluster-scoped, not instance-scoped.** For `aurora-*`
  engines, encryption, deletion protection, and Multi-AZ are properties of the
  DBCluster, not the individual DB instance. Auditing instance-level fields on
  an Aurora instance produces false positives — the cluster block is the source
  of truth.

## Quick reference — severity thresholds

The verdict enum is ordered worst → least. The first matching dimension in the
ordered steps below is the verdict; remaining dimensions are still enumerated
in the FINDINGS list.

| Condition | Verdict | Step |
|---|---|---|
| `PubliclyAccessible: true` on a non-Aurora instance | **PUBLIC** | Step 1 |
| `StorageEncrypted: false` (non-Aurora, or DBCluster for Aurora) | **UNENCRYPTED** | Step 2 |
| `DeletionProtection: false` on the instance (or cluster, Aurora) | **NO_DELETION_PROTECTION** | Step 3 |
| `MultiAZ: false` on a primary, non-Aurora, non-Read-Replica instance | **SINGLE_AZ** | Step 4 |
| `BackupRetentionPeriod: 0` OR `AutoMinorVersionUpgrade: false` OR `MonitoringInterval: 0` | **CONFIG_GAP** | Step 5-7 |
| All seven dimensions pass | **OK** | Step 8 |

See the ordered steps for Aurora/replica edge cases. Deep RDS-specific
behaviours (immutability, cluster scope, standby semantics, maintenance-window
interactions) are in the [Expert edge cases](#expert-edge-cases) section.

## Pre-flight: instance metadata gate (run before classification)

Several instance attributes **short-circuit** or **redirect** the audit.
Misclassifying them produces false positives that erode trust.

**Account-wide sweep (pagination):** `describe-db-instances` caps at 100
records/page. Drain the `Marker` to completion:
```bash
token=""
while true; do
  if [ -z "$token" ]; then
    aws rds describe-db-instances --output json > page.json
  else
    aws rds describe-db-instances --output json --starting-token "$token" > page.json
  fi
  # Process page.json instances here
  token=$(jq -r '.Marker // empty' page.json)
  [ -z "$token" ] && break
done
# Aurora: fetch cluster metadata in a separate paginated call
aws rds describe-db-clusters --output json > clusters.json
```

| Attribute | Value | Effect on audit |
|---|---|---|
| `Engine` | `aurora-mysql`, `aurora-postgresql` | **Aurora instance.** Encryption, deletion protection, and Multi-AZ live on the DBCluster. Do NOT flag instance-level `StorageEncrypted`/`DeletionProtection`/`MultiAZ` — defer to cluster metadata (Steps 2-4 cluster branch). Backup retention is also cluster-level and `0` is rejected by the API. |
| `DBInstanceStatus` | `deleting` | Instance is being torn down. Skip audit, emit `VERDICT: OK` with note "instance is deleting — no remediation applicable." Do NOT propose modifications against a deleting instance. |
| `DBInstanceStatus` | `failed`, `inaccessible`, `incompatible-*` | Instance is non-functional. Surface as an operational finding but still audit the seven dimensions on the stored configuration. |
| `ReadReplicaSourceDBInstanceIdentifier` | present | **Read Replica.** Read-only by design. SINGLE_AZ on a replica is lower acuity (the primary's Multi-AZ is the availability gate for writes); downgrade SINGLE_AZ from a hard fail to a note unless the replica is itself a production read endpoint. |
| `InstanceClass` | `db.serverless` | Aurora Serverless v1/v2 scaling is cluster-governed; MultiAZ semantics differ. Defer to cluster. |
| `PendingModifiedValues` | any field populated | An in-flight modification is queued. Audit the CURRENT value (not the pending one); note the pending change in REMEDIATION so the operator knows whether the gap is already being addressed. |
| `StorageEncrypted: true` + `KmsKeyId` absent | — | RDS uses the AWS-managed `aws/rds` key. **It IS encrypted** — do NOT flag UNENCRYPTED. Key-policy / rotation concerns are the kms-key-policy-auditor's scope, not this skill. |

**If the instance metadata is malformed** (missing `DBInstanceIdentifier`,
absent `Engine`, or unparseable), output:

```text
INSTANCE: <identifier or unknown>
VERDICT: ERROR
REASON: RDS instance metadata is missing required fields (DBInstanceIdentifier, Engine) — cannot classify.
REMEDIATION: Re-fetch with `aws rds describe-db-instances --db-instance-identifier <id> --output json` and re-audit.
```

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious RDS behaviours that change classification

These are the operational gotchas a senior RDS engineer knows from incident
experience — NOT the basic AWS-docs descriptions of what each field does.
Each one changes a verdict if ignored:

- **`modify-db-instance` is last-write-wins per field, per maintenance window.**
  Two modifications to the SAME field queued without `--apply-immediately` do
  not stack — the later value silently overwrites the earlier one. The default
  maintenance window is weekly (e.g. `sun:03:00-sun:04:00`), so an operator
  who queues `--backup-retention-period 1` then `--backup-retention-period 7`
  a few days later sees only `7` applied, not a 1→7 progression. Modifications
  to DIFFERENT fields apply together in the same window. Always surface queued
  values in REMEDIATION so the operator knows which changes will land.

- **Multi-AZ failover recovers the database, not the application.** The
  60-120 second RDS failover covers standby promotion only. JVM clients cache
  DNS for 60 seconds by default (`networkaddress.cache.ttl=60`); many JDBC
  connection pools pin TCP to the old writer's IP until the pool is recycled;
  some HTTP-tier retry policies treat `Connection refused` as fatal rather
  than transient. Without client-side retry/backoff + DNS-cache tuning, a
  Multi-AZ failover still presents as a 5-30 minute outage to the application.
  Treat SINGLE_AZ as an RPO/RTO primitive, not a complete recovery solution —
  note client-side retry requirements in REMEDIATION when flagging SINGLE_AZ
  on production databases.

- **`gp3` IOPS are capped by a storage ratio that silently blocks
  modification.** gp3 includes 3000 IOPS and 125 MB/s throughput at no extra
  cost; above 3000 IOPS you pay per-IOPS-month. But provisioned IOPS cannot
  exceed 500× allocated-GB for MySQL/PostgreSQL (lower ratios for some
  legacy engines — SQL Server ~64:1, Oracle ~250:1). A `modify-db-instance`
  requesting 15000 IOPS on a 20 GB instance fails validation with
  `IopsToStorageRatio` — the operator must either raise storage or drop IOPS.
  When the audit surfaces storage-class or IOPS changes, note the ratio cap so
  the operator does not chase a remediation the API will reject.

- **KMS CMK rotation does NOT re-encrypt existing RDS data.** Enabling
  automatic annual rotation on the backing CMK generates new key material for
  NEW encrypt operations, but existing ciphertext (data files, automated
  backups, manual snapshots) continues to decrypt with the prior key material
  indefinitely. There is no in-place CMK re-encryption path for RDS — rotating
  OFF a compromised CMK requires the same snapshot → re-encrypt → restore-new
  migration as the initial encryption cutover. Operators who enable KMS
  rotation believing it addresses key compromise have a false sense of safety;
  surface this when the instance is encrypted with a CMK the customer
  suspects is compromised.

- **`MultiAZ: true` standby is NOT usable for reads.** The standby is a
  failover target only — it does not accept client connections. This is a
  common misconception: teams enable Multi-AZ expecting read-scaling and are
  surprised when connections to the standby fail. Read-scaling requires
  separate Read Replicas. For SQL Server, Multi-AZ uses Always On / mirroring
  semantics with additional feature constraints.

- **Aurora instances are cluster members, not standalone databases.** For
  `aurora-*` engines, `StorageEncrypted`, `DeletionProtection`, `MultiAZ`, and
  `BackupRetentionPeriod` are properties of the `DBCluster`, not the
  `DBInstance`. `describe-db-instances` returns instance-level echoes of some
  of these, but the cluster block is authoritative. Auditing Aurora at the
  instance level produces false positives on every dimension except public
  accessibility (which IS instance-level even for Aurora — each instance has
  its own `PubliclyAccessible` flag).

- **`EnhancedMonitoring` (`MonitoringInterval > 0`) requires a role and emits
  to CloudWatch Logs.** RDS assumes `MonitoringRoleARN` to emit OS-level
  metrics (CPU steal, swap, file systems) at the configured interval
  (1/5/10/15/30/60 seconds). `0` means off — only engine-level CloudWatch
  metrics exist. Enhanced Monitoring is distinct from Performance Insights
  (query-level) and from RDS Events; this skill audits Enhanced Monitoring
  specifically because it is the gap most often missing on instances that
  later suffer unexplained OS-level incidents.

- **`PendingModifiedValues` is a queue, not the current state.** Always audit
  the top-level CURRENT value; note the pending change via the `[PENDING]`
  annotation in FINDINGS so the operator can decide whether to force-apply or
  wait. See the output-format section for the annotation shape.

- **Read Replicas and Multi-AZ are independent.** A Read Replica can itself
  be Multi-AZ (rare) or single-AZ (common). The replica exists for read
  scaling or cross-region DR; the primary's Multi-AZ posture is the write
  availability gate. Flagging a single-AZ Read Replica as a hard SINGLE_AZ
  finding over-states the risk for read-only workloads.

- **The `--apply-immediately` flag changes blast radius.** For the PUBLIC
  finding, removal of public IP should use `--apply-immediately` (existing
  public-IP connections drop, but the gap closes now). For non-urgent
  dimensions (minor-version upgrade, enhanced monitoring), prefer the
  maintenance window to avoid stacking modifications. Encryption has no
  `--apply-immediately` path at all — it is the snapshot-migration workflow.

- **Cross-Region Read Replicas inherit the source encryption state.** You
  cannot create an encrypted cross-region read replica from an unencrypted
  source — the KMS key is region-scoped, so the replica must reference a CMK in
  the destination region. An unencrypted primary silently blocks the entire
  cross-region DR topology. If a cross-region replica exists for this instance,
  flag its encryption state as a DR-readiness signal, not just a data-protection
  finding.

- **Setting `BackupRetentionPeriod` to 0 is immediately destructive.** It does
  not merely "stop future backups" — it triggers immediate deletion of all
  existing automated backups, transaction logs, and PITR history for the
  instance. The only recovery path after that is a manual snapshot (if one
  exists). When remediating in the other direction (0 → 7), the first automated
  backup is triggered within the next backup window, not instantly.

- **`StorageType: magnetic` is deprecated and cannot skip generations.**
  Instances on `magnetic` (standard HDD) cannot be modified directly to `io1`/
  `io2`/`gp3` — they must transition through `gp2` first. Separately, `gp3`
  (the current default for new instances) provisions IOPS and throughput
  independently of storage capacity, so a `gp3` instance with low allocated
  storage but high IOPS needs is valid and should not be flagged as
  under-provisioned from capacity alone.

### Step 1: Public accessibility (highest priority — internet exposure)

If `PubliclyAccessible: true` on the instance, the dimension verdict is
**PUBLIC**. This is the worst verdict in the enum — an internet-reachable
database is the highest-impact RDS misconfiguration. The flag is evaluated
first because exposure compounds every other finding: an unencrypted, no-backup
public database is a write-once ransomware target.

For Aurora instances, `PubliclyAccessible` is still instance-level (each
instance gets its own flag), so this step applies the same way.

A `0.0.0.0/0` security-group inbound rule is NOT required to produce PUBLIC —
the flag alone is sufficient. Note permissive SGs in REMEDIATION regardless.

### Step 2: Encryption-at-rest (immutable — migration required)

For non-Aurora engines: if `StorageEncrypted: false`, the dimension verdict is
**UNENCRYPTED**.

For Aurora engines: defer to the `DBCluster.StorageEncrypted` field. If the
cluster block is not provided in the input, emit an AURORA_SCOPE note and do
NOT classify this dimension from the instance-level echo — flag it as needing
cluster metadata. If `DBCluster.StorageEncrypted: false`, the verdict is
UNENCRYPTED at the cluster level. **Missing-cluster fallback:** when no
DBCluster block is provided, append to FINDINGS:
`[AURORA_SCOPE] Cluster metadata missing — run: aws rds describe-db-clusters --db-cluster-identifier <cluster-id> --output json. Cannot classify encryption/deletion-protection/Multi-AZ from instance echoes. Verdict reflects instance-level checks only (PubliclyAccessible).`
This prevents silent false-positives while giving the operator the exact CLI
to fetch the missing data.

`StorageEncrypted: true` with absent `KmsKeyId` is OK — RDS uses the
AWS-managed `aws/rds` key. Do NOT flag this as UNENCRYPTED.

### Step 3: Deletion protection (accidental deletion guardrail)

For non-Aurora: if `DeletionProtection: false`, the dimension verdict is
**NO_DELETION_PROTECTION**. With protection off, a single
`delete-db-instance` call (with `--skip-final-snapshot`) destroys the instance
and its data. The guardrail exists to force a deliberate disable step before
destructive actions.

For Aurora: defer to `DBCluster.DeletionProtection`. Instance-level deletion
protection is not the gate for Aurora — the cluster is the deletable unit.

### Step 4: Multi-AZ (availability — AZ failure resilience)

For non-Aurora primary instances: if `MultiAZ: false`, the dimension verdict
is **SINGLE_AZ**. With no standby, an AZ-level failure (power, network, host)
causes an outage until RDS provisions a replacement — typically minutes to
tens of minutes. Multi-AZ provides a synchronous standby in a second AZ with
automatic failover (60-120 seconds of connection drop).

**Downgrade cases (note in FINDINGS, do not drive the verdict):**
- **Read Replica** (`ReadReplicaSourceDBInstanceIdentifier` present): the
  replica is read-only; the primary's Multi-AZ is the write-availability gate.
  Emit SINGLE_AZ as a note, not a hard finding, unless this replica is a
  production read endpoint with strict read SLAs.
- **Aurora instance**: Multi-AZ is a cluster-level property (replicas across
  AZs). Defer to the cluster; do not flag instance-level `MultiAZ`.

### Step 5: Automated backups (PITR coverage)

If `BackupRetentionPeriod: 0` on a non-Aurora instance, this is a CONFIG_GAP
contributor. `0` disables automated backups and point-in-time recovery
entirely — there is no transaction-log archive and the only restore path is a
manual snapshot. The valid range is 0-35 days; AWS default is 7.

For Aurora: `BackupRetentionPeriod` is cluster-level and `0` is rejected by
the API (continuous backups, 1-35). A reported `0` on Aurora is stale or
invalid metadata — note it but do NOT flag CONFIG_GAP from this field.

### Step 6: Auto minor-version upgrade (patching hygiene)

If `AutoMinorVersionUpgrade: false`, this is a CONFIG_GAP contributor. The
instance will not pick up minor-engine-version patches during the maintenance
window — these include security fixes and stability improvements. Major
versions are always opt-in and are out of scope for this flag.

### Step 7: Enhanced Monitoring (OS-level observability)

If `MonitoringInterval: 0` (or absent), Enhanced Monitoring is OFF and this
is a CONFIG_GAP contributor. Without it, only engine-level CloudWatch metrics
exist — there is no OS-level signal for CPU steal, swap pressure, or file
system fill, which are the precursors to most "the database is slow but
CloudWatch looks fine" incidents.

### Step 8: Aggregation — worst finding wins

The final verdict is the **worst** dimension verdict in this fixed order,
where PUBLIC > UNENCRYPTED > NO_DELETION_PROTECTION > SINGLE_AZ > CONFIG_GAP >
OK:

```text
verdict = first_match(
  Step 1 PUBLIC,
  Step 2 UNENCRYPTED,
  Step 3 NO_DELETION_PROTECTION,
  Step 4 SINGLE_AZ,
  Step 5-7 CONFIG_GAP,
  OK
)
```

All dimensions are still enumerated in the FINDINGS list regardless of the
verdict, so the operator sees the full posture (a PUBLIC instance that is
also UNENCRYPTED shows both, with PUBLIC as the headline verdict).

## Output format (per instance)

```text
INSTANCE: <db-instance-identifier>
VERDICT: PUBLIC | UNENCRYPTED | NO_DELETION_PROTECTION | SINGLE_AZ | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its step number>
FINDINGS:
  - [PUBLIC] <finding description (Step 1)>
  - [UNENCRYPTED] <finding description (Step 2)>
  - [OK] <dimension that passed>
  - [PENDING] <field> is queued to change to <value> at next window / on --apply-immediately (audited on CURRENT value; do not double-remediate)
REMEDIATION: <specific action per finding, or "None required" if OK>
CONFIRM: Before executing any state-changing CLI above, emit and await operator
approval: "CONFIRM: About to <action> on <id> in <region>. Proceed? (yes/no)"
```

The `[PENDING]` line is emitted ONLY when `PendingModifiedValues` contains a
queued change to one of the seven audited fields. It is informational — the
verdict and FINDINGS reflect the CURRENT value. Skip the `[PENDING]` line when
no fields are pending.

### Concrete error-handling example — malformed metadata

When the input is missing required fields (no `DBInstanceIdentifier`, absent
`Engine`, or unparseable JSON), the skill MUST emit a single deterministic
ERROR block and NOT attempt partial classification:

```text
INSTANCE: <identifier or unknown>
VERDICT: ERROR
REASON: RDS instance metadata is missing required fields (DBInstanceIdentifier, Engine) — cannot classify.
FINDINGS:
  - [ERROR] Missing field: <field-name>. Re-fetch with `aws rds describe-db-instances --db-instance-identifier <id> --output json`.
REMEDIATION: Re-fetch metadata and re-audit. If the identifier is unknown, list instances first with `aws rds describe-db-instances --query 'DBInstances[*].DBInstanceIdentifier' --output text`.
```

For a field that is present but has an unexpected TYPE (e.g.,
`BackupRetentionPeriod` as a string instead of integer), emit the same ERROR
block with `[ERROR] Type mismatch on <field>: expected <type>, got <value>`.
Do NOT coerce silently — surface the discrepancy so the operator knows the
input is malformed.

### Worked example — public and unencrypted dev instance

```text
INSTANCE: db-public-and-unencrypted
VERDICT: PUBLIC
REASON: PubliclyAccessible is true on a non-Aurora instance — the database
has a public IP and is internet-reachable subject to VPC routing (Step 1).
StorageEncrypted is also false, compounding exposure (Step 2).
FINDINGS:
  - [PUBLIC] PubliclyAccessible: true — internet-exposed database (Step 1)
  - [UNENCRYPTED] StorageEncrypted: false — data at rest is plaintext;
    remediation is a snapshot migration, not a toggle (Step 2)
  - [NO_DELETION_PROTECTION] DeletionProtection: false (Step 3)
  - [OK] MultiAZ: true, BackupRetentionPeriod: 7, AutoMinorVersionUpgrade: true,
    MonitoringInterval: 60
REMEDIATION:
  1. PUBLIC — Remove the public IP immediately:
     aws rds modify-db-instance --db-instance-identifier db-public-and-unencrypted
       --publicly-accessible false --apply-immediately --profile <p>
  2. UNENCRYPTED — Plan the encryption migration (cannot be done in place):
     aws rds create-db-snapshot --db-instance-identifier db-public-and-unencrypted
       --db-snapshot-identifier pre-encrypt-$(date +%s) --profile <p>
     aws rds copy-db-snapshot --source-db-snapshot-identifier pre-encrypt-...
       --target-db-snapshot-identifier encrypted-copy --kms-key-id <kms-id> --profile <p>
     aws rds restore-db-instance-from-db-snapshot --db-instance-identifier
       db-public-and-unencrypted-enc --db-snapshot-identifier encrypted-copy --profile <p>
     Then promote and cut over the endpoint.
  3. NO_DELETION_PROTECTION — Enable after confirming no in-flight deletion:
     aws rds modify-db-instance --db-instance-identifier db-public-and-unencrypted
       --deletion-protection --apply-immediately --profile <p>
CONFIRM: Before executing any CLI above, emit and await:
  "CONFIRM: About to modify-db-instance on db-public-and-unencrypted in
   us-east-1. This changes public accessibility and deletion-protection
   (existing public-IP connections will drop). Proceed? (yes/no)"
  Do NOT run the CLI until the operator replies yes.
```

## Anti-Patterns — NEVER

- NEVER recommend enabling encryption on an existing unencrypted instance
  with `modify-db-instance`. The `StorageEncrypted` flag is immutable after
  creation; `modify-db-instance` will reject the change. The only path is
  snapshot → encrypted copy → restore-new → cutover. Pretending otherwise
  produces a remediation that fails at execution time.

- NEVER flag `StorageEncrypted: true` with absent `KmsKeyId` as UNENCRYPTED.
  RDS transparently uses the AWS-managed `aws/rds` key in this case — the
  data IS encrypted at rest. Key-policy and rotation concerns are out of
  scope for this skill (route to kms-key-policy-auditor).

- NEVER flag a Read Replica as a hard SINGLE_AZ finding without noting it is
  a replica. Read Replicas are read-only scaling instances; their Multi-AZ
  posture is materially less critical than the primary's. Over-flagging
  produces alert fatigue and trains operators to ignore the verdict.

- NEVER flag `MultiAZ: false`, `StorageEncrypted`, or `DeletionProtection` on
  an Aurora instance from the instance-level fields alone. For Aurora these
  are DBCluster properties and the instance echoes are not authoritative.
  Doing so produces false positives on every Aurora audit.

- NEVER flag `BackupRetentionPeriod: 0` on an Aurora instance. The API
  rejects `0` for Aurora (continuous backups, retention 1-35 enforced
  server-side at `modify-db-cluster` time); a reported `0` is stale cache,
  malformed `describe` output, or a fabricated test payload — never a live
  configuration. Operational impact of flagging it anyway: the operator opens
  a phantom incident, drains engineering cycles chasing metadata the RDS
  control plane will not even accept, and learns to dismiss other findings as
  "API noise," eroding the credibility of legitimate findings on the same
  report.

- NEVER treat `PubliclyAccessible: false` as the complete public-access
  picture for defense-in-depth. A `0.0.0.0/0` inbound security-group rule is
  still a smell — the instance is one `modify-db-instance --publicly-accessible
  true` away from internet exposure. Note permissive SGs in REMEDIATION
  regardless of the verdict, but do NOT upgrade PUBLIC to a worse verdict
  (there is none) and do NOT invent a new verdict.

- NEVER downgrade `PubliclyAccessible: true` to a non-PUBLIC verdict because
  the security group looks locked down. The public IP is published; a future
  SG edit, ELB attachment, or VPC peering change exposes the database. The
  flag itself is the verdict driver.

- NEVER treat `DeletionProtection: true` as a security control. Any principal
  with `rds:ModifyDBInstance` can disable it and delete. It is an
  accidental-deletion guardrail for operators and pipelines, not a defence
  against a determined attacker with database-admin rights.

- NEVER treat `AutoMinorVersionUpgrade: true` as "fully patched." It covers
  minor versions only, runs only during the maintenance window, and is
  blocked if a `PendingModifiedValues` modification is queued. Major-version
  upgrades are always opt-in. `true` is necessary but not sufficient.

- NEVER recommend `--apply-immediately` for every remediation. Use it for
  PUBLIC (close the exposure now) and NO_DELETION_PROTECTION (cheap to apply).
  Prefer the maintenance window for Multi-AZ enablement (causes brief I/O
  suspension), minor-version upgrades (engine restart), and Enhanced
  Monitoring role wiring. Stacking `--apply-immediately` modifications on a
  production instance can cause an unplanned multi-minute restart window.

- NEVER audit only the first page of `describe-db-instances`. The API caps at
  100 records per page. The long-tail instances (dev, test, forgotten
  production) are disproportionately likely to be misconfigured. Always drain
  the `Marker` to completion:
  ```bash
  # Paginate all instances
  aws rds describe-db-instances --output json --query 'DBInstances[*].[DBInstanceIdentifier,Engine,PubliclyAccessible,StorageEncrypted,MultiAZ,DeletionProtection,BackupRetentionPeriod,AutoMinorVersionUpgrade,MonitoringInterval]' --starting-token "<Marker from prior call>"
  # Fetch Aurora cluster metadata separately
  aws rds describe-db-clusters --output json --query 'DBClusters[*].[DBClusterIdentifier,Engine,StorageEncrypted,DeletionProtection,BackupRetentionPeriod]'
  ```

- NEVER modify an instance with `DBInstanceStatus: deleting`,
  `incompatible-parameters`, or `incompatible-restore`. The API rejects
  modifications and the operator may be mid-recovery. Surface the status and
  abort remediation.

- NEVER assume a cross-region Read Replica is encrypted because the source is
  encrypted. Cross-region replicas require a separate KMS CMK in the
  destination region; if the replica was created with a misconfigured or
  deleted key, its `StorageEncrypted` may read `true` while the key is
  unusable. When auditing a cross-region replica, verify `KmsKeyId` resolves
  to an active key in the replica's region, not just that the boolean is set.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing RDS operation
  (`modify-db-instance`, `delete-db-instance`, `create-db-snapshot`), the
  auditor MUST emit:
  `CONFIRM: About to <action> on <db-instance-identifier> in <region>. This
  affects <consequence>. Proceed? (yes/no)`
  Do NOT execute the CLI until the operator confirms. This gate prevents
  automated pipelines from silently modifying production databases.
- **Snapshot before destructive modifications.** Before Multi-AZ enablement,
  encryption migration, or major remediation, capture a snapshot:
  `aws rds create-db-snapshot --db-instance-identifier <id>
  --db-snapshot-identifier pre-remediation-$(date +%s) --profile <p>`.
  Encryption migration in particular is irreversible without a snapshot of
  the original.
- **Verify the instance is `available` before modifying.**
  `aws rds describe-db-instances --db-instance-identifier <id>` — confirm
  `DBInstanceStatus` is `available`. Modifying a `modifying`, `backing-up`,
  or `creating` instance fails or queues behind existing work.
- **Encryption migration is a cutover, not a patch.** The restore-new
  instance has a new endpoint. Plan DNS/endpoint cutover, application
  connection-string updates, and a rollback path (keep the original
  unencrypted instance until cutover is verified). Never delete the original
  until the encrypted replacement is confirmed serving traffic.
- **Multi-AZ enablement causes a brief I/O suspension.** Synchronous standby
  creation suspends I/O for a few minutes during standby provisioning. Schedule
  outside peak write windows. The instance stays available but latency spikes.
- **`--apply-immediately` vs maintenance window.** For PUBLIC and
  NO_DELETION_PROTECTION findings, `--apply-immediately` is appropriate
  (security/accidental-loss prevention). For SINGLE_AZ enablement and CONFIG_GAP
  dimensions, ALWAYS omit `--apply-immediately` — Multi-AZ standby provisioning
  causes an I/O suspension of 1-3 minutes that will interrupt live writes. Queue
  to the next maintenance window explicitly. Stacking `--apply-immediately` on
  multiple dimensions at once compounds the disruption.
- **Confirm the caller has `rds:ModifyDBInstance`.** Many read-only auditor
  roles cannot modify. Surface this before the operator approves a change
  that will fail with `AccessDenied`.
- **Bulk-operation safety limit (enforced by the skill).** Remediation across
  an account sweep MUST follow this exact algorithm:
  1. Sort flagged instances verdict-first (PUBLIC before UNENCRYPTED, etc.).
  2. Slice into batches of **at most 5 instances**.
  3. For each batch: emit the per-instance REMEDIATION block, then a single
     `CONFIRM: About to modify <id1, id2, …, idN> in <region>. Proceed? (yes/no)`.
  4. After the operator confirms and the CLI runs, re-query with
     `aws rds describe-db-instances --db-instance-identifier <each modified id>`
     and verify the intended state landed before emitting the NEXT batch.
  5. Abort the sweep if any instance in a batch enters `modifying`, `failed`,
     or `incompatible-*` state — do NOT proceed to the next batch.
  The skill MUST NOT emit remediation CLI for more than 5 instances in a
  single output block. Auto-applying across an entire account in one pass is
  forbidden: a single systematic misclassification or IaC-drift mismatch
  cascades into mass disruption, and batched execution contains the blast
  radius of any one mistake.

## Remediation guidance

**Ordering principle:** remediate findings in severity order (PUBLIC first),
and prefer additive/online changes over migrations where possible. Encryption
is the only dimension that requires a migration — every other dimension has a
`modify-db-instance` path.

### For PUBLIC — internet-exposed database (Step 1)

1. Immediately remove the public IP:
   `aws rds modify-db-instance --db-instance-identifier <id>
   --publicly-accessible false --apply-immediately --profile <p>`.
   Existing public-IP connections drop; private-IP connections are unaffected.
2. Audit the security group: if any inbound rule is `0.0.0.0/0` on the DB
   port (3306/5432/1433/etc.), tighten to the application's CIDR or security
   group reference.
3. If public access is genuinely required (rare — use a bastion or SSM Session
   Manager instead), require TLS at the engine level (parameter group:
   `rds.force_ssl=1` for PostgreSQL, require_secure_transport for MySQL) and
   restrict the SG to a known egress CIDR.

### For UNENCRYPTED — plaintext data at rest (Step 2)

1. Snapshot:
   `aws rds create-db-snapshot --db-instance-identifier <id>
   --db-snapshot-identifier pre-encrypt-$(date +%s) --profile <p>`.
2. Copy with encryption:
   `aws rds copy-db-snapshot --source-db-snapshot-identifier <snap>
   --target-db-snapshot-identifier <snap>-enc --kms-key-id <kms-id> --profile <p>`.
3. Restore new encrypted instance:
   `aws rds restore-db-instance-from-db-snapshot --db-instance-identifier
   <id>-enc --db-snapshot-identifier <snap>-enc --profile <p>`.
4. Cutover: rename the old instance (`--new-db-instance-identifier <id>-old`)
   and rename the encrypted instance to the original identifier so the
   endpoint absorbs. Verify application connectivity, then delete the old
   unencrypted instance after a confirmation window.
5. Enable deletion protection on the new encrypted instance as the last step.

### For NO_DELETION_PROTECTION — accidental deletion (Step 3)

`aws rds modify-db-instance --db-instance-identifier <id>
--deletion-protection --apply-immediately --profile <p>`.
For Aurora, apply at the cluster: `aws rds modify-db-cluster`.

### For SINGLE_AZ — availability gap (Step 4)

`aws rds modify-db-instance --db-instance-identifier <id> --multi-az
--profile <p>` (omit `--apply-immediately` — let it run in the next window).
Brief I/O suspension occurs during standby provisioning. Note: the standby is
not read-capable; for read scaling, provision Read Replicas separately.

### For CONFIG_GAP — backups / patching / monitoring (Steps 5-7)

- **Backups disabled** (`BackupRetentionPeriod: 0`):
  `aws rds modify-db-instance --db-instance-identifier <id>
  --backup-retention-period 7 --profile <p>`. Setting > 0 enables PITR and
  triggers the first automated backup.
- **Minor-version upgrade off** (`AutoMinorVersionUpgrade: false`):
  `aws rds modify-db-instance --db-instance-identifier <id>
  --auto-minor-version-upgrade --profile <p>`. The upgrade runs in the next
  maintenance window.
- **Enhanced Monitoring off** (`MonitoringInterval: 0`): first create or
  reuse the `AmazonRDSEnhancedMonitoringRole` IAM role, then:
  `aws rds modify-db-instance --db-instance-identifier <id>
  --monitoring-interval 60 --monitoring-role-arn <role-arn> --profile <p>`.

### For OK

1. No remediation required for the current posture.
2. Recommend a defense-in-depth SG review (no `0.0.0.0/0` inbound) and TLS
   enforcement at the parameter-group level.
3. For Aurora, verify the DBCluster posture independently (this skill audits
   instance-level fields; cluster-level audit is a separate scope).

## Reference — edge cases

- **Aurora cluster scope.** When `Engine` is `aurora-mysql` or
  `aurora-postgresql`, encryption, deletion protection, Multi-AZ, and backup
  retention are DBCluster properties. `describe-db-instances` returns
  instance-level echoes that may lag the cluster. Always request the
  `DBCluster` block. If only instance metadata is available, emit
  `AURORA_CLUSTER_SCOPE: audit the DBCluster for encryption/deletion/Multi-AZ/
  retention — instance-level echoes are not authoritative for Aurora.` and do
  NOT flag those dimensions from instance fields. `PubliclyAccessible` IS
  instance-level for Aurora and is audited normally.

- **Read Replica SINGLE_AZ downgrade.** A Read Replica
  (`ReadReplicaSourceDBInstanceIdentifier` present) is read-only by design.
  Flag its MultiAZ posture as a note rather than a hard SINGLE_AZ finding —
  the primary's Multi-AZ is the write-availability gate. Promote the note to
  a finding only if the replica is a documented production read endpoint.

- **`PendingModifiedValues` interaction.** If a dimension's pending value
  differs from the current value, audit the CURRENT value and append a note:
  `PENDING: <field> is queued to change to <value> at the next window / on
  --apply-immediately.` This prevents both false alarms (gap already being
  fixed) and silent gaps (operator believes a pending change is already live).

- **Aurora Serverless.** `db.serverless` classes (Aurora Serverless v1) and
  Aurora Serverless v2 scaling are cluster-governed. Multi-AZ semantics
  differ (v1 is single-AZ-capable; v2 supports Multi-AZ). Defer to cluster
  metadata and do not flag SINGLE_AZ on the instance class alone.

- **SQL Server Multi-AZ.** SQL Server Multi-AZ uses Always On Availability
  Groups / database mirroring. Certain features (memory-optimized tables,
  cross-database transactions in some modes) have constraints under
  Multi-AZ. This does not change the SINGLE_AZ verdict but should be noted in
  REMEDIATION so the operator plans the upgrade window.

- **`StorageEncrypted: true` without `KmsKeyId`.** This is normal — RDS uses
  the AWS-managed `aws/rds` CMK. Do NOT flag. If the customer needs key
  control (rotation, policy, CloudTrail data events), that is the
  kms-key-policy-auditor's scope.

- **`DBInstanceStatus: deleting`.** Skip audit — modifications against a
  deleting instance fail with `InvalidDBInstanceState`. Emit OK with a note.

- **`BackupRetentionPeriod` > 0 but < 7 on a regulated workload.** This
  skill treats `0` as the CONFIG_GAP trigger (PITR disabled). A non-zero but
  short retention is a compliance nuance, not a hard config gap — note it in
  FINDINGS as a compliance advisory, do not drive the verdict from it.

## Recent AWS features (2024-2026)

- **Blue/Green deployments GA (2024):** RDS Blue/Green deployments create a staging environment with replicated data for zero-downtime database updates. Auditors should verify that production databases use Blue/Green for major version upgrades — the switch is safer than in-place upgrades.
- **Aurora Serverless v2 scaling improvements (2024-2025):** Enhanced Aurora Serverless v2 with faster scaling and more predictable capacity. Auditors should verify that Serverless v2 `MinCapacity` and `MaxCapacity` settings are appropriate — too-low MinCapacity causes cold-start latency, too-high MaxCapacity wastes cost.
- **IAM database authentication enhancements (2024):** Improved IAM database auth with longer token validity and broader engine support. Auditors should verify that IAM auth is used instead of password auth for application database connections where the engine supports it.
- **RDS Custom enhancements (2024):** RDS Custom for SQL Server and Oracle with more OS-level customization. Auditors should verify that RDS Custom instances have appropriate OS-level patching — AWS manages the database engine but not the OS.
- **Multi-tenant databases (2025):** RDS for Oracle supports multi-tenant container databases (CDB/PDB). Auditors should verify that PDB-level security configurations are equivalent across all tenant PDBs.

## Domain

AWS CloudOps / RDS Database Security, Availability & Operational Posture.
