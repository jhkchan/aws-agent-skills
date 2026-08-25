---
name: cloudhsm-cluster-deployer
description: 'Provisions AWS CloudHSM clusters with production defaults: cluster creation in a VPC with subnets across 2+ AZs for HA, HSM instance creation, one-time cluster activation (CSR signing, self-signed cert), crypto officer/user management (mu, password policies), HSM backups (daily automatic + on-demand), cross-region backup copy, HA across AZs, PKCS#11/JCE/PCSC library integration, SSL/TLS offload, FIPS 140-2 Level 3 compliance, network security group (sg-xxx), CN-to-cluster-ID mapping, and degradation recovery (create replacement, sync). Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating a CloudHSM cluster, activating an HSM, managing crypto officers, configuring backups, or recovering from HSM degradation. Triggers: create cloudhsm cluster, activate cloudhsm, HSM instance, crypto officer, cloudhsm backup, cross-region backup, PKCS#11, JCE, FIPS 140-2 Level 3, CN-to-cluster-ID.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with cloudhsm, ec2, iam, sts access, plus the CloudHSM client (config -a) and key_mgmt_util / cloudhsm_mgmt_util for crypto officer workflows. Works with Terraform aws_cloudhsm_v2_cluster / aws_cloudhsm_v2_hsm resources and CloudFormation AWS::CloudHSM::Cluster / AWS::CloudHSM::HSM templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Security
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, cloudhsm, hsm, cloudops, deploy, security, provisioning, fips-140-2, pkcs11, jce, cluster-activation, hsm-backup
  dependencies: aws-orchestrator
  keywords: aws, cloudhsm, hsm, cloudops, deploy, provisioning, security, fips 140-2, pkcs#11, jce, crypto officer, cluster activation, hsm backup, cross-region backup, ha
  when_to_use: Invoke when the user wants to create an AWS CloudHSM cluster, activate an HSM (CSR → self-signed cert), create HSM instances across 2+ AZs for HA, manage crypto officers and users, configure backups (daily + on-demand + cross-region copy), integrate PKCS#11/JCE/PCSC libraries, offload SSL/TLS, or recover from HSM degradation. Do NOT invoke for AWS KMS (use kms-key-deployer), ACM (use acm-certificate-deployer), or AWS Signer (use signer-signing-profile-deployer).
---

# CloudHSM Cluster Deployer

An AWS CloudOps agent skill that provisions AWS CloudHSM clusters
with correct production defaults: cluster creation in a VPC with
subnets across 2+ AZs, HSM instance creation, one-time cluster
activation (CSR → self-signed cert), crypto officer/user management,
backups, HA, PKCS#11/JCE integration, FIPS 140-2 Level 3 posture,
and degradation recovery. Captures every configuration decision and
emits a READY_TO_DEPLOY checklist with verification commands.

## Activation keywords

create CloudHSM cluster, activate CloudHSM, HSM instance, crypto
officer, CloudHSM backup, cross-region backup, PKCS#11, JCE, FIPS
140-2 Level 3, CN-to-cluster-ID, HSM degradation recovery.

## STRICT output contract

When this skill is invoked with a CloudHSM-provisioning request
(create a cluster, activate an HSM, add an HSM instance, configure
backups, or recover from degradation), the agent MUST respond with
the READY_TO_DEPLOY checklist defined in "Output format" using the
literal all-caps labels `CLOUDHSM:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels
breaks automation silently.

If any prerequisite is missing, the verdict is
`PREREQUISITES_MISSING` with a specific gap citation in the checklist
(marked `[✗]`), and `READY_TO_DEPLOY` MUST NOT also appear. The
response uses these literal labels: `CLOUDHSM: <cluster-id>
(<subnet-az-list>)`, then `VERDICT:`, then `CHECKLIST:` with status
markers, then `VERIFICATION_COMMANDS:` with indented
`aws cloudhsmv2 ...` and `aws ec2 ...` commands.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Cluster creation (VPC, 2+ AZ subnets) | Core topology |
| Step 2 — HSM instance creation | Per-AZ HA |
| Step 3 — Cluster activation (one-time CSR) | One-time gate |
| Step 4 — Crypto officer/user management | CO password + users |
| Step 5 — HSM backups (daily + on-demand) | Backup posture |
| Step 6 — Cross-region backup copy | DR posture |
| Step 7 — HA across AZs | Availability |
| Step 8 — PKCS#11/JCE/PCSC integration | Client libraries |
| Step 9 — SSL/TLS offload | Workload integration |
| Step 10 — FIPS 140-2 Level 3 compliance | Compliance |
| Step 11 — Network security group (sg-xxx) | Network isolation |
| Step 12 — CN-to-cluster-ID mapping | Client discovery |
| Step 13 — Degradation recovery | Replace + sync |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/cluster-activation-and-users.md | Activation + CO detail |
| references/backups-and-ha.md | Backups + HA + recovery detail |
| references/advanced-patterns.md | Heuristics + integration detail |
| references/error-handling.md | API errors + remedies |

## Mindset

**One-line takeaway:** An AWS CloudHSM cluster is a single-tenant
HSM fleet inside your VPC, validated to FIPS 140-2 Level 3.
Creation gives you a `cluster-id`; creating the FIRST HSM produces
a CSR that you sign once to issue the cluster's customer certificate
— this activation is one-time and the resulting trust root is what
every subsequent HSM inherits. Production clusters need HSMs in
≥2 AZs for HA, and the crypto officer (CO) password is NOT
recoverable — lose it (or lose quorum) and the cluster's key
material is unrecoverable.

Three misconceptions dominate CloudHSM misdesign at provisioning
time:

- **"Create a cluster and you're done."** You're not. After
  `create-cluster` you must (a) create at least one HSM instance
  (`create-hsm`), (b) wait for the HSM to be `ACTIVE`, (c) sign the
  CSR the HSM produces and upload the signed cert + your customerCA
  certificate to activate the cluster. Until activated, no CO, no
  users, no crypto operations.

- **"One HSM is enough for HA."** It isn't. A single HSM is a
  single point of failure. AWS CloudHSM supports HA by adding HSM
  instances in different AZs to the SAME cluster — they auto-sync
  key material. Production needs ≥2 AZs.

- **"The CO password can be reset like a normal password."** It
  cannot. CloudHSM crypto officer credentials are NOT recoverable.
  Lose the CO password (or the CO user) and you lose access to the
  key material. Maintain quorum and a secure offline record. No
  "forgot password" flow exists.

## Configuration dependency graph (novel heuristic)

CloudHSM configurations are NOT independent. The cluster needs a
VPC with subnets in 2+ AZs. The first HSM instance produces the
CSR. Activation (CSR → self-signed cert) is a one-time gate that
unlocks CO/user management. Backups are taken per-cluster, copied
cross-region for DR. HA requires ≥2 AZs. Use this graph to sequence
provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Cluster | VPC + ≥2 subnet-AZs; `cloudhsm:CreateCluster` | cluster-id is fixed; subnet list cannot be expanded later | cluster-id for HSM creation |
| HSM instance | cluster-id; AZ in subnet list; `cloudhsm:CreateHsm` | first HSM emits a CSR; HSM unreachable until activation | CSR for activation |
| Cluster activation | first HSM `ACTIVE`; CSR signed by in-house CA | ONE-TIME — customer cert becomes trust root for every subsequent HSM | CO/user mgmt; all crypto ops |
| Crypto officer (CO) | cluster activated; CO logs in via `cloudhsm_mgmt_util` (mu) | CO password NOT recoverable; lose CO + quorum = lose key material | user creation, key mgmt, policy |
| HSM user (CU) | cluster activated; CO creates users via `mu` or `key_mgmt_util` | users are cluster-scoped; same username/password on every HSM (sync) | key use via PKCS#11/JCE clients |
| Daily automatic backup | cluster activated; 5-min delta + daily snapshot | backups cluster-scoped; retention configurable; hold key material | point-in-time restore |
| On-demand backup | cluster activated; via mu `createBackup` | snapshot at time T | pre-change safety net |
| Cross-region backup copy | destination region enabled; `cloudhsm:CopyBackupToRegion` | copy is one-way; restores in destination create a new cluster | DR in second region |
| HA across AZs | cluster activated; ≥2 HSM instances in different AZs | key material auto-syncs across HSMs; client lib load-balances | AZ failure tolerance |
| PKCS#11/JCE client | cluster activated; client configured with CN-to-cluster-ID | client uses customer CA cert to trust cluster; wrong mapping = failure | workload crypto operations |
| Network security group | SG attached to CloudHSM ENIs; inbound from workload subnets | SG enforced at ENI; too-broad CIDR = attack surface | network isolation |
| CN-to-cluster-ID mapping | registered via `configure -a <ip>` or DNS CNAME | client uses CN to verify cluster identity; mismatch = TLS failure | client bootstrap |

**The activation-is-one-time row is the one a baseline model
misses.** A naive answer treats activation as repeatable or skips
it. In reality the customer certificate you upload after signing the
CSR becomes the cluster's permanent trust root; every subsequent
HSM inherits it. The CO-password-not-recoverable row is the second
most missed: operators assume an AWS-side reset path that does not
exist.

**Cross-dependency gotchas:**
- Activation is one-time. After uploading the signed customer
  certificate, you CANNOT re-activate under a different CA without
  a new cluster (restoring from backup).
- HA requires ≥2 AZs in the SAME cluster. Two clusters in two AZs
  do NOT sync key material.
- Cross-region backup copy creates a restorable backup in the
  destination region; it does NOT create a running cluster. Restore
  = `restore-backup` → new cluster-id in destination.
- CloudHSM ENI security group must allow inbound from workload
  subnets on HSM service ports (TCP 22 for SSH-less mu, TCP 17578
  for management, TCP 2223 for client). Use narrowest possible
  CIDR.

## Prerequisites (verify before provisioning)

Before provisioning, verify these prerequisites. If any are missing,
the verdict is **PREREQUISITES_MISSING** and the specific gap must
be cited.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| VPC + ≥2 subnets in different AZs | HA requires ≥2 AZs in the same cluster | `aws ec2 describe-subnets --filters Name=vpc-id,Values=<vpc>` |
| Security group for CloudHSM ENIs | Network isolation; workload subnets only | `aws ec2 describe-security-groups` |
| `cloudhsm:CreateCluster`, `cloudhsm:CreateHsm` IAM | Required to create cluster + HSM | `aws iam simulate-principal-policy ...` |
| Service-linked role (`AWSServiceRoleForCloudHSM`) | CloudHSM auto-creates; if deleted, recreate | `aws iam get-role --role-name AWSServiceRoleForCloudHSM` |
| HSM type chosen (`hsm1.medium`) | Instance type for the HSM | Confirm capacity needs |
| Backup retention policy decision | Daily snapshots; retention in days | Confirm policy intent |
| Cross-region destination (if DR) | Destination region must be enabled | `aws cloudhsmv2 describe-regions-settings --region <dst>` |
| Customer CA (for activation) | Bootstrap CA to sign the first CSR | Confirm in-house CA or self-sign |
| CO password storage plan | CO password is not recoverable | Confirm secret store (Secrets Manager / KMS vault) |
| CloudHSM client installed (for activation) | CloudHSM client + key_mgmt_util + cloudhsm_mgmt_util | `cloudhsm-cli version` |

If any prerequisite is missing, output
`VERDICT: PREREQUISITES_MISSING` and cite the specific gap.

## Step 1 — Cluster creation (VPC, 2+ AZ subnets)

The cluster is a regional resource that holds HSM instances.
Specify the subnet list (one per AZ) and a security group.

```bash
# Create the cluster (subnet-az list fixes the HA topology)
CLUSTER_ID=$(aws cloudhsmv2 create-cluster \
  --hsm-type hsm1.medium \
  --subnet-ids subnet-aaa11122 subnet-bbb22233 subnet-ccc33344 \
  --security-group-id sg-cloudhsm-prod \
  --query 'Cluster.ClusterId' --output text --region us-east-1)

# Verify cluster state (CREATE_IN_PROGRESS → UNINITIALIZED)
aws cloudhsmv2 describe-clusters \
  --filters clusterIds=$CLUSTER_ID \
  --query 'Clusters[*].{Id:ClusterId, State:State, Subnets:SubnetMapping, Type:HsmType}' \
  --output table --region us-east-1
```

**Constraint:** the subnet list CANNOT be expanded after cluster
creation. Plan the AZ topology up front. Adding a new AZ requires a
new cluster.

## Step 2 — HSM instance creation

Create at least one HSM (per AZ) in the cluster. The first HSM
emits the CSR for activation.

```bash
# Create HSMs — one per AZ for HA
aws cloudhsmv2 create-hsm --cluster-id "$CLUSTER_ID" --availability-zone us-east-1a \
  --ip-address 10.0.1.10 --region us-east-1
aws cloudhsmv2 create-hsm --cluster-id "$CLUSTER_ID" --availability-zone us-east-1b \
  --ip-address 10.0.2.10 --region us-east-1

# Verify each HSM reaches ACTIVE
aws cloudhsmv2 describe-clusters --filters clusterIds=$CLUSTER_ID \
  --query 'Clusters[0].Hsms[*].{Id:HsmId, AZ:AvailabilityZone, State:State, ENI:EniIp}' \
  --output table --region us-east-1
```

Each HSM gets an ENI in the specified subnet. State transitions:
`CREATE_IN_PROGRESS → ACTIVE`. Once the first HSM is `ACTIVE`, the
CSR is available via `describe-clusters`.

## Step 3 — Cluster activation (one-time CSR → self-signed cert)

Activation is the one-time gate that unlocks CO/user management.

```bash
# 1. Fetch the CSR from the first ACTIVE HSM
aws cloudhsmv2 describe-clusters \
  --filters clusterIds=$CLUSTER_ID \
  --query 'Clusters[0].Certificates.ClusterCertificate' \
  --output text --region us-east-1 > cluster.csr

# 2. Sign the CSR with your in-house CA (or self-sign for bootstrap)
openssl x509 -req -days 3650 -in cluster.csr \
  -CA customerCA.crt -CAkey customerCA.key -set_serial 01 \
  -out customerCertificate.crt

# 3. Upload signed cert + CA cert to activate the cluster
aws cloudhsmv2 initialize-cluster \
  --cluster-id "$CLUSTER_ID" \
  --signed-cert fileb://customerCertificate.crt \
  --trust-anchor fileb://customerCA.crt --region us-east-1

# 4. Verify state transitions to INITIALIZED → ACTIVE
aws cloudhsmv2 describe-clusters \
  --filters clusterIds=$CLUSTER_ID \
  --query 'Clusters[0].{State:State, Cert:Certificates}' \
  --output table --region us-east-1
```

**Critical:** activation is ONE-TIME. After this, the customer
certificate is the trust root. To change CAs, restore from backup
into a new cluster.

## Step 4 — Crypto officer/user management

Full procedure: [cluster-activation-and-users.md](references/cluster-activation-and-users.md). Log in via `cloudhsm_mgmt_util` (mu) over the ENI; create the first CO (`admin`) and CUs. The CO password is the crown-jewel secret — store in Secrets Manager (customer-managed KMS key) and keep >=2 COs for quorum.

## Step 5 — HSM backups (daily + on-demand)

Full procedure: [backups-and-ha.md](references/backups-and-ha.md). Automatic backups every ~5 minutes (delta) plus a daily snapshot; on-demand backups via the mu `createBackup` command. Backups are cluster-scoped; retention is configurable per cluster.

## Step 6 — Cross-region backup copy

Full procedure: [backups-and-ha.md](references/backups-and-ha.md). `copy-backup-to-region` for DR — the copy is one-way and restore in the destination creates a NEW cluster-id (cold DR, not a hot replica).

## Step 7 — HA across AZs

Full procedure: [backups-and-ha.md](references/backups-and-ha.md). 2 AZs tolerates 1 AZ failure (minimum production posture); 3 AZs tolerates 1 failure during a replace (recommended). Two separate clusters do NOT sync key material.

## Step 8 — PKCS#11/JCE/PCSC library integration

Full procedure: [advanced-patterns.md](references/advanced-patterns.md). The client uses the customer CA certificate (uploaded at activation) to trust the cluster — keep the bundle current on every client host.

## Step 9 — SSL/TLS offload

Full procedure: [advanced-patterns.md](references/advanced-patterns.md). Generate the keypair inside the HSM; the web server holds only the certificate — the private key never leaves the HSM.

## Step 10 — FIPS 140-2 Level 3 compliance

Full procedure: [advanced-patterns.md](references/advanced-patterns.md). In-HSM operations only; CloudTrail control-plane + HSM data-plane audit trail; narrow SG inbound; CO quorum for destructive operations.

## Step 11 — Network security group (sg-xxx)

Full procedure: [advanced-patterns.md](references/advanced-patterns.md). Inbound TCP 2223 (client) from workload subnets only; TCP 17578 (management utility); TCP 22 (mu). Use the narrowest CIDR — never `0.0.0.0/0`.

## Step 12 — CN-to-cluster-ID mapping

Full procedure: [cluster-activation-and-users.md](references/cluster-activation-and-users.md). Register the mapping via `configure -a <eni-ip>` or a DNS CNAME; a wrong mapping fails the client TLS handshake.

## Step 13 — Degradation recovery (create replacement, sync)

Full procedure: [backups-and-ha.md](references/backups-and-ha.md). Create the replacement HSM FIRST, wait for ACTIVE + sync, then delete the degraded HSM — never drop below 1 ACTIVE HSM.

## NEVER do these things

1. **NEVER deploy a production CloudHSM cluster with HSMs in only
   one AZ.** Single-AZ is a single point of failure. Use ≥2 AZs.

2. **NEVER skip cluster activation.** `create-cluster` +
   `create-hsm` leaves the cluster UNINITIALIZED. Without activation
   (CSR → signed cert upload), no CO, no users, no crypto.

3. **NEVER treat activation as repeatable.** The customer certificate
   is the cluster's permanent trust root. To change CAs, restore
   from backup into a new cluster.

4. **NEVER lose the CO password.** CloudHSM has NO password reset
   flow. Lose CO + lose quorum = lose key material. Maintain ≥2 COs
   and a secure offline record.

5. **NEVER use two clusters as HA.** Two clusters do NOT sync key
   material. HA is intra-cluster: ≥2 HSMs in different AZs in the
   SAME cluster.

6. **NEVER expand the subnet-AZ list after cluster creation.** The
   subnet list is fixed at create-cluster time. Adding an AZ
   requires a new cluster.

7. **NEVER open CloudHSM ENI security group to `0.0.0.0/0`.** Use
   the narrowest workload-subnet CIDR.

8. **NEVER export key material to workload memory if you need
   FIPS 140-2 Level 3.** Use in-HSM operations via PKCS#11/JCE.

9. **NEVER assume cross-region backup copy creates a hot replica.**
   Copy is one-way. Restore creates a NEW cluster-id; cold DR, not
   a running failover target.

10. **NEVER delete the degraded HSM before the replacement is
    ACTIVE.** Dropping below 1 ACTIVE HSM loses HA. Create
    replacement first; verify sync; then delete.

11. **NEVER confuse CloudHSM with KMS.** CloudHSM is single-tenant
    hardware, FIPS 140-2 Level 3, BYO client libraries, you manage
    users/keys. KMS is multi-tenant regional, FIPS 140-2 Level 2
    (mostly), AWS manages the HSM backing.

## Output format

```text
CLOUDHSM: <cluster-id> (<az-list>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Cluster ID: <cluster-id>
  [✓|✗] VPC + subnets: <vpc-id> (subnet-AZ list)
  [✓|✗] HSM type: hsm1.medium
  [✓|✗] HSM instances: <count> across <n> AZs (≥2 for HA)
  [✓|✗] Cluster state: UNINITIALIZED → ACTIVE (after activation)
  [✓|✗] Activation: CSR signed by <CA>, customer cert uploaded (ONE-TIME)
  [✓|✗] Customer CA: <ca-name> (trust root for the cluster)
  [✓|✗] Crypto officer (CO): ≥2 CO users created
  [✓|✗] CO password: stored in Secrets Manager (KMS-encrypted)
  [✓|✗] Crypto users (CU): <cu-list>
  [✓|✗] Password policy: <policy-summary>
  [✓|✗] Daily automatic backup: enabled (cluster-scoped)
  [✓|✗] On-demand backup: pre-change snapshot available
  [✓|✗] Cross-region backup copy: destination region <region>
  [✓|✗] HA: <n> AZs (tolerates 1 AZ failure)
  [✓|✗] PKCS#11/JCE client: configured with CN-to-cluster-ID mapping
  [✓|✗] SSL/TLS offload: <workload-list>
  [✓|✗] FIPS 140-2 Level 3: in-HSM operations, audit trail configured
  [✓|✗] Security group: sg-cloudhsm-prod (narrow CIDR inbound)
  [✓|✗] CN-to-cluster-ID mapping: configured (DNS CNAME or configure -a)
  [✓|✗] Degradation recovery: documented (create replacement, sync, delete)
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws cloudhsmv2 describe-clusters --filters clusterIds=<cluster-id> --region <region>
  aws cloudhsmv2 describe-backups --filters clusterIds=<cluster-id> --region <region>
  aws ec2 describe-security-groups --group-ids <sg-id> --region <region>
  aws cloudtrail lookup-events --lookup-attributes AttributeKey=EventSource,AttributeValue=cloudhsm.amazonaws.com --region <region>
```

### Worked example — 3-AZ CloudHSM cluster with activation and HA

```text
CLOUDHSM: cluster-abc123def (us-east-1a, us-east-1b, us-east-1c)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Cluster ID: cluster-abc123def
  [✓] VPC + subnets: vpc-aaa11122 (subnet-aaa in 1a, subnet-bbb in 1b, subnet-ccc in 1c)
  [✓] HSM type: hsm1.medium
  [✓] HSM instances: 3 across 3 AZs (tolerates 1 AZ failure during replace)
  [✓] Cluster state: ACTIVE
  [✓] Activation: CSR signed by in-house customerCA, cert uploaded (ONE-TIME)
  [✓] Customer CA: customerCA (trust root for cluster)
  [✓] Crypto officer (CO): admin, officer2 (2 COs for quorum)
  [✓] CO password: stored in Secrets Manager (KMS-encrypted)
  [✓] Crypto users (CU): app-tls-user, app-code-sign-user
  [✓] Password policy: min 14 chars, mixed, 90-day rotation
  [✓] Daily automatic backup: enabled (5-min delta + daily snapshot)
  [✓] On-demand backup: pre-change snapshot backup-aaa11122
  [✓] Cross-region backup copy: us-west-2
  [✓] HA: 3 AZs (tolerates 1 AZ failure during replace)
  [✓] PKCS#11 client: configured (CN-to-cluster-ID via DNS CNAME)
  [✓] SSL/TLS offload: nginx using CloudHSM-held private key
  [✓] FIPS 140-2 Level 3: in-HSM ops, CloudTrail + HSM logs
  [✓] Security group: sg-cloudhsm-prod (10.0.10.0/24 inbound on 2223)
  [✓] CN-to-cluster-ID mapping: cloudhsm.internal.example.com → 10.0.1.10
  [✓] Degradation recovery: documented (create replacement, sync, delete)
  [✓] Tags: Environment=production, Workload=tls-offload, Owner=platform-team
VERIFICATION_COMMANDS:
  aws cloudhsmv2 describe-clusters --filters clusterIds=cluster-abc123def --region us-east-1
  aws cloudhsmv2 describe-backups --filters clusterIds=cluster-abc123def --region us-east-1
  aws ec2 describe-security-groups --group-ids sg-cloudhsm-prod --region us-east-1
  aws cloudtrail lookup-events --lookup-attributes AttributeKey=EventSource,AttributeValue=cloudhsm.amazonaws.com --region us-east-1
```

## References (load on demand)

- [Cluster activation and users](references/cluster-activation-and-users.md) — one-time CSR activation flow, CO/CU management via mu, password policies, quorum, CN-to-cluster-ID mapping (Steps 4 and 12 in detail)
- [Backups and HA](references/backups-and-ha.md) — backup model, cross-region copy, HA topology, degradation recovery, DR drill (Steps 5, 6, 7, and 13 in detail)
- [Advanced patterns](references/advanced-patterns.md) — expert heuristics (one-time activation, >=2 AZs, CO password non-recoverability), PKCS#11/JCE/PCSC integration, SSL/TLS offload, FIPS 140-2 Level 3 posture, security groups (Steps 8-11 in detail)
- [Error handling](references/error-handling.md) — API error codes and remedies
- [End-to-end walkthrough](examples/README.md) — full worked example from invocation to verification

## Domain

AWS CloudOps / AWS CloudHSM Cluster Provisioning & HSM Lifecycle.

## AWS documentation

- **CloudHSM user guide** — https://docs.aws.amazon.com/cloudhsm/latest/userguide/introduction.html
- **Create cluster** — https://docs.aws.amazon.com/cloudhsm/latest/userguide/create-cluster.html
- **Initialize cluster** — https://docs.aws.amazon.com/cloudhsm/latest/userguide/initialize-cluster.html
- **HSM management** — https://docs.aws.amazon.com/cloudhsm/latest/userguide/manage-hsm.html
- **Backups** — https://docs.aws.amazon.com/cloudhsm/latest/userguide/backups.html
- **Cross-region copy** — https://docs.aws.amazon.com/cloudhsm/latest/userguide/backup-copy.html
- **PKCS#11 library** — https://docs.aws.amazon.com/cloudhsm/latest/userguide/pkcs11-lib.html
- **JCE provider** — https://docs.aws.amazon.com/cloudhsm/latest/userguide/java-lib.html
- **FIPS 140-2 Level 3** — https://docs.aws.amazon.com/cloudhsm/latest/userguide/compliance.html
- **CloudTrail events** — https://docs.aws.amazon.com/cloudhsm/latest/userguide/logging-using-cloudtrail.html
