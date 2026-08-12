# EKS Security Configuration Reference

Supplementary reference for the EKS Security Optimizer skill. Loaded
on-demand when detailed CLI commands, IAM policy templates, policy
examples, or error-handling tables are needed.

## CLI commands by security dimension

### Cluster configuration inspection

```bash
# Full cluster config (endpoint, logging, encryption, OIDC)
aws eks describe-cluster --name <cluster> --output json

# Check addons (GuardDuty agent, Pod Identity agent, etc.)
aws eks list-addons --cluster-name <cluster>
aws eks describe-addon --cluster-name <cluster> --addon-name aws-guardduty-agent

# Check logging configuration
aws eks describe-cluster --name <cluster> --query 'cluster.logging.clusterLogging'
```

### Pod Security Admission

**Check current PSA labels:**
```bash
kubectl get namespaces --show-labels | grep pod-security
```

**Apply PSA profiles:**
```bash
# Baseline-enforce + restricted-audit (recommended starting point)
kubectl label namespace <ns> \
  pod-security.kubernetes.io/enforce=baseline \
  pod-security.kubernetes.io/enforce-version=latest \
  pod-security.kubernetes.io/audit=restricted \
  pod-security.kubernetes.io/audit-version=latest \
  pod-security.kubernetes.io/warn=restricted \
  pod-security.kubernetes.io/warn-version=latest

# Restricted-enforce (target for production)
kubectl label namespace <ns> \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/enforce-version=latest
```

**PSA profile reference:**

| Profile | Key restrictions |
|---|---|
| privileged | None (all capabilities, all host access) |
| baseline | No privilege escalation, no host PID/IPC/network, no added capabilities, no hostPath |
| restricted | All of baseline + runAsNonRoot required, seccompProfile required, specific caps dropped (ALL), volume types restricted |

### IRSA / Pod Identity

**Check OIDC provider:**
```bash
aws eks describe-cluster --name <cluster> \
  --query 'cluster.identity.oidc.issuer' --output text
```

**Check which service accounts use IRSA:**
```bash
kubectl get serviceaccounts -A -o jsonpath=\
  '{range .items[*]}{.metadata.namespace}{"/"}{.metadata.name}{"\t"}{.metadata.annotations.eks\.amazonaws\.com/role-arn}{"\n"}{end}'
```

**Create IAM role for IRSA:**

```bash
# Get the OIDC provider URL (without https://)
OIDC_ID=$(aws eks describe-cluster --name <cluster> \
  --query 'cluster.identity.oidc.issuer' --output text | sed 's|https://||')

# Create trust policy
cat > trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::<acct>:oidc-provider/${OIDC_ID}"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "${OIDC_ID}:sub": "system:serviceaccount:<namespace>:<service-account>"
        }
      }
    }
  ]
}
EOF

aws iam create-role --role-name <app-role> \
  --assume-role-policy-document file://trust-policy.json

# Attach permissions
aws iam put-role-policy --role-name <app-role> \
  --policy-name <app-policy> \
  --policy-document file://permissions.json

# Annotate the service account
kubectl annotate serviceaccount <sa-name> \
  eks.amazonaws.com/role-arn=arn:aws:iam::<acct>:role/<app-role> \
  -n <namespace>
```

**EKS Pod Identity (alternative):**
```bash
# Install Pod Identity agent addon
aws eks create-addon --cluster-name <cluster> \
  --addon-name eks-pod-identity-agent \
  --addon-version v1.3.0

# Create a Pod Identity association
aws eks create-pod-identity-association \
  --cluster-name <cluster> \
  --namespace <namespace> \
  --service-account <sa-name> \
  --role-arn arn:aws:iam::<acct>:role/<app-role>
```

### Network policies

**Install Calico:**
```bash
helm repo add projectcalico https://docs.projectcalico.org/charts
helm install calico projectcalico/tigera-operator \
  -n tigera-operator --create-namespace
```

**Install Cilium:**
```bash
helm repo add cilium https://helm.cilium.io/
helm install cilium cilium/cilium --namespace kube-system \
  --set kubeProxyReplacement=disabled \
  --set enableL7Proxy=false
```

**Default-deny policy:**
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Ingress
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-egress
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Egress
```

**Allow specific flows:**
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
```

### Secrets encryption (KMS)

**Check current encryption:**
```bash
aws eks describe-cluster --name <cluster> \
  --query 'cluster.encryptionConfig' --output json
```

**Enable KMS encryption:**
```bash
# Create KMS key
KEY_ID=$(aws kms create-key --description "EKS secrets encryption for <cluster>" \
  --query 'KeyMetadata.KeyId' --output text)

# Enable encryption
aws eks update-cluster-config --name <cluster> \
  --encryption-config \
    '{"resources":["secrets"],"provider":{"keyArn":"arn:aws:kms:us-east-1:<acct>:key/'$KEY_ID'"}}'
```

**Re-encrypt existing secrets:**
```bash
# After enabling KMS, re-encrypt all existing secrets
kubectl get secrets -A -o json | kubectl replace -f -
```

### Image scanning (ECR)

**Check scan configuration:**
```bash
aws ecr describe-repositories \
  --query 'repositories[].{name:repositoryName,scan:imageScanningConfiguration}'
```

**Enable scan-on-push:**
```bash
aws ecr put-image-scanning-configuration \
  --repository-name <repo> \
  --image-scanning-configuration scanOnPush=true
```

**Enable enhanced scanning (Inspector):**
```bash
aws ecr put-enhanced-image-scan-policy \
  --repository-name <repo> \
  --policy '{"enhancedScanType": "INSPECTOR"}'
```

**Check scan findings:**
```bash
aws ecr describe-image-scan-findings \
  --repository-name <repo> \
  --image-id imageTag=latest
```

### Runtime security (GuardDuty EKS)

**Enable GuardDuty EKS addon:**
```bash
aws eks create-addon --cluster-name <cluster> \
  --addon-name aws-guardduty-agent \
  --addon-version v1.0.0
```

**Check GuardDuty findings:**
```bash
aws guardduty list-findings \
  --detector-id <detector-id> \
  --filter '{"criterion":{"service.serviceName":{"eq":["EKS"]}}}'
```

### Admission policies (Gatekeeper / Kyverno)

**Install Gatekeeper:**
```bash
helm repo add gatekeeper https://open-policy-agent.github.io/gatekeeper/charts
helm install gatekeeper gatekeeper/gatekeeper \
  -n gatekeeper-system --create-namespace
```

**Install Kyverno:**
```bash
helm repo add kyverno https://kyverno.github.io/kyverno/
helm install kyverno kyverno/kyverno \
  -n kyverno-system --create-namespace
```

**Kyverno policy: disallow privileged containers:**
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: disallow-privileged-containers
spec:
  validationFailureAction: Enforce
  rules:
  - name: privileged-containers
    match:
      resources:
        kinds:
        - Pod
    validate:
      message: "Privileged containers are not allowed"
      pattern:
        spec:
          containers:
          - =(securityContext):
              =(privileged): "false"
```

### Service mesh mTLS

**Install Istio with STRICT mTLS:**
```bash
istioctl install --set values.defaultRevision=default
kubectl apply -f - <<EOF
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT
EOF
```

**Install App Mesh:**
```bash
helm appmesh install appmesh appmesh/appmesh \
  -n appmesh-system --create-namespace
```

### IMDSv2 enforcement

**Check node metadata options:**
```bash
aws ec2 describe-instances \
  --filters "Name=tag:eks:cluster-name,Values=<cluster>" \
  --query 'Reservations[].Instances[].{Id:InstanceId,IMDSType:MetadataOptions.HttpTokens,HopLimit:MetadataOptions.HttpPutResponseHopLimit}' \
  --output table
```

**Enforce IMDSv2 and set hop-limit=1:**
```bash
aws ec2 modify-instance-metadata-options \
  --instance-id <id> \
  --http-tokens required \
  --http-put-response-hop-limit 1
```

**For managed node groups, set in launch template:**
```json
{
  "MetadataOptions": {
    "HttpTokens": "required",
    "HttpPutResponseHopLimit": 1
  }
}
```

## Error-handling tables

### EKS API failures

| Failure mode | Detection | Handling |
|---|---|---|
| `describe-cluster` returns ResourceNotFoundException | API error | Cluster does not exist in region. Verify name and region. |
| `update-cluster-config` fails with InvalidParameterException | API error | KMS key ARN format incorrect or key in wrong region. |
| `create-addon` fails with ResourceInUseException | API error | Addon already installed. Use `update-addon` instead. |
| `update-cluster-config` for KMS fails with InvalidStateException | Cluster not in ACTIVE state | Wait for cluster to reach ACTIVE, retry. |

### kubectl failures

| Failure mode | Detection | Handling |
|---|---|---|
| `kubectl` connection refused | Timeout/connection error | API server endpoint is private-only and kubectl is outside VPC. Use VPN/bastion. |
| PSA label application fails | `Error from server: NotFound` | Namespace does not exist. Verify namespace name. |
| Network policy application fails | `error: unable to recognize` | Calico/Cilium CRDs not installed. Install the CNI plugin first. |
| IRSA annotation fails with no effect | Pod still uses node role | Pod must be restarted to pick up the new service account annotation. |

## Extended NEVER list

These supplement the top 5 anti-patterns in SKILL.md.

- NEVER assume VPC CNI supports NetworkPolicy. It does NOT by default.
  Install Calico or Cilium for network policy enforcement.

- NEVER apply PSA `restricted-enforce` on `kube-system`. System pods
  require privileged mode and will be rejected.

- NEVER enable KMS encryption on a cluster without planning for secret
  re-encryption. Existing secrets remain with the old encryption.

- NEVER recommend disabling the public API endpoint without verifying
  VPN/bastion access. This will immediately lock out all external kubectl.

- NEVER assume EKS Pod Identity and IRSA are mutually exclusive. They
  can coexist during migration.

- NEVER apply Kyverno/Gatekeeper policies in `Enforce` mode without
  testing in `Audit` mode first.

- NEVER modify the node IAM role to add broad permissions for a specific
  workload. Use IRSA instead.

- NEVER enable mTLS STRICT mode without first running PERMISSIVE mode
  to enroll all workloads. STRICT mode rejects non-mTLS traffic.

## Severity scoring reference

| Severity | Criteria | Examples |
|---|---|---|
| CRITICAL | Direct path to credential theft or cluster takeover | Node IAM on all pods, IMDSv1 accessible, API server unrestricted public |
| HIGH | Significant attack surface expansion | No network policies, no PSA, no KMS encryption, no image scanning |
| MEDIUM | Defense-in-depth gap | No GuardDuty runtime, no admission webhook, no mTLS, incomplete audit logging |
| LOW | Hardening recommendation | PSA warn instead of enforce, basic scan instead of enhanced, no key rotation |
