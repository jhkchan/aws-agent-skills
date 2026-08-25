# Backups and HA — CloudHSM Cluster Deployer

Deep reference on CloudHSM backups (daily automatic + on-demand),
cross-region backup copy semantics, HA topology (≥2 AZs intra-
cluster), and degradation recovery (create replacement, sync,
delete). Loaded on demand by the skill — kept out of the main
SKILL.md body so the provisioning procedure stays scannable.

## Backup model

AWS CloudHSM takes backups automatically and on-demand.

| Type | Trigger | Scope | Retention |
|---|---|---|---|
| Automatic delta | Every ~5 min | Cluster (config + key material) | Configurable per cluster |
| Automatic daily | Daily snapshot | Cluster | Configurable per cluster |
| On-demand | Operator (via mu) | Cluster at time T | Manual |

Backups are cluster-scoped. The backup captures config AND key
material, so a restore reconstructs a working cluster.

### Listing backups

```bash
aws cloudhsmv2 describe-backups \
  --filters clusterIds=$CLUSTER_ID \
  --query 'Backups[*].{Id:BackupId, Created:CreateTimestamp, Type:BackupType, State:BackupState}' \
  --output table --region us-east-1
```

### On-demand backup via mu

```text
Inside cloudhsm_mgmt_util (mu) as CO:
  createBackup
  → returns backup-id (e.g., bk-aaa11122)
```

Use an on-demand backup before any risky change (key rotation, user
deletion, CO password rotation).

### Restoring from a backup

```bash
aws cloudhsmv2 restore-backup --backup-id <backup-id> --region us-east-1
# Creates a NEW cluster-id from the backup
```

Restore ALWAYS creates a new cluster-id. There is no in-place
restore.

## Cross-region backup copy

For DR, copy backups to a second region.

```bash
aws cloudhsmv2 copy-backup-to-region \
  --backup-id <backup-id> \
  --destination-region us-west-2 \
  --region us-east-1

# In the destination region, restore the copied backup into a new cluster
aws cloudhsmv2 restore-backup --backup-id <dest-backup-id> --region us-west-2
```

**Semantics:**
- Copy is ONE-WAY (source → destination).
- The destination region must be enabled for CloudHSM.
- Restore in the destination creates a NEW cluster-id; it is a COLD
  DR, not a running failover target.
- The new cluster in the destination region needs its own HSM
  instances, CO users, and client configuration.

## HA topology

HA is achieved by adding HSM instances in different AZs to the SAME
cluster. Key material auto-syncs across HSMs in the cluster.

```text
Production topology:
  Cluster: cloudhsm-prod (cluster-xxx)
    ├── HSM in us-east-1a (subnet-aaa) — ENI 10.0.1.10
    ├── HSM in us-east-1b (subnet-bbb) — ENI 10.0.2.10
    └── HSM in us-east-1c (subnet-ccc) — ENI 10.0.3.10

  Key material auto-syncs. Client lib load-balances across ENIs.
  Loss of 1 AZ = no outage (other HSMs serve).
```

**HA rules:**
- 2 AZs tolerates 1 AZ failure (minimum production posture).
- 3 AZs tolerates 1 AZ failure during a replace operation
  (recommended for strict HA).
- Two separate clusters in two AZs do NOT sync key material and do
  NOT count as HA.

### Adding an HSM for stricter HA

```bash
aws cloudhsmv2 create-hsm --cluster-id "$CLUSTER_ID" \
  --availability-zone us-east-1c --ip-address 10.0.3.10 --region us-east-1
```

The new HSM auto-syncs key material from the existing HSMs.

## Degradation recovery

When an HSM degrades (hardware fault, AZ outage), recover by
creating a replacement HSM in the SAME cluster, waiting for ACTIVE
+ sync, then deleting the degraded HSM.

```text
Recovery procedure:
  1. Identify the degraded HSM (describe-clusters, state != ACTIVE)
  2. If AZ is healthy:
       aws cloudhsmv2 create-hsm --cluster-id <id> --availability-zone <az>
  3. If AZ is down:
       create the replacement in a different AZ already in the
       cluster's subnet list
  4. Wait for replacement ACTIVE — it auto-syncs key material
  5. Delete the degraded HSM:
       aws cloudhsmv2 delete-hsm --cluster-id <id> --hsm-id <degraded>
  6. Verify ≥2 ACTIVE HSMs in different AZs
```

**Constraint:** NEVER drop below 1 ACTIVE HSM in a production
cluster. Always create the replacement BEFORE deleting the degraded
HSM. Dropping below 1 ACTIVE HSM loses HA and may impact clients.

### Delete degraded HSM

```bash
aws cloudhsmv2 delete-hsm \
  --cluster-id "$CLUSTER_ID" \
  --hsm-id hsm-degraded111 --region us-east-1
```

## DR drill

Run an annual DR drill to verify the restore path:

1. Pick a recent backup (automatic or on-demand).
2. Copy cross-region (if not already copied automatically).
3. Restore in the destination region → new cluster-id.
4. Create HSM instances in the new cluster (≥2 AZs).
5. Activate the new cluster (one-time CSR flow).
6. Create CO/CU users.
7. Configure a client to point at the new cluster and verify crypto
   operations work.
8. Tear down the DR cluster.

Document the recovery time objective (RTO) and recovery point
objective (RPO) observed during the drill.

## Common pitfalls

1. **Treating cross-region copy as a hot replica.** Restore creates
   a new cluster-id; it is cold DR.

2. **Single-AZ HA.** Two clusters in two AZs do NOT sync. HA is
   intra-cluster.

3. **Deleting before replacing.** Dropping below 1 ACTIVE HSM loses
   HA. Always create the replacement first.

4. **No restore drill.** The restore path is untested until you
   actually run it. Run annually.

5. **Expanding the subnet-AZ list after creation.** The subnet list
   is fixed at `create-cluster` time. Plan the AZ topology up front.

---

## Step 5 — HSM backups (daily + on-demand)

AWS CloudHSM takes automatic backups every 5 minutes (delta) plus a
daily snapshot. On-demand backups create a manual snapshot before
risky changes via the management utility.

```bash
# List recent backups
aws cloudhsmv2 describe-backups \
  --filters clusterIds=$CLUSTER_ID \
  --query 'Backups[*].{Id:BackupId, Created:CreateTimestamp, Type:BackupType, State:BackupState}' \
  --output table --region us-east-1
```

For an on-demand backup, use the management util (`mu`) `createBackup`
command; the backup ID is returned in the mu output. Backups are
cluster-scoped. Retention is configurable per cluster.

---

## Step 6 — Cross-region backup copy

For DR, copy backups to a second region. The destination region
must be enabled for CloudHSM.

```bash
# Copy a backup to a destination region (DR)
aws cloudhsmv2 copy-backup-to-region \
  --backup-id <backup-id> \
  --destination-region us-west-2 \
  --region us-east-1

# In the destination region, restore the backup into a new cluster
aws cloudhsmv2 restore-backup --backup-id <dest-backup-id> --region us-west-2
# (Creates a NEW cluster-id in us-west-2)
```

**Constraint:** cross-region copy is one-way. The destination
backup creates a new cluster-id on restore; it is NOT a hot
replica.

---

## Step 7 — HA across AZs

HA is achieved by adding HSM instances in different AZs to the SAME
cluster. Key material auto-syncs.

```text
Recommended HA topologies:
  2 AZs: tolerates 1 AZ failure (minimum production posture)
  3 AZs: tolerates 1 AZ failure during a replace (recommended)
```

```bash
# Add a third HSM for stricter HA
aws cloudhsmv2 create-hsm --cluster-id "$CLUSTER_ID" \
  --availability-zone us-east-1c --ip-address 10.0.3.10 --region us-east-1

# Verify all HSMs ACTIVE and in sync
aws cloudhsmv2 describe-clusters --filters clusterIds=$CLUSTER_ID \
  --query 'Clusters[0].Hsms[*].{AZ:AvailabilityZone, State:State, ENI:EniIp}' \
  --output table --region us-east-1
```

Two separate clusters in two AZs do NOT sync. HA is intra-cluster.

---

## Step 13 — Degradation recovery (create replacement, sync)

When an HSM degrades (hardware fault, AZ outage), recover by
creating a replacement HSM in the same cluster; key material
auto-syncs from the surviving HSM(s).

```text
Recovery procedure:
  1. Identify the degraded HSM (describe-clusters, state != ACTIVE)
  2. If AZ is healthy: create a replacement HSM in the same AZ
     (aws cloudhsmv2 create-hsm --cluster-id <id> --availability-zone <az>)
  3. If AZ is down: create a replacement in a different AZ already
     in the cluster's subnet list
  4. Wait for new HSM ACTIVE — it auto-syncs key material
  5. Delete the degraded HSM:
     aws cloudhsmv2 delete-hsm --cluster-id <id> --hsm-id <degraded-hsm-id>
  6. Verify ≥2 ACTIVE HSMs in different AZs
```

```bash
# Delete a degraded HSM after the replacement is ACTIVE
aws cloudhsmv2 delete-hsm \
  --cluster-id "$CLUSTER_ID" \
  --hsm-id hsm-degraded111 --region us-east-1
```

**Constraint:** never drop below 1 ACTIVE HSM in production; you
lose HA. Always create the replacement BEFORE deleting the degraded
HSM.
