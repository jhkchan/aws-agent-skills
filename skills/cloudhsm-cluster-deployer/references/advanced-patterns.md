# Advanced Patterns — CloudHSM Cluster Deployer

Deep-dive explanatory content moved out of the SKILL.md body for progressive disclosure: the three expert heuristics (cluster activation is one-time, minimum 2 AZs for HA, CO password non-recoverability), client library integration (PKCS#11/JCE/PCSC), SSL/TLS offload, FIPS 140-2 Level 3 posture, and ENI security group rules. Loaded on demand by the skill.

---

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

---

## Expert heuristic: minimum 2 AZs for HA

A single HSM is a single point of failure. CloudHSM achieves HA by
adding HSM instances in different AZs to the SAME cluster; key
material auto-syncs.

```text
Production topology:
  Cluster: cloudhsm-prod (cluster-xxx)
    ├── HSM in us-east-1a (subnet-aaa)
    ├── HSM in us-east-1b (subnet-bbb)
    └── HSM in us-east-1c (subnet-ccc) [N+2 for stricter HA]

  Key material auto-syncs. Client lib load-balances across the ENIs.
  Loss of 1 AZ = no outage (other HSMs serve).
```

**Key implication:** 2 AZs tolerates 1 AZ failure. 3 AZs tolerates
1 AZ failure during a replace (recommended production posture). Two
separate clusters in two AZs do NOT sync and do NOT count as HA.

---

## Expert heuristic: crypto officer password is NOT recoverable (quorum required)

CloudHSM has no "forgot password" flow. The Crypto Officer (CO) user
is the root-of-trust account inside the HSM. Lose the CO password
AND you've lost access to the cluster's key material. Lose quorum
(if you set quorum policies) and you've lost the ability to perform
privileged operations.

```text
Recoverability posture:
  CO password lost → key material is UNRECOVERABLE
  Quorum not met → privileged operations blocked (no override)
  Mitigations:
    ├── ≥2 CO users, each with the password in a secure offline
    │   store (Secrets Manager, KMS-encrypted vault)
    ├── Documented quorum policy (M-of-N) for destructive ops
    └── Frequent backups + cross-region copy so the worst case is
        "restore from backup into a new cluster"
```

**Key implication:** treat the CO password as a crown-jewel secret.
Maintain ≥2 COs, document rotation, and test the backup-restore
drill annually.

---

## Step 8 — PKCS#11/JCE/PCSC library integration

Workloads integrate with CloudHSM via the PKCS#11 library (C/C++),
the JCE provider (Java), or PCSC (smart-card HSM). The client
config maps the cluster CN to the cluster-ID.

```bash
# Install + configure the PKCS#11 library
sudo yum install -y cloudhsm-client-pkcs11
sudo /opt/cloudhsm/bin/configure-pkcs11 -i <cluster-id> \
  -e /opt/cloudhsm/etc/customerCA.crt

# For Java JCE: install and configure
sudo yum install -y cloudhsm-client-java
# Edit /opt/cloudhsm/java/libcloudhsm.conf to point at the cluster
```

**Constraint:** the client uses the customer CA certificate (the
one you uploaded during activation) to trust the cluster. Keep the
bundle current on every client host.

---

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

---

## Step 10 — FIPS 140-2 Level 3 compliance

AWS CloudHSM is validated to FIPS 140-2 Level 3. To maintain the
compliance posture:

- Use only Amazon-provided client libraries (PKCS#11, JCE, PCSC).
- Do NOT export key material to the workload's memory (use in-HSM
  operations).
- Maintain the audit trail: CloudTrail logs control-plane events
  (`CreateCluster`, `CreateHsm`, `InitializeCluster`,
  `CopyBackupToRegion`); the HSM logs data-plane operations (key
  use, user logins) to HSM logs.
- Restrict ENI security group inbound to workload subnets only.
- Use CO quorum for destructive operations.

```bash
# Audit CloudHSM control-plane events
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventSource,AttributeValue=cloudhsm.amazonaws.com \
  --max-results 50 --region us-east-1
```

---

## Step 11 — Network security group (sg-xxx)

The CloudHSM ENI security group is the network-isolation boundary.
Inbound rules should be the narrowest possible.

| Port | Protocol | Source | Purpose |
|---|---|---|---|
| 22 | TCP | CO bastion subnet | SSH-less management (mu) — restrict further |
| 17578 | TCP | CO bastion subnet | Management utility |
| 2223 | TCP | workload subnet | Client (PKCS#11/JCE/PCSC) |

```bash
# Tighten the SG to workload subnet CIDR only
aws ec2 authorize-security-group-ingress \
  --group-id sg-cloudhsm-prod \
  --ip-permissions IpProtocol=tcp,FromPort=2223,ToPort=2223,IpRanges=[{CidrIp=10.0.10.0/24}] \
  --region us-east-1
```

Never open `0.0.0.0/0` to CloudHSM ENIs.
