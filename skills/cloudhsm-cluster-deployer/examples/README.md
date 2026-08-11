# End-to-End Example: AWS CloudHSM Cluster Deployment

A walkthrough showing how to use the `cloudhsm-cluster-deployer`
skill from invocation through verification. Mirrors the
structured-eval pattern of shipping a concrete worked example per
skill.

---

## Scenario

You are provisioning a 3-AZ CloudHSM cluster with one-time
activation, two crypto officers (for quorum), daily automatic
backups, cross-region backup copy for DR, PKCS#11 client config,
and nginx SSL/TLS offload. The cluster needs:

- Cluster: `cloudhsm-prod` (3 AZs in us-east-1)
- VPC: `vpc-aaa11122`; subnets `subnet-aaa` (1a), `subnet-bbb` (1b),
  `subnet-ccc` (1c)
- HSM type: `hsm1.medium`
- Security group: `sg-cloudhsm-prod`
- Customer CA: in-house `customerCA`
- CO users: `admin`, `officer2` (CO password in Secrets Manager)
- Daily automatic backup + cross-region copy to us-west-2
- Workload: nginx SSL/TLS offload via PKCS#11

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-cloudhsm-cluster
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a CloudHSM cluster cloudhsm-prod across 3 AZs in
      us-east-1. Activate with our in-house CA. Two CO users,
      password in Secrets Manager. Daily backups plus cross-region
      copy to us-west-2. Configure PKCS#11 for nginx TLS offload."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a cloudhsm cluster"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

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

---

## Step 3 — Provisioning commands

```bash
# 1. Create the cluster (subnet-az list fixes the HA topology)
CLUSTER_ID=$(aws cloudhsmv2 create-cluster \
  --hsm-type hsm1.medium \
  --subnet-ids subnet-aaa subnet-bbb subnet-ccc \
  --security-group-id sg-cloudhsm-prod \
  --query 'Cluster.ClusterId' --output text --region us-east-1)

# 2. Create HSMs (one per AZ)
aws cloudhsmv2 create-hsm --cluster-id "$CLUSTER_ID" --availability-zone us-east-1a \
  --ip-address 10.0.1.10 --region us-east-1
aws cloudhsmv2 create-hsm --cluster-id "$CLUSTER_ID" --availability-zone us-east-1b \
  --ip-address 10.0.2.10 --region us-east-1
aws cloudhsmv2 create-hsm --cluster-id "$CLUSTER_ID" --availability-zone us-east-1c \
  --ip-address 10.0.3.10 --region us-east-1

# 3. Wait for first HSM ACTIVE, then fetch the CSR
aws cloudhsmv2 describe-clusters --filters clusterIds=$CLUSTER_ID \
  --query 'Clusters[0].Certificates.ClusterCertificate' \
  --output text --region us-east-1 > cluster.csr

# 4. Sign the CSR with the in-house CA
openssl x509 -req -days 3650 -in cluster.csr \
  -CA customerCA.crt -CAkey customerCA.key -set_serial 01 \
  -out customerCertificate.crt

# 5. Activate the cluster (ONE-TIME)
aws cloudhsmv2 initialize-cluster \
  --cluster-id "$CLUSTER_ID" \
  --signed-cert fileb://customerCertificate.crt \
  --trust-anchor fileb://customerCA.crt --region us-east-1

# 6. Configure the client and create CO/CU users via mu
sudo /opt/cloudhsm/bin/configure -a 10.0.1.10
/opt/cloudhsm/bin/cloudhsm_mgmt_util /opt/cloudhsm/etc/cloudhsm_mgmt_util.cfg
# Inside mu:
#   loginHSM CO admin <password-from-secrets-manager>
#   createUser CO officer2 <password>
#   createUser CU app-tls-user <password>
#   quit

# 7. Configure cross-region backup copy (run from source region)
aws cloudhsmv2 copy-backup-to-region \
  --backup-id <recent-backup-id> \
  --destination-region us-west-2 --region us-east-1
```

---

## Step 4 — Post-deployment verification

```bash
# Cluster state and HSM topology
aws cloudhsmv2 describe-clusters --filters clusterIds=$CLUSTER_ID \
  --query 'Clusters[0].{State:State, Hsms:Hsms[*].{AZ:AvailabilityZone, State:State, ENI:EniIp}}' \
  --output table --region us-east-1

# Recent backups
aws cloudhsmv2 describe-backups --filters clusterIds=$CLUSTER_ID \
  --query 'Backups[*].{Id:BackupId, Created:CreateTimestamp, Type:BackupType}' \
  --output table --region us-east-1

# Security group rules
aws ec2 describe-security-groups --group-ids sg-cloudhsm-prod \
  --query 'SecurityGroups[0].IpPermissions' --output table --region us-east-1

# CloudTrail audit of CloudHSM control-plane events
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventSource,AttributeValue=cloudhsm.amazonaws.com \
  --max-results 20 --region us-east-1
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| HA topology | Single AZ | ≥2 AZs (3 recommended) | Single-AZ is a single point of failure; HA is intra-cluster |
| Activation | Skipped or treated as repeatable | One-time CSR → cert upload | Without activation, no CO, no users, no crypto |
| CO password | Stored in plaintext or single CO | Secrets Manager + ≥2 COs | CO password is NOT recoverable; lose quorum = lose keys |
| Cross-region copy | Treated as hot replica | Cold DR (restore creates new cluster) | Restore creates a NEW cluster-id; not a failover target |
| Subnet-AZ list | Added later | Fixed at create-cluster | Adding an AZ requires a new cluster |
| Client trust | Missing CA bundle | customerCA.crt on every client | Client uses CA bundle to verify cluster TLS |
| Degradation | Delete first, replace after | Replace first, delete after | Dropping below 1 ACTIVE HSM loses HA |
| CloudHSM vs KMS | Confused | Single-tenant FIPS 140-2 L3 vs multi-tenant L2 | CloudHSM is BYO client libraries, you manage keys |

---

## Related artifacts

- **Skill definition:** `skills/cloudhsm-cluster-deployer/SKILL.md`
- **Cluster activation + CO guide:** `skills/cloudhsm-cluster-deployer/references/cluster-activation-and-users.md`
- **Backups + HA + recovery guide:** `skills/cloudhsm-cluster-deployer/references/backups-and-ha.md`
- **Slash command:** `commands/aws/deploy-cloudhsm-cluster.md`
- **Eval suite:** `skills/cloudhsm-cluster-deployer/evals/evals.json`
- **Legacy test cases:** `skills/cloudhsm-cluster-deployer/eval/test-cases.yaml`
