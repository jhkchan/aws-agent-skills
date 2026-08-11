---
name: cloudhsm-cluster-deployer
description: >-
  Provisions AWS CloudHSM clusters with production defaults: cluster
  creation in a VPC with subnets across 2+ AZs for HA, HSM instance
  creation, one-time cluster activation (CSR signing, self-signed
  cert), crypto officer/user management (mu, password policies),
  HSM backups (daily automatic + on-demand), cross-region backup
  copy, HA across AZs, PKCS#11/JCE/PCSC library integration,
  SSL/TLS offload, FIPS 140-2 Level 3 compliance, network security
  group (sg-xxx), CN-to-cluster-ID mapping, and degradation
  recovery (create replacement, sync). Emits a READY_TO_DEPLOY
  checklist with verification commands. Use when creating a
  CloudHSM cluster, activating an HSM, managing crypto officers,
  configuring backups, or recovering from HSM degradation.
  Triggers: create cloudhsm cluster, activate cloudhsm, HSM
  instance, crypto officer, cloudhsm backup, cross-region backup,
  PKCS#11, JCE, FIPS 140-2 Level 3, CN-to-cluster-ID.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live deployment: AWS CLI v2 with cloudhsm,
  ec2, iam, sts access, plus the CloudHSM client (config -a) and
  key_mgmt_util / cloudhsm_mgmt_util for crypto officer workflows.
  Works with Terraform aws_cloudhsm_v2_cluster /
  aws_cloudhsm_v2_hsm resources and CloudFormation
  AWS::CloudHSM::Cluster / AWS::CloudHSM::HSM templates.
keywords:
  - aws
  - cloudhsm
  - hsm
  - cloudops
  - deploy
  - provisioning
  - security
  - fips 140-2
  - pkcs#11
  - jce
  - crypto officer
  - cluster activation
  - hsm backup
  - cross-region backup
  - ha
tags:
  - aws
  - cloudhsm
  - hsm
  - cloudops
  - deploy
  - security
  - provisioning
  - fips-140-2
  - pkcs11
  - jce
  - cluster-activation
  - hsm-backup
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: Security
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - cloudhsm
    - hsm
    - cloudops
    - deploy
    - security
    - provisioning
    - fips-140-2
    - pkcs11
    - jce
    - cluster-activation
    - hsm-backup
  dependencies:
    - aws-orchestrator
  keywords:
    - create cloudhsm cluster
    - activate cloudhsm cluster
    - hsm instance
    - crypto officer
    - cloudhsm backup
    - cross-region backup
    - pkcs#11 library
    - jce library
    - fips 140-2 level 3
    - cn-to-cluster-id mapping
    - hsm degradation recovery
  when_to_use: >-
    Invoke when the user wants to create an AWS CloudHSM cluster,
    activate an HSM (CSR → self-signed cert), create HSM instances
    across 2+ AZs for HA, manage crypto officers and users,
    configure backups (daily + on-demand + cross-region copy),
    integrate PKCS#11/JCE/PCSC libraries, offload SSL/TLS, or
    recover from HSM degradation. Do NOT invoke for AWS KMS
    (use kms-key-deployer), ACM (use acm-certificate-deployer),
    or AWS Signer (use signer-signing-profile-deployer).
---

# CloudHSM Cluster Deployer

An AWS CloudOps agent skill that provisions AWS CloudHSM clusters
with correct production defaults: cluster creation in a VPC with
subnets across 2+ AZs, HSM instance creation, one-time cluster
activation (CSR → self-signed cert), crypto officer/user management,
backups, HA, PKCS#11/JCE integration, FIPS 140-2 Level 3 posture,
and degradation recovery. The skill captures every configuration
decision and emits a READY_TO_DEPLOY checklist with copy-pasteable
verification commands.

## Activation keywords

create CloudHSM cluster, activate CloudHSM cluster, HSM instance,
crypto officer, CloudHSM backup, cross-region backup, PKCS#11, JCE,
FIPS 140-2 Level 3, CN-to-cluster-ID mapping, HSM degradation
recovery.

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

## Mindset

**One-line takeaway:** An AWS CloudHSM cluster is a single-tenant
HSM fleet inside your VPC, validated to FIPS 140-2 Level 3.
Creation gives you a `cluster-id`; creating the FIRST HSM instance
produces a CSR that you sign once to issue the cluster's self-signed
customer-certificate — this activation is one-time and the resulting
trust root is what every subsequent HSM in the cluster inherits.
Production clusters need HSM instances in at least 2 AZs for HA, and
the crypto officer (CO) password is NOT recoverable — lose it (or
lose quorum) and the cluster's key material is unrecoverable.

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
| Cluster | VPC + ≥2 subnet-AZs in the region; `ec2:CreateSecurityGroup` for the CloudHSM ENI; `cloudhsm:CreateCluster` | cluster-id is fixed; subnet list cannot be expanded later without a new cluster | cluster-id for HSM creation |
| HSM instance | cluster-id; AZ in cluster's subnet list; `cloudhsm:CreateHsm` | first HSM in a cluster emits a CSR; HSM is unreachable until cluster activation completes | CSR for activation |
| Cluster activation (CSR → cert) | first HSM `ACTIVE`; CSR downloaded via `describe-clusters`; signed by your in-house CA | activation is ONE-TIME — the customer certificate becomes the trust root for every subsequent HSM | CO/user management; all crypto operations |
| Crypto officer (CO) | cluster activated; CO logs in via `cloudhsm_mgmt_util` (mu) over the ENI | CO password is NOT recoverable; lose CO + lose quorum = lose key material | user creation, key management, policy |
| HSM user (CU) | cluster activated; CO creates users via `mu` or key_mgmt_util (ku) | users are cluster-scoped; same username/password on every HSM in cluster (sync) | key use via PKCS#11/JCE clients |
| Daily automatic backup | cluster activated; AWS auto-backup every 5 min (delta) + daily snapshot | backups are cluster-scoped; retention configurable; backups hold key material | point-in-time restore |
| On-demand backup | cluster activated; `cloudhsm:CopyBackupToRegion` requires source backup ID | on-demand backup is a snapshot at time T | pre-change safety net |
| Cross-region backup copy | destination region enabled for CloudHSM; `cloudhsm:CopyBackupToRegion` | copy is one-way; restores in destination create a new cluster | DR in second region |
| HA across AZs | cluster activated; ≥2 HSM instances in different AZs | key material auto-syncs across HSMs in cluster; client lib load-balances | AZ failure tolerance |
| PKCS#11/JCE client | cluster activated; client configured with cluster's CN-to-cluster-ID mapping | client uses the customer CA cert to trust the cluster; wrong mapping = connection failure | workload crypto operations |
| Network security group | security group attached to CloudHSM ENIs; inbound from workload subnets only | SG is enforced at the ENI; too-broad CIDR = attack surface | network isolation |
| CN-to-cluster-ID mapping | registered in client config via `configure -a <cluster-ip>` or DNS CNAME | client uses CN to verify cluster identity; mismatch = TLS failure | client bootstrap |

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

## Expert heuristic: cluster activation is one-time (CSR → self-signed cert)

A baseline model says "create a cluster, create an HSM, done." The
correct heuristic recognizes that the first HSM in a cluster emits
a Certificate Signing Request (CSR); you sign it with your in-house
CA (or self-sign for the bootstrap), then upload the signed
certificate PLUS the issuing CA certificate to AWS. AWS uses these
to activate the cluster. After activation:

```text
Cluster state lifecycle:
  CreateCluster → Uninitialized
  CreateHsm (first) → ACTIVATING (HSM emits CSR)
  Download CSR → sign with your CA → upload signed cert + CA cert
  AWS verifies → cluster becomes ACTIVE
  Once ACTIVE: activation is ONE-TIME. The customer certificate is
  the trust root for every subsequent HSM in the cluster.
```

**Key implication:** you CANNOT re-activate under a different CA
without a new cluster. Plan the CA choice up front. If you must
rotate the trust root, restore from backup into a new cluster.

## Expert heuristic: minimum 2 AZs for HA

A single HSM is a single point of failure. CloudHSM achieves HA by
adding HSM instances in different AZs to the SAME cluster; key
material auto-syncs.

```text
Production topology:
  Cluster: cloudhsm-prod (cluster-xxx)
    ├── HSM in us-east-1a (subnet-aaa)
    ├── HSM in us-east-1b (subnet-bbb)
    └── HSM in us-east-1c (subnet-ccc)  [optional — N+2 for stricter HA]

  Key material auto-syncs across HSMs. Client lib load-balances
  across the ENIs. Loss of 1 AZ = no outage (other HSMs serve).
```

**Key implication:** 2 AZs tolerates 1 AZ failure. 3 AZs tolerates
1 AZ failure during a replace operation (the recommended production
posture). Two separate clusters in two AZs do NOT sync and do NOT
count as HA.

## Expert heuristic: crypto officer password is NOT recoverable (quorum required)

CloudHSM has no "forgot password" flow. The Crypto Officer (CO)
user is the root-of-trust account inside the HSM. Lose the CO
password AND you've lost access to the cluster's key material.
Lose quorum (if you set quorum policies) and you've lost the ability
to perform privileged operations.

```text
Recoverability posture:
  CO password lost → key material is UNRECOVERABLE
  Quorum not met → privileged operations blocked (no override)
  Mitigations:
    ├── ≥2 CO users in the cluster, each with the password in a
    │   secure offline store (secrets manager, KMS-encrypted vault)
    ├── Documented quorum policy (M-of-N) for the most destructive
    │   operations
    └── Frequent backups + cross-region copy so the worst case is
        "restore from backup into a new cluster" (still loses keys
        taken after the last backup if the cluster is unrecoverable)
```

**Key implication:** treat the CO password as a crown-jewel secret.
Maintain ≥2 COs, document the password rotation procedure, and test
the backup-restore drill annually.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites.
If any are missing, the verdict is **PREREQUISITES_MISSING** and the
specific gap must be cited.

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

echo "Cluster ID: $CLUSTER_ID"

# Verify cluster state (will be CREATE_IN_PROGRESS → UNINITIALIZED)
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
aws cloudhsmv2 describe-clusters \
  --filters clusterIds=$CLUSTER_ID \
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

Once the cluster is ACTIVE, log in via the CloudHSM management util
(`cloudhsm_mgmt_util`, often aliased `mu`) over the ENI to create
the first Crypto Officer (CO) and Crypto Users (CU).

```bash
# Configure the CloudHSM client with the cluster's ENI
sudo /opt/cloudhsm/bin/configure -a 10.0.1.10

# Start the management utility (mu)
/opt/cloudhsm/bin/cloudhsm_mgmt_util /opt/cloudhsm/etc/cloudhsm_mgmt_util.cfg

# Inside mu:
#   loginHSM CO admin <password-from-secrets-manager>
#   createUser CO officer2 <password>
#   createUser CU app-user <password>
#   quit
```

**Critical practices:**
- The CO `admin` password is the cluster's crown-jewel secret. Store
  it in AWS Secrets Manager (encrypted with a customer-managed KMS
  key).
- Create ≥2 CO users so you have quorum if one is lost.
- Crypto Users (CU) own and use keys; they are created by COs and
  scoped to the cluster.
- Password policies (length, complexity) are enforced per-HSM and
  propagate via the cluster sync.

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

## Step 7 — HA across AZs

HA is achieved by adding HSM instances in different AZs to the SAME
cluster. Key material auto-syncs.

```text
Recommended HA topologies:
  2 AZs: tolerates 1 AZ failure (minimum production posture)
  3 AZs: tolerates 1 AZ failure during a replace operation
         (recommended for strict HA)
```

```bash
# Add a third HSM for stricter HA
aws cloudhsmv2 create-hsm --cluster-id "$CLUSTER_ID" \
  --availability-zone us-east-1c --ip-address 10.0.3.10 \
  --region us-east-1

# Verify all HSMs ACTIVE and in sync
aws cloudhsmv2 describe-clusters \
  --filters clusterIds=$CLUSTER_ID \
  --query 'Clusters[0].Hsms[*].{AZ:AvailabilityZone, State:State, ENI:EniIp}' \
  --output table --region us-east-1
```

Two separate clusters in two AZs do NOT sync and do NOT count as
HA. HA is intra-cluster.

## Step 8 — PKCS#11/JCE/PCSC library integration

Workloads integrate with CloudHSM via the PKCS#11 library (C/C++),
the JCE provider (Java), or PCSC (smart-card HSM). The client
config maps the cluster CN to the cluster-ID.

```bash
# Install the PKCS#11 library (Amazon-provided)
sudo yum install -y cloudhsm-client-pkcs11

# Configure the client with the cluster's ENI and CA cert
sudo /opt/cloudhsm/bin/configure-pkcs11 -i <cluster-id> \
  -e /opt/cloudhsm/etc/customerCA.crt

# For Java JCE: install the JCE provider and configure
sudo yum install -y cloudhsm-client-java
# Edit /opt/cloudhsm/java/libcloudhsm.conf to point at the cluster
```

**Constraint:** the client uses the customer CA certificate (the
one you uploaded during activation) to trust the cluster. Keep that
certificate bundle current on every client host.

## Step 9 — SSL/TLS offload

CloudHSM can hold the private key for an SSL/TLS offload workload
(Nginx, Apache, HAProxy). The private key never leaves the HSM; the
workload references it by handle.

```text
1. Generate the keypair inside the HSM (via PKCS#11 or key_mgmt_util).
2. Create a CSR from the HSM-held private key.
3. Issue the certificate (ACM or external CA).
4. Configure the web server to use the CloudHSM PKCS#11 provider
   for the private key.
5. The web server holds only the certificate; the private key
   remains in the HSM.
```

This offloads TLS termination private-key operations to the HSM,
satisfying FIPS 140-2 Level 3 for key material.

## Step 10 — FIPS 140-2 Level 3 compliance

AWS CloudHSM is validated to FIPS 140-2 Level 3. To maintain the
compliance posture:

- Use only Amazon-provided client libraries (PKCS#11, JCE, PCSC).
- Do NOT export key material to the workload's memory (use
  in-HSM operations).
- Maintain the audit trail: CloudTrail logs the control-plane
  (`CreateCluster`, `CreateHsm`, `InitializeCluster`,
  `CopyBackupToRegion`); the HSM itself logs data-plane operations
  (key use, user logins) to HSM logs.
- Restrict ENI security group inbound to workload subnets only.
- Use CO quorum for destructive operations.

```bash
# Audit CloudHSM control-plane events
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventSource,AttributeValue=cloudhsm.amazonaws.com \
  --max-results 50 --region us-east-1
```

## Step 11 — Network security group (sg-xxx)

The CloudHSM ENI security group is the network-isolation boundary.
Inbound rules should be the narrowest possible.

| Port | Protocol | Source | Purpose |
|---|---|---|---|
| 22 | TCP | CO bastion subnet | SSH-less management (mu) — restrict further |
| 17578 | TCP | CO bastion subnet | Management utility |
| 2223 | TCP | workload subnet | Client (PKCS#11/JCE/PCSC) |

```bash
# Tighten the security group to workload subnet CIDR only
aws ec2 authorize-security-group-ingress \
  --group-id sg-cloudhsm-prod \
  --ip-permissions \
    IpProtocol=tcp,FromPort=2223,ToPort=2223,IpRanges=[{CidrIp=10.0.10.0/24}] \
  --region us-east-1
```

Never open `0.0.0.0/0` to CloudHSM ENIs.

## Step 12 — CN-to-cluster-ID mapping

The CloudHSM client uses the cluster's Common Name (CN) to verify
the cluster during TLS handshake. The mapping is registered in the
client config (`configure -a <eni-ip>` or DNS CNAME).

```bash
# Point the client at the cluster's primary ENI
sudo /opt/cloudhsm/bin/configure -a 10.0.1.10

# Or use DNS CNAME: cloudhsm.internal.example.com → 10.0.1.10
# The client uses the CN from the cluster cert to verify identity
```

If the mapping is wrong, the client fails the TLS handshake. Verify
the customer CA bundle is current on the client host.

## Step 13 — Degradation recovery (create replacement, sync)

When an HSM degrades (hardware fault, AZ outage), recover by
creating a replacement HSM in the same cluster; key material
auto-syncs from the surviving HSM(s).

```text
Recovery procedure:
  1. Identify the degraded HSM (describe-clusters, state != ACTIVE)
  2. (If AZ is healthy) Create a replacement HSM in the same AZ:
       aws cloudhsmv2 create-hsm --cluster-id <id> --availability-zone <az>
  3. (If AZ is down) Create a replacement HSM in a different AZ
     already in the cluster's subnet list
  4. Wait for new HSM to reach ACTIVE — it auto-syncs key material
  5. Delete the degraded HSM:
       aws cloudhsmv2 delete-hsm --cluster-id <id> --hsm-id <degraded-hsm-id>
  6. Verify ≥2 ACTIVE HSMs in different AZs
```

```bash
# Delete a degraded HSM after the replacement is ACTIVE
aws cloudhsmv2 delete-hsm \
  --cluster-id "$CLUSTER_ID" \
  --hsm-id hsm-degraded111 \
  --region us-east-1
```

**Constraint:** never drop below 1 ACTIVE HSM in a production
cluster; you lose HA. Always create the replacement BEFORE deleting
the degraded HSM.

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
  [✓] Activation: CSR signed by in-house customerCA, customer cert uploaded (ONE-TIME)
  [✓] Customer CA: customerCA (trust root for cluster)
  [✓] Crypto officer (CO): admin, officer2 (2 COs for quorum)
  [✓] CO password: stored in Secrets Manager (KMS-encrypted)
  [✓] Crypto users (CU): app-tls-user, app-code-sign-user
  [✓] Password policy: min 14 chars, mixed, 90-day rotation
  [✓] Daily automatic backup: enabled (5-min delta + daily snapshot)
  [✓] On-demand backup: pre-change snapshot backup-aaa11122
  [✓] Cross-region backup copy: us-west-2
  [✓] HA: 3 AZs (tolerates 1 AZ failure during replace)
  [✓] PKCS#11 client: configured (CN-to-cluster-ID mapping via DNS CNAME)
  [✓] SSL/TLS offload: nginx using CloudHSM-held private key
  [✓] FIPS 140-2 Level 3: in-HSM operations, CloudTrail + HSM logs
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

## Error handling

### create-cluster fails with CloudHsmAccessDeniedException
- Caller missing `cloudhsm:CreateCluster` or the
  AWSServiceRoleForCloudHSM service-linked role. Recreate via IAM.

### HSM stuck in CREATE_IN_PROGRESS
- Poll `describe-clusters`. If >30 min, the AZ may lack capacity.
  Try a different AZ in the cluster's subnet list.

### initialize-cluster fails with CloudHsmInvalidStateException
- The CSR hasn't been emitted yet (first HSM not ACTIVE). Wait for
  first HSM to reach ACTIVE before fetching the CSR.

### CO login fails with HSM error
- Wrong CO password, or the cluster's customer CA bundle isn't on
  the client host. Verify the CA bundle path
  (`/opt/cloudhsm/etc/customerCA.crt`) and password.

### Cross-region copy fails with ValidationException
- Destination region not enabled for CloudHSM. Enable via
  `cloudhsmv2 put-allow-destination-region` (or console).

### HSM in degraded state
- Create a replacement HSM in the same cluster (different AZ if the
  AZ is down), wait for ACTIVE + sync, then delete the degraded
  HSM.

### Want to change the customer CA
- Activation is one-time. To change CAs, restore from backup into a
  new cluster under the new CA.

## Domain

AWS CloudOps / AWS CloudHSM Cluster Provisioning & HSM Lifecycle.

## AWS documentation

- **AWS CloudHSM user guide** — https://docs.aws.amazon.com/cloudhsm/latest/userguide/introduction.html
- **Create cluster** — https://docs.aws.amazon.com/cloudhsm/latest/userguide/create-cluster.html
- **Initialize cluster (activation)** — https://docs.aws.amazon.com/cloudhsm/latest/userguide/initialize-cluster.html
- **HSM management** — https://docs.aws.amazon.com/cloudhsm/latest/userguide/manage-hsm.html
- **Backups** — https://docs.aws.amazon.com/cloudhsm/latest/userguide/backups.html
- **Cross-region backup copy** — https://docs.aws.amazon.com/cloudhsm/latest/userguide/backup-copy.html
- **PKCS#11 library** — https://docs.aws.amazon.com/cloudhsm/latest/userguide/pkcs11-lib.html
- **JCE provider** — https://docs.aws.amazon.com/cloudhsm/latest/userguide/java-lib.html
- **FIPS 140-2 Level 3** — https://docs.aws.amazon.com/cloudhsm/latest/userguide/compliance.html
- **CloudTrail events** — https://docs.aws.amazon.com/cloudhsm/latest/userguide/logging-using-cloudtrail.html
