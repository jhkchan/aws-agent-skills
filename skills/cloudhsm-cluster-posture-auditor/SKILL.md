---
name: cloudhsm-cluster-posture-auditor
description: Audits AWS CloudHSM clusters for high-availability posture (HSM count and cross-AZ distribution), backup/restore readiness (retention policy, backup recency, restorability), PKCS#11 user management (default CO password, quorum), cluster initialization (certificate signing chain), and subnet/ security-group network exposure. Emits a deterministic verdict (SINGLE_AZ | NO_BACKUP | CONFIG_GAP | OK) per cluster with enumerated findings and specific remediation. Use when reviewing CloudHSM cluster configuration, checking HA readiness, validating backup posture, auditing PKCS#11 user hygiene, or hardening HSM security before production deployment.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline cluster-config classification. Live-account audits use aws cloudhsm describe-clusters, aws cloudhsm describe-backups, and cloudhsm_mgmt_util (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Security
  verdict_shape: SINGLE_AZ | NO_BACKUP | CONFIG_GAP | OK
  when_to_use: Reviewing a CloudHSM cluster before production deployment, checking HA readiness across availability zones, validating backup posture and retention, auditing PKCS#11 user management, inspecting cluster initialization state, or hardening HSM network exposure.
  activation_triggers: audit this CloudHSM cluster, check CloudHSM HA posture, is my CloudHSM cluster highly available, CloudHSM backup readiness, CloudHSM PKCS#11 user audit, CloudHSM single AZ risk, CloudHSM cluster initialized, harden CloudHSM cluster
  invocation_schema: 'Input: either (a) a CloudHSM cluster configuration (describe-clusters output plus PKCS#11 management metadata), optionally paired with backup details, OR (b) a cluster-id for live-account audit. Output: deterministic CLUSTER/VERDICT/REASON/FINDINGS/REMEDIATION block per cluster, where VERDICT is one of SINGLE_AZ, NO_BACKUP, CONFIG_GAP, OK, or ERROR.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: CloudHSM, cluster posture, high availability, HSM, PKCS#11, backup, cross-AZ, single-AZ, certificate signing, InitializeCluster, Crypto Officer, CO password, quorum, subnet routing, security group, FIPS 140-2, key management, hardware security module, backup retention, cluster initialization
  tags: cloudhsm, security, ha, backup, pkcs11, hsm, fips, audit
---

# CloudHSM Cluster Posture Auditor

## Mindset

**One-line takeaway:** the verdict is always the **worst** finding across
all dimensions, ordered SINGLE_AZ > NO_BACKUP > CONFIG_GAP > OK. The most
common — and most dangerous — misjudgment is treating HSM count as a proxy
for high availability: three HSMs in a single AZ provide HSM-level
redundancy but zero AZ-level redundancy.

AWS CloudHSM provides single-tenant FIPS 140-2 Level 3 HSM instances. A
cluster is the management boundary — it groups HSMs, backups, and the
certificate trust chain. Three properties make CloudHSM uniquely fragile
compared to other AWS services:

- **HSMs are stateful and single-tenant.** Unlike EC2 or RDS, you cannot
  "just restart" an HSM. If an HSM fails, its key material survives only
  in backups and in the other HSMs that were synchronised before the failure.
- **Backups are the ONLY recovery path.** CloudHSM has no snapshots, no
  automated cross-region replication, and no recycle bin. A cluster with no
  backups that loses all HSMs is permanently unrecoverable — every key is
  lost forever.
- **Cluster initialization is a trust anchor.** The signed certificate
  uploaded during InitializeCluster is how clients verify the HSM's
  identity. An uninitialized cluster is physically present but
  cryptographically unreachable — clients will refuse to connect.

## Quick reference — verdict thresholds

| Condition | Verdict | Step |
|---|---|---|
| All HSMs in a single AZ (regardless of HSM count) | **SINGLE_AZ** | Step 1 |
| Fewer than 2 distinct AZs represented across ACTIVE HSMs | **SINGLE_AZ** | Step 1 |
| BackupRetentionPolicy Type=DAYS Value=0 (or absent) | **NO_BACKUP** | Step 2 |
| Zero backups exist | **NO_BACKUP** | Step 2 |
| Most recent backup >7 days old | **NO_BACKUP** | Step 2 |
| Cluster State=UNINITIALIZED (no signed certificate) | **CONFIG_GAP** | Step 3 |
| Default CO password unchanged | **CONFIG_GAP** | Step 3 |
| Security group allows 0.0.0.0/0 on ports 2223-2225 | **CONFIG_GAP** | Step 3 |
| 2+ HSMs across 2+ AZs, recent backups, clean config | **OK** | Step 4 |

Verdict precedence: SINGLE_AZ > NO_BACKUP > CONFIG_GAP > OK (worst finding
wins).

## Pre-flight: cluster metadata gate

Before evaluating the cluster posture, classify the cluster itself.

**Multi-cluster / account-wide sweep note:** `aws cloudhsm describe-clusters`
returns all clusters in the region (no pagination needed for the cluster
list itself). For each cluster, call `aws cloudhsm describe-backups
--cluster-id <id>` — backups are paginated at 50 per page, so use
`--next-token` to drain the full list.

| Attribute | Value | Effect on audit |
|---|---|---|
| `State` | `UNINITIALIZED` | **Cluster not initialized.** Jump to Step 3 — this is always at least CONFIG_GAP. Clients cannot connect. |
| `State` | `INITIALIZED` | Proceed with full audit. |
| `State` | `CREATE_IN_PROGRESS` | Output: `VERDICT: ERROR, REASON: Cluster creation in progress — re-audit when State is UNINITIALIZED or INITIALIZED.` |
| `State` | `DELETE_IN_PROGRESS` | Output: `VERDICT: ERROR, REASON: Cluster is being deleted — no posture audit applicable.` |
| `State` | `DEGRADED` | One or more HSMs are degraded. Still audit all dimensions; add a DEGRADED note. |
| `HsmType` | `hsm1m.medium` / `hsm2m.medium` | Note the type — it is immutable after cluster creation. Flag older types as a migration-planning note, not a security verdict. |
| HSM `State` | Any non-`ACTIVE` | Exclude from effective cross-AZ count. If this drops the AZ count below 2, escalate to SINGLE_AZ. |

**If the cluster configuration is malformed** (missing HSM list, missing
SubnetMapping, invalid State), output:

```text
CLUSTER: <cluster-id>
VERDICT: ERROR
REASON: Cluster configuration is incomplete or malformed — cannot classify.
REMEDIATION: Retrieve the canonical config with `aws cloudhsm describe-clusters --cluster-id <id> --output json` and re-audit.
```

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious CloudHSM behaviors that change classification

These behaviors are easy to misjudge without operational CloudHSM experience.
Each changes a verdict if ignored:

- **HSM count is NOT a proxy for HA.** Three HSMs in a single AZ provide
  HSM-level redundancy (one HSM can fail without data loss) but ZERO
  AZ-level redundancy. An AZ failure — network partition, power loss, or
  AWS infrastructure event — takes down ALL co-located HSMs simultaneously.
  The audit must check `AvailabilityZone` distribution across HSMs, not
  just HSM count.

- **BackupRetentionPolicy Type=DAYS Value="0" silently disables backups.**
  Value=0 means backups are immediately eligible for deletion. The cluster
  will report zero backups even though the backup mechanism technically
  exists at the API level. This is the CloudHSM equivalent of setting S3
  lifecycle expiration to 0 — the setting exists but accomplishes the
  opposite of data protection.

- **An UNINITIALIZED cluster is physically present but cryptographically
  unreachable.** The cluster's HSMs may report ACTIVE state, but clients
  cannot establish a trust link without the signed certificate from
  InitializeCluster. This is not a transient state — it persists until an
  operator explicitly downloads the cluster CSR, signs it with their CA,
  and uploads the signed certificate plus full CA trust chain.

- **The default Crypto Officer (CO) password is a well-known credential.**
  Set during InitializeCluster, the default password is documented in AWS
  CloudHSM user guides. Any attacker who can reach the NTLS port (2224)
  from within the VPC can authenticate as CO and manage keys, users, and
  policies. It MUST be changed as the first post-initialization action.

- **KMS Custom Key Store coupling is invisible but critical.** When a
  CloudHSM cluster is linked as a KMS Custom Key Store, all KMS
  Encrypt/Decrypt/GenerateDataKey calls proxy through the cluster's HSMs.
  A single-AZ cluster used as a custom key store causes intermittent KMS
  failures during AZ events — and because KMS returns generic
  `KMSInternalException`, the root cause is non-obvious. Always check if
  the cluster is a KMS custom key store and flag single-AZ as elevated
  operational risk in that context.

- **CloudHSM ports 2223-2225 carry data and management traffic.** Port
  2223 is the PKCS#11 library interface, 2224 is NTLS (client management
  and crypto operations), and 2225 is the performance/monitoring channel.
  The HSMs expose Elastic Network Interfaces (ENIs) in the cluster's
  subnets. A security group allowing 0.0.0.0/0 on these ports exposes
  the HSM management interface to any entity with VPC network reachability.

- **Backups are point-in-time, not continuous.** CloudHSM creates backups
  on a periodic schedule and on-demand (CreateBackup). Data written to the
  HSM AFTER the last backup is lost if all HSMs fail before the next
  backup. The 7-day recency threshold is the practical maximum for
  production — beyond that, any keys created or rotated since the backup
  are unrecoverable.

- **DeleteCluster requires all HSMs to be deleted first.** This is a safety
  gate, not a limitation — it prevents accidental cluster deletion with
  active HSMs. When auditing a cluster scheduled for deletion, verify that
  all HSMs have been individually deleted via DeleteHsm first.

- **HSM type is immutable after cluster creation.** `hsm1m.medium` vs
  `hsm2m.medium` is set at CreateCluster time. To change the type, you must
  create a new cluster, restore from backup, and migrate clients — a
  multi-hour maintenance window. This is relevant when auditing a cluster
  with an older HSM type approaching end-of-support.

- **Quorum authentication (M-of-N) is optional but recommended for
  production.** CloudHSM supports requiring M of N Crypto Officers to
  approve sensitive operations (user deletion, key deletion, policy
  changes). Without quorum, a single compromised CO can destroy all keys.
  The absence of quorum is a CONFIG_GAP in regulated environments.

- **Cluster certificates require the FULL CA chain.** The certificate
  uploaded during InitializeCluster must include the complete chain (leaf
  to intermediate to root). A partial chain causes client connection
  failures that are difficult to diagnose because the error references
  "trust" without specifying which certificate link is missing.

- **Restoring a backup creates a NEW cluster with a different cluster ID.**
  The original cluster ARN is NOT preserved across a restore. All client
  applications, KMS custom key store links, and monitoring configurations
  that reference the original cluster ID must be re-pointed to the new
  cluster after restore. A DR plan that assumes "restore in place" without
  updating references will silently fail.

- **New HSMs spend 5-20 minutes in CREATE_IN_PROGRESS replicating keys**
  from existing HSMs before reaching ACTIVE state. During this window, the
  HSM is NOT serving client traffic and does NOT count toward HA. An
  operator who adds a cross-AZ HSM and immediately removes the old one
  creates a temporary HA gap — always wait for ACTIVE confirmation via
  `describe-clusters` before rebalancing.

- **BackupRetentionPolicy Type=DAYS vs Type=COUNT have different safety
  properties.** DAYS auto-deletes backups older than the threshold
  regardless of how many remain — if the backup schedule is disrupted,
  the cluster can reach zero valid backups within the retention window.
  COUNT guarantees a minimum number of restorable points regardless of
  schedule gaps. For production, COUNT is the safer default; for
  compliance with time-based retention mandates, use DAYS.

- **The cluster SecurityGroup is immutable at the CloudHSM API level.**
  There is no `ModifyCluster --security-group` API. To change the security
  group rules, you modify the security group itself via the EC2 API
  (`aws ec2 authorize-security-group-ingress`). The HSM ENIs inherit the
  group from the cluster at creation time and cannot be re-attached to a
  different group without recreating the HSM.

### Step 1: Cluster HA / AZ distribution (highest priority — SINGLE_AZ)

For each ACTIVE HSM in the cluster, extract `AvailabilityZone`. Classify:

- **SINGLE_AZ** — All ACTIVE HSMs reside in the same AZ, OR fewer than 2
  distinct AZs are represented. This is the worst verdict because an
  AZ-level event (power, network, cooling) takes down the entire cluster
  simultaneously.

- **OK for HA** — ACTIVE HSMs span 2+ distinct AZs. The minimum for HA is
  2 HSMs in 2 distinct AZs. AWS recommends 3 HSMs in 3 AZs for production
  (provides quorum-based recovery and tolerates a full-AZ failure with no
  data loss).

**HSM state interaction:** exclude any HSM in a non-ACTIVE state
(DEGRADED, CREATE_IN_PROGRESS) from the effective AZ count before
evaluating this step. A cluster with 3 HSMs across 3 AZs where one HSM is
DEGRADED has an effective count of 2 AZs — still HA, but the degraded HSM
should be noted as an operational risk.

**Single-HSM special case:** a cluster with exactly 1 HSM is ALWAYS
SINGLE_AZ, regardless of the AZ or subnet configuration. A single HSM is
a single point of failure for both HSM-level and AZ-level redundancy.

### Step 2: Backup posture (NO_BACKUP)

Evaluate backup readiness across three sub-dimensions. ANY failure
produces NO_BACKUP:

- **Retention policy:** If `BackupRetentionPolicy.Type` is `DAYS` and
  `Value` is `"0"`, OR the policy is absent entirely, backups are
  effectively disabled. Even if some backups exist from before the policy
  change, they are orphans with no retention guarantee and will be
  auto-deleted.

- **Backup count:** If zero backups exist in the cluster's backup list
  (from `aws cloudhsm describe-backups --cluster-id <id>`), there is no
  recovery path. All key material, users, and policies are irrecoverable
  if the cluster fails.

- **Backup recency:** If the most recent backup (by `CreateDate`) is more
  than 7 days old, the backup posture is effectively stale. CloudHSM
  creates backups automatically on a periodic schedule, and a gap >7 days
  indicates the backup mechanism is broken or the retention policy is
  aggressively deleting backups before new ones complete.

**Expert note — retention calibration:** the default retention is 90 days
(Type=DAYS, Value=90). This is adequate for operational recovery but may
be insufficient for compliance frameworks requiring 1-year or 7-year
retention. When auditing for compliance, compare the retention period
against the framework's requirement and flag as CONFIG_GAP if shorter.

### Step 3: Configuration posture (CONFIG_GAP)

Evaluate cluster configuration across four sub-dimensions. Each failure
produces a CONFIG_GAP finding:

**3a. Cluster initialization:**
If `State` is `UNINITIALIZED`, the cluster has not been initialized.
Clients cannot connect. The InitializeCluster step (download CSR, sign
with CA, upload signed cert plus trust chain) has not been completed.
This is always CONFIG_GAP.

**3b. PKCS#11 user management — default CO password:**
If the default Crypto Officer password has not been changed (the operator
confirms `co_password_changed: false`, or the password change timestamp
matches/predates the cluster initialization date), the cluster is using a
well-known credential. This is CONFIG_GAP. There is no AWS API to verify
password state — rely on operator-provided metadata.

**3c. Security group exposure:**
If the cluster's security group allows inbound from `0.0.0.0/0` on any
CloudHSM port (2223-2225), the HSM management and data interfaces are
exposed to any network-reachable entity. This is CONFIG_GAP. The correct
posture is to allow inbound only from the application subnet CIDR or a
specific client security group.

**3d. Quorum / M-of-N authentication (regulated environments):**
If quorum is not enabled for sensitive CO operations (user deletion, key
deletion, policy modification) in a regulated environment, flag as
CONFIG_GAP. Quorum is configured client-side via `cloudhsm_mgmt_util`.

### Step 4: Aggregation — worst finding wins

The final verdict is the **maximum severity** across all dimensions, where
SINGLE_AZ > NO_BACKUP > CONFIG_GAP > OK:

```text
verdict = max(ha_finding, backup_finding, config_finding)
```

If no findings (all dimensions pass), the verdict is **OK**.

## Output format (per cluster)

```text
CLUSTER: <cluster-id>
VERDICT: SINGLE_AZ | NO_BACKUP | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its step>
FINDINGS:
  - [SINGLE_AZ] <finding description (Step 1)>
  - [NO_BACKUP] <finding description (Step 2)>
  - [OK] <dimension that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — single-AZ cluster with no backup

```text
CLUSTER: cluster-single-az-demo
VERDICT: SINGLE_AZ
REASON: All 1 HSMs reside in a single AZ (us-east-1a) — an AZ-level event
takes the entire cluster offline with no cross-AZ failover. Backup retention
is also disabled (Type=DAYS, Value=0), compounding the risk with no recovery
path.
FINDINGS:
  - [SINGLE_AZ] 1 HSM in us-east-1a only — no AZ-level redundancy (Step 1)
  - [NO_BACKUP] BackupRetentionPolicy DAYS=0 — backups disabled (Step 2)
REMEDIATION:
  1. Add HSMs in at least one additional AZ: aws cloudhsm create-hsm
     --cluster-id <id> --availability-zone us-east-1b --subnet-id <subnet-b>.
  2. Set backup retention: modify-backup-attributes with Type=DAYS,Value=90.
  3. Create an immediate backup: aws cloudhsm create-backup --cluster-id <id>.
```

## Edge-case handling

- **Cluster with HSMs in DEGRADED state.** Exclude DEGRADED HSMs from the
  effective AZ count. If the remaining ACTIVE HSMs span 2+ AZs, the HA
  verdict is OK but emit a DEGRADED note. If the remaining ACTIVE HSMs
  are all in 1 AZ, escalate to SINGLE_AZ.

- **Cluster used as KMS Custom Key Store.** If the cluster is linked to KMS
  (check via `aws kms describe-custom-key-stores`), a SINGLE_AZ verdict
  should include an additional operational risk note: "This cluster is a
  KMS Custom Key Store. Single-AZ posture will cause intermittent KMS
  Encrypt/Decrypt failures (KMSInternalException) during AZ events."

- **Cluster with 2 AZs (minimum HA).** Two HSMs in two AZs meets the
  minimum HA threshold. Note that this tolerates a single HSM or AZ
  failure but does NOT provide quorum-based recovery (which requires 3
  HSMs). Recommend 3 AZs for production in the REMEDIATION field.

- **Recently created cluster (no backups yet).** A cluster created less
  than 1 hour ago may legitimately have zero backups if the first scheduled
  backup has not yet executed. If the cluster age is under 1 hour AND
  BackupRetentionPolicy is properly configured (DAYS >= 7), do NOT flag
  NO_BACKUP — emit a note: "Cluster recently created — first backup
  pending."

- **Backup in CREATE_IN_PROGRESS state.** A backup that is not yet in
  READY state should not be counted as a valid recovery point. Exclude it
  from the backup count and recency checks.

## Anti-Patterns — NEVER

- NEVER treat HSM count as sufficient for HA. Three HSMs in a single AZ
  is SINGLE_AZ — the AZ is the failure domain, not the individual HSM. A
  single power or network event in that AZ destroys all three HSMs
  simultaneously. Always check AZ distribution.

- NEVER classify a cluster with zero backups as OK. Without a backup,
  total cluster failure means permanent, unrecoverable key-material loss.
  CloudHSM has no snapshot, no recycle bin, and no automated cross-region
  replication. The backup is the ONLY recovery path.

- NEVER assume BackupRetentionPolicy Type=DAYS Value=0 means "keep
  forever." It means the opposite — backups are immediately eligible for
  deletion. This is one of the most dangerous CloudHSM misconfigurations
  because it looks like a valid retention policy.

- NEVER treat an UNINITIALIZED cluster as production-ready. The HSMs may
  report ACTIVE state, but without the signed certificate from
  InitializeCluster, clients cannot establish the NTLS trust link. The
  cluster is cryptographically unreachable.

- NEVER leave the default CO password in place for production. It is a
  documented credential — any principal with VPC network access to port
  2224 can authenticate as Crypto Officer and manage all keys. The
  password change is the first post-initialization action.

- NEVER expose CloudHSM ports 2223-2225 to 0.0.0.0/0. These ports carry
  PKCS#11 data-plane traffic (2223), NTLS management (2224), and
  monitoring (2225). An open security group lets any network-reachable
  client attempt HSM authentication — the default CO password combined
  with an open SG is a full compromise path.

- NEVER ignore backup recency. A backup from 30 days ago is marginally
  better than no backup, but any keys created or rotated since then are
  unrecoverable. The 7-day threshold is the practical maximum for
  production; beyond that, the backup is dangerously stale.

- NEVER assume a cluster in DEGRADED state has the same HA posture as
  one with all ACTIVE HSMs. A DEGRADED HSM may not be synchronizing key
  material — exclude it from the effective AZ count when evaluating Step 1.

- NEVER recommend deleting a cluster without verifying it is not linked
  as a KMS Custom Key Store. Deleting a backing cluster causes all KMS
  operations on that custom key store to fail permanently. Always check
  `aws kms describe-custom-key-stores` before recommending deletion.

- NEVER recommend changing the HSM type (hsm1m.medium to hsm2m.medium) as
  an in-place remediation. The type is immutable — the only path is
  create-new-cluster, restore-from-backup, migrate-clients, which is a
  multi-hour maintenance window.

- NEVER assume BackupRetentionPolicy Type=DAYS guarantees a minimum number
  of restorable backups. DAYS deletes by age, not by count — if the backup
  schedule is disrupted, the cluster can reach zero valid backups within
  the retention window. Use Type=COUNT to guarantee N restorable points
  regardless of schedule gaps, or monitor backup creation alerts to catch
  schedule disruptions early.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (CreateHsm, DeleteHsm, DeleteCluster, InitializeCluster,
  ModifyBackupAttributes, CreateBackup, DeleteBackup), the auditor MUST
  emit: `CONFIRM: About to <action> on cluster <id>. This affects
  <consequence>. Proceed? (yes/no)`. Do NOT execute until the operator
  confirms.

- Confirm the cluster exists and is accessible:
  `aws cloudhsm describe-clusters --cluster-id <id> --profile <p>` —
  fail closed (skip remediation) if it returns an error.

- Before modifying backup retention, snapshot the current backup list:
  `aws cloudhsm describe-backups --cluster-id <id> --output json >
  /tmp/<id>-backups-$(date +%s).json`. This documents what was restorable
  before the change.

- Before adding an HSM to a cluster, verify the target subnet exists and
  has available ENI capacity — each HSM consumes one ENI in its subnet.

- Before initializing a cluster, verify the signed certificate includes
  the FULL CA chain (leaf, intermediate, root). A partial chain causes
  cryptic client connection failures.

- For SINGLE_AZ findings on a KMS Custom Key Store cluster, treat as
  incident-response — add cross-AZ HSMs immediately. KMS operations are
  silently failing during AZ events.

- Prefer additive changes (add HSMs, add backups) over destructive changes
  (delete HSMs, delete backups). Additive changes do not risk existing key
  material or recovery points.

## Remediation guidance

### For SINGLE_AZ

1. Add HSMs in additional AZs to achieve cross-AZ distribution:
   `aws cloudhsm create-hsm --cluster-id <id> --availability-zone <az>
   --subnet-id <subnet-id>`.
2. Target 3 HSMs across 3 AZs for production — provides quorum-based
   recovery and tolerates a full-AZ failure with no data loss.
3. If the cluster is a KMS Custom Key Store, this is elevated operational
   risk — KMS Encrypt/Decrypt calls will fail during AZ events with
   KMSInternalException.
4. After adding HSMs, verify they reach ACTIVE state and synchronise keys
   from existing HSMs before considering HA achieved.

### For NO_BACKUP

1. Set a proper backup retention policy using
   `aws cloudhsm modify-backup-attributes` with Type=DAYS, Value=90.
2. Create an immediate on-demand backup:
   `aws cloudhsm create-backup --cluster-id <id>`.
3. If the most recent backup is stale (>7 days), investigate why scheduled
   backups are not being created. Common cause: retention Value=0 auto-
   deleting backups faster than they are created.
4. For compliance frameworks requiring longer retention, increase Value
   accordingly (e.g., 365 for annual retention).

### For CONFIG_GAP — uninitialized cluster

1. Download the cluster CSR from `describe-clusters` output
   (`Certificates.ClusterCsr`).
2. Sign the CSR with your issuing CA (or self-sign for testing):
   `openssl x509 -req -in cluster.csr -CA ca.crt -CAkey ca.key
   -CAcreateserial -out signed.crt -days 365`.
3. Upload the signed certificate and trust anchor:
   `aws cloudhsm initialize-cluster --cluster-id <id>
   --signed-cert fileb://signed.crt --trust-anchor fileb://ca.crt`.
4. After initialization, immediately change the default CO password via
   `cloudhsm_mgmt_util`.

### For CONFIG_GAP — default CO password unchanged

1. Connect to the HSM using cloudhsm_mgmt_util with the cluster config.
2. Log in with the default CO credentials.
3. Change the password using `changePswd CO admin <new-password>`.
4. Verify by logging out and back in with the new password.

### For CONFIG_GAP — open security group

1. Identify the security group(s) attached to the cluster's HSM ENIs.
2. Remove the 0.0.0.0/0 inbound rule on ports 2223-2225.
3. Add a scoped inbound rule allowing only the application subnet CIDR or
   client security group on ports 2223-2225.
4. Verify client connectivity from the application tier.

### For OK

1. No remediation required for the current posture.
2. Recommend enabling quorum authentication for regulated environments.
3. Recommend 3 HSMs across 3 AZs if currently at the 2-AZ minimum.
4. Verify backup restore readiness by periodically performing a test
   restore to a staging cluster.

## AWS documentation

- **AWS CloudHSM User Guide** — https://docs.aws.amazon.com/cloudhsm/latest/userguide/introduction.html
- **CloudHSM Security** — https://docs.aws.amazon.com/cloudhsm/latest/userguide/cloudhsm-security.html
- **CloudHSM API Reference** — https://docs.aws.amazon.com/cloudhsm/latest/APIReference/
- **AWS CLI Command Reference (CloudHSM)** — https://docs.aws.amazon.com/cli/latest/reference/cloudhsm/
- **CloudHSM cluster management** — https://docs.aws.amazon.com/cloudhsm/latest/userguide/clusters.html
- **CloudHSM backups** — https://docs.aws.amazon.com/cloudhsm/latest/userguide/backups.html

## Recent AWS features (2024-2026)

- **CloudHSM hsm2m.medium GA (2024):** The next-generation HSM type
  `hsm2m.medium` is now GA, offering improved performance and memory.
  Auditors should note the HSM type and flag `hsm1m.medium` clusters as a
  migration-planning item (the type is immutable; migration requires
  create-new-cluster, restore-from-backup, and client migration).
- **Cross-region backup copy (2024-2025):** AWS introduced the ability to
  copy CloudHSM backups across regions for disaster recovery. Auditors
  should verify that production clusters in multi-region architectures
  have cross-region backup copies for DR readiness.
- **Enhanced CloudTrail logging (2024):** CloudHSM now emits additional
  CloudTrail events for HSM-level operations (user creation, key
  generation, policy changes). Auditors should verify CloudTrail is logging
  CloudHSM management events for forensic readiness.
- **Backup retention policy enhancements (2025):** BackupRetentionPolicy
  now supports both DAYS-based and COUNT-based retention. COUNT-based
  retention guarantees a minimum number of restorable points regardless
  of creation frequency. Auditors should verify the retention type matches
  the operational model.
- **Security group referencing (2025):** CloudHSM clusters now support
  referencing security groups in inbound rules (not just CIDR blocks),
  enabling tighter network isolation. Auditors should verify that
  production clusters use security-group-referenced rules rather than
  broad CIDR rules.

## Domain

AWS CloudOps / CloudHSM Security & Compliance.
