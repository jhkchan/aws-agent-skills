# Cluster Activation and Crypto Officer Management — CloudHSM Cluster Deployer

Deep reference on the one-time cluster activation flow (CSR fetch,
sign, upload), the customer CA as permanent trust root, crypto
officer (CO) and crypto user (CU) management via the management
utility (mu) and key_mgmt_util (ku), password policies, quorum, and
the CO password non-recoverability posture. Loaded on demand by the
skill — kept out of the main SKILL.md body so the provisioning
procedure stays scannable.

## The activation flow

Activation is the one-time gate between `create-hsm` (first HSM in
the cluster) and any CO/user management or crypto operations.

```text
Cluster state lifecycle:
  CreateCluster → Uninitialized
  CreateHsm (first) → ACTIVATING (HSM emits CSR)
  Download CSR → sign with your CA → upload signed cert + CA cert
  AWS verifies → cluster becomes ACTIVE
  Once ACTIVE: activation is ONE-TIME. The customer certificate is
  the trust root for every subsequent HSM in the cluster.
```

### Fetching the CSR

```bash
aws cloudhsmv2 describe-clusters \
  --filters clusterIds=$CLUSTER_ID \
  --query 'Clusters[0].Certificates.ClusterCertificate' \
  --output text --region us-east-1 > cluster.csr
```

### Signing the CSR with your in-house CA

```bash
openssl x509 -req -days 3650 -in cluster.csr \
  -CA customerCA.crt -CAkey customerCA.key -set_serial 01 \
  -out customerCertificate.crt
```

For a bootstrap environment, you can self-sign
(`customerCA.crt` and `customerCertificate.crt` may be the same
self-signed pair). For production, use your in-house CA so the
trust chain is real.

### Uploading the signed cert + CA cert

```bash
aws cloudhsmv2 initialize-cluster \
  --cluster-id "$CLUSTER_ID" \
  --signed-cert fileb://customerCertificate.crt \
  --trust-anchor fileb://customerCA.crt \
  --region us-east-1
```

After upload, the cluster state transitions to INITIALIZED → ACTIVE.
At that point the customer certificate is the cluster's permanent
trust root; every subsequent HSM added to the cluster inherits it.

### Changing the customer CA later

Activation is one-time. To change the CA, restore from backup into
a NEW cluster under the new CA. There is no re-initialize API.

## Crypto officer (CO) and crypto user (CU) management

CloudHSM has two privileged user classes:

- **Crypto Officer (CO):** root-of-trust inside the HSM. Can create
  users, manage key policies, set quorum, take backups.
- **Crypto User (CU):** owns and uses keys. Created by a CO. Cannot
  manage other users.

A cluster has at least one CO (`admin`) created at activation time.
Additional COs are created via `cloudhsm_mgmt_util` (mu).

### Configuring the client + starting mu

```bash
# Point the CloudHSM client at the cluster's primary ENI
sudo /opt/cloudhsm/bin/configure -a 10.0.1.10

# Start the management utility (mu)
/opt/cloudhsm/bin/cloudhsm_mgmt_util /opt/cloudhsm/etc/cloudhsm_mgmt_util.cfg
```

### CO commands inside mu

```text
loginHSM CO admin <password-from-secrets-manager>
createUser CO officer2 <password>
createUser CU app-tls-user <password>
createUser CU app-code-sign-user <password>
changePswd CO admin <new-password>
listUsers
quit
```

The `admin` CO password is the cluster's crown-jewel secret. Store
it in AWS Secrets Manager encrypted with a customer-managed KMS key.
Rotate on a fixed cadence (e.g., 90 days).

### Password policy

Per-cluster policy is enforced per-HSM and propagates via the
cluster sync. Set via mu:

```text
setPasswordPolicies CO 14 0 1 1 1   # min 14 chars, no reuse, mixed
```

CU passwords follow the same policy pattern.

## Quorum

Quorum requires M-of-N COs to approve destructive operations (key
deletion, user deletion). Without quorum, the operation is blocked
with NO override.

```text
Inside mu (after loginHSM as CO):
  setQuorum M 2                      # 2-of-N required
  assignQuorumTokens CO officer2 1   # token 1
  assignQuorumTokens CO admin 2      # token 2
```

**Recoverability:** if quorum cannot be met (CO users lost, tokens
lost), the destructive operations are blocked indefinitely. Mitigate
with ≥2 COs, secure token storage, and an annual restore drill.

## CO password is NOT recoverable

CloudHSM has NO "forgot password" flow. Lose the CO password AND
the cluster's key material is unrecoverable.

```text
Recoverability posture:
  CO password lost → key material is UNRECOVERABLE
  Quorum not met → privileged operations blocked (no override)
```

Mitigations:

1. ≥2 CO users, each with the password in a secure offline store
   (Secrets Manager, KMS-encrypted vault).
2. Documented quorum policy (M-of-N) for destructive operations.
3. Frequent backups + cross-region copy so the worst case is
   "restore from backup into a new cluster."
4. Annual restore drill to verify the path works.

## Terraform example

```hcl
resource "aws_cloudhsm_v2_cluster" "prod" {
  hsm_type        = "hsm1.medium"
  subnet_ids      = [aws_subnet.cloudhsm_a.id, aws_subnet.cloudhsm_b.id, aws_subnet.cloudhsm_c.id]
  security_group_id = aws_security_group.cloudhsm.id

  tags = {
    Environment = "production"
    Workload    = "tls-offload"
  }
}

resource "aws_cloudhsm_v2_hsm" "a" {
  cluster_id    = aws_cloudhsm_v2_cluster.prod.cluster_id
  subnet_id     = aws_subnet.cloudhsm_a.id
  ip_address    = "10.0.1.10"
  availability_zone = "us-east-1a"
}

resource "aws_cloudhsm_v2_hsm" "b" {
  cluster_id    = aws_cloudhsm_v2_cluster.prod.cluster_id
  subnet_id     = aws_subnet.cloudhsm_b.id
  ip_address    = "10.0.2.10"
  availability_zone = "us-east-1b"
}

# NOTE: activation (initialize-cluster) and CO/user management are
# NOT yet first-class Terraform resources. They must be performed
# via the CloudHSM client tools after Terraform apply.
```

## Common pitfalls

1. **Treating activation as repeatable.** The customer certificate
   is the permanent trust root. To change CAs, restore from backup
   into a new cluster.

2. **Single CO.** Lose the CO + lose quorum = lose key material.
   Maintain ≥2 COs.

3. **CO password in plaintext.** Use Secrets Manager encrypted with
   a customer-managed KMS key.

4. **Skipping the customer CA bundle on the client host.** The
   client uses `/opt/cloudhsm/etc/customerCA.crt` to trust the
   cluster. Wrong bundle = TLS failure.

5. **Forgetting the quorum token drill.** Quorum is useless if no
   one knows how to meet it under pressure. Run an annual drill.

---

## Step 4 — Crypto officer/user management

Once the cluster is ACTIVE, log in via the CloudHSM management util
(`cloudhsm_mgmt_util`, aliased `mu`) over the ENI to create the
first Crypto Officer (CO) and Crypto Users (CU).

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
  in AWS Secrets Manager (encrypted with a customer-managed KMS key).
- Create ≥2 CO users so you have quorum if one is lost.
- CUs own and use keys; created by COs; scoped to the cluster.
- Password policies (length, complexity) propagate via cluster sync.

---

## Step 12 — CN-to-cluster-ID mapping

The CloudHSM client uses the cluster's Common Name (CN) to verify
the cluster during TLS handshake. The mapping is registered in the
client config (`configure -a <eni-ip>` or DNS CNAME).

```bash
# Point the client at the cluster's primary ENI
sudo /opt/cloudhsm/bin/configure -a 10.0.1.10
# Or DNS CNAME: cloudhsm.internal.example.com → 10.0.1.10
```

If the mapping is wrong, the client fails the TLS handshake. Verify
the customer CA bundle is current on the client host.
