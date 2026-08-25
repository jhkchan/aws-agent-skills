# Advanced patterns — CloudHSM Cluster Posture Auditor

Expert knowledge, edge-case catalog, and recent-feature notes moved out of
SKILL.md for progressive disclosure. Load on demand.

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
