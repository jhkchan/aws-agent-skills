# Worked Examples — EKS Security Optimizer

Full worked examples covering PSA enable, IRSA migration, network policy
default-deny, KMS encryption enable, already-secured cluster,
NEED_MORE_INFO, and an end-to-end security hardening walkthrough. Loaded
on demand — kept out of the main SKILL.md body so the procedure stays
scannable.

## Worked example — multi-dimension CRITICAL (PSA + IRSA + network)

```text
TARGET: prod-cluster-1
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Production EKS cluster with no Pod Security Admission enforcement,
  12 of 15 namespaces using node IAM role instead of IRSA, and no network
  policies. A single pod compromise allows full cluster takeover via node
  IAM credentials and unrestricted lateral movement.
RECOMMENDATION:
  Current: PSA not configured, node IAM on 12/15 namespaces, no network policies, KMS not configured
  Proposed: PSA baseline-enforce on all namespaces, IRSA on all non-system namespaces, Calico default-deny, KMS secrets encryption
  Dimensions changed: psa (Step 1) + iam (Step 2) + network (Step 3) + secrets (Step 4)
  Dimensions checked: psa → (not configured)  iam → (node role on 12 ns)
    network → (no policies)  secrets → (no KMS)  images ✓ (scan-on-push enabled)
    runtime ✓ (GuardDuty enabled)  admission ✓ (Gatekeeper deployed)  mtls → (no mTLS)
  Confidence: HIGH — cluster config verified via describe-cluster + kubectl
    inspection; all findings confirmed against live state.
SEVERITY: CRITICAL
ESTIMATED_RISK: Node IAM role on all pods means any pod can assume the
  node's AWS permissions. Combined with no network policies, an attacker
  who compromises one pod can access all AWS resources the node IAM role
  permits and move laterally to any other pod in the cluster.
REMEDIATION_STEPS:
  1. Enable PSA baseline-enforce on all non-system namespaces:
     kubectl label namespace <ns> pod-security.kubernetes.io/enforce=baseline
  2. Create IRSA roles for the 12 namespaces and annotate service accounts:
     kubectl annotate sa <sa> eks.amazonaws.com/role-arn=<role-arn> -n <ns>
  3. Install Calico and apply default-deny per namespace:
     helm install calico projectcalico/tigera-operator -n tigera-operator --create-namespace
  4. Enable KMS secrets encryption:
     aws eks update-cluster-config --name prod-cluster-1 --encryption-config '{...}'
  5. Enable mTLS via App Mesh (MEDIUM priority, can be phased):
     helm install appmesh appmesh/appmesh -n appmesh-system --create-namespace
CONFIRM: About to apply security hardening on prod-cluster-1 (PSA, IRSA,
  network policies, KMS encryption). This will require pod restarts in
  12 namespaces. Proceed? (yes/no)
```

## Worked example — IRSA migration (single dimension)

```text
TARGET: staging-cluster-2
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Cluster has strong posture except 16 of 20 namespaces still use
  the node IAM role. All pods in those namespaces inherit the node's AWS
  permissions, bypassing least privilege. Other dimensions (PSA, network,
  KMS, scanning, runtime, admission, mTLS) are all properly configured.
RECOMMENDATION:
  Current: PSA baseline-enforce ✓, Calico default-deny ✓, KMS ✓, but node IAM on 16/20 namespaces
  Proposed: IRSA on all 20 non-system namespaces with scoped IAM roles
  Dimensions changed: iam (Step 2)
  Dimensions checked: psa ✓ (baseline-enforce)  iam → (node role on 16 ns)
    network ✓ (Calico default-deny)  secrets ✓ (KMS enabled)
    images ✓ (enhanced scanning)  runtime ✓ (GuardDuty enabled)
    admission ✓ (Kyverno 12 policies)  mtls ✓ (Istio STRICT)
  Confidence: HIGH — all other dimensions verified; only IAM gap remains.
SEVERITY: HIGH
ESTIMATED_RISK: Workloads in 16 namespaces have unrestricted access to
  all AWS resources the node IAM role permits. A compromised pod can
  read/write S3, invoke Lambda, modify DynamoDB, or pivot to other AWS
  services without additional exploitation.
REMEDIATION_STEPS:
  1. For each of the 16 namespaces, identify required AWS permissions by
     auditing CloudTrail for the node IAM role's actual API calls.
  2. Create a scoped IAM role per namespace with the OIDC trust policy.
  3. Annotate each namespace's service account:
     kubectl annotate sa <sa> eks.amazonaws.com/role-arn=<role-arn> -n <ns>
  4. Restart pods to pick up new credentials:
     kubectl rollout restart deployment <deployment> -n <ns>
  5. Verify pods function correctly with scoped permissions.
  6. After all 16 namespaces are migrated, remove unnecessary permissions
     from the node IAM role.
CONFIRM: About to migrate 16 namespaces from node IAM to IRSA. This
  requires per-namespace IAM policy mapping and pod restarts. Proceed? (yes/no)
```

## Worked example — network policy default-deny

```text
TARGET: api-cluster-3
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Cluster has good IAM posture (IRSA on all namespaces) and PSA
  configured, but no network policies — default allow all east-west
  traffic. A compromised pod can reach any other pod in the cluster
  without restriction.
RECOMMENDATION:
  Current: IRSA ✓, PSA ✓, but no network policies (default allow all)
  Proposed: Install Cilium, apply default-deny per namespace, add explicit allow rules
  Dimensions changed: network (Step 3)
  Dimensions checked: psa ✓ (restricted-enforce)  iam ✓ (IRSA on all ns)
    network → (no policies)  secrets ✓ (KMS enabled)
    images ✓ (enhanced scanning)  runtime ✓ (GuardDuty enabled)
    admission ✓ (Gatekeeper 10 policies)  mtls → (App Mesh permissive, not strict)
  Confidence: HIGH — verified no Calico/Cilium CRDs present; all other
    dimensions confirmed.
SEVERITY: HIGH
ESTIMATED_RISK: Without network policies, any pod can reach any other pod
  on any port. This enables lateral movement after a single pod
  compromise. Combined with App Mesh in permissive mode (no mTLS
  enforcement), traffic is also unauthenticated and unencrypted.
REMEDIATION_STEPS:
  1. Install Cilium:
     helm install cilium cilium/cilium --namespace kube-system
  2. Apply default-deny in each namespace (staging first):
     kubectl apply -f default-deny.yaml -n staging
  3. Add explicit allow rules for known traffic flows:
     frontend → backend:8080, backend → database:5432
  4. Monitor for 7 days; investigate any broken connections.
  5. Roll out default-deny to production namespaces.
  6. Switch App Mesh from permissive to STRICT mTLS mode.
CONFIRM: About to install Cilium and apply network policies on
  api-cluster-3. Default-deny will immediately block unallowed traffic.
  Testing in staging first. Proceed? (yes/no)
```

## Worked example — KMS + IMDSv2 gaps

```text
TARGET: data-cluster-4
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Cluster has good pod-level security (PSA, IRSA, Cilium network
  policies) but missing infrastructure-level controls: no KMS secrets
  encryption and IMDSv2 not enforced (hop-limit=2 allows pod access to
  node metadata service).
RECOMMENDATION:
  Current: Pod-level security ✓, but no KMS encryption and IMDSv1 accessible
  Proposed: Enable KMS secrets encryption, enforce IMDSv2 with hop-limit=1
  Dimensions changed: secrets (Step 4) + IMDSv2 (infrastructure)
  Dimensions checked: psa ✓ (baseline-enforce)  iam ✓ (IRSA on all ns)
    network ✓ (Cilium default-deny)  secrets → (no KMS)
    images ✓ (enhanced scanning)  runtime ✓ (GuardDuty enabled)
    admission ✓ (Gatekeeper 8 policies)  mtls ✓ (Istio STRICT)
  Confidence: HIGH — KMS absence confirmed in describe-cluster; IMDSv2
    gap confirmed via describe-instances metadata options.
SEVERITY: HIGH
ESTIMATED_RISK: Without KMS encryption, anyone with etcd access can read
  all Kubernetes secrets (database passwords, API keys, tokens). IMDSv1
  access allows pod-level SSRF attacks to steal node IAM credentials,
  bypassing the IRSA isolation already in place.
REMEDIATION_STEPS:
  1. Create a KMS key and enable secrets encryption:
     aws kms create-key --description "EKS secrets for data-cluster-4"
     aws eks update-cluster-config --name data-cluster-4 \
       --encryption-config '{"resources":["secrets"],"provider":{"keyArn":"..."}}'
  2. Re-encrypt existing secrets:
     kubectl get secrets -A -o json | kubectl replace -f -
  3. Enforce IMDSv2 on all nodes:
     aws ec2 modify-instance-metadata-options --instance-id <id> \
       --http-tokens required --http-put-response-hop-limit 1
  4. Update the node group launch template to include IMDSv2 settings
     for future node replacements.
  5. Verify no pods rely on IMDSv1 access (check for metadata service
     calls in application logs).
CONFIRM: About to enable KMS secrets encryption and enforce IMDSv2 on
  data-cluster-4. KMS requires cluster update (brief UPDATING state).
  IMDSv2 change requires node rolling update. Proceed? (yes/no)
```

## Worked example — already secured

```text
TARGET: secure-prod-cluster-5
VERDICT: OPTIMIZED
REASON: All eight security dimensions verified: PSA restricted-enforce
  on all non-system namespaces, IRSA on all 20 non-system namespaces,
  Calico default-deny with explicit allow rules, KMS encryption with
  rotation, ECR enhanced scanning with CRITICAL block via Kyverno,
  GuardDuty EKS runtime active, Kyverno with 15 enforced policies, Istio
  STRICT mTLS, private API server, IMDSv2 enforced.
RECOMMENDATION:
  Current: All dimensions secured — no change
  Dimensions checked: psa ✓ (restricted-enforce)  iam ✓ (IRSA 20/20)
    network ✓ (Calico default-deny)  secrets ✓ (KMS + rotation)
    images ✓ (enhanced + CRITICAL block)  runtime ✓ (GuardDuty active)
    admission ✓ (Kyverno 15 policies)  mtls ✓ (Istio STRICT)
  Confidence: HIGH — all dimensions verified via describe-cluster,
    kubectl inspection, and describe-instances.
SEVERITY: N/A
ESTIMATED_RISK: No critical or high-risk findings. Cluster is hardened
  to defense-in-depth baseline.
REMEDIATION_STEPS:
  - None required. Re-evaluate quarterly or after major cluster changes.
    Monitor GuardDuty findings continuously.
```

## Worked example — NEED_MORE_INFO

```text
TARGET: unknown-cluster
VERDICT: NEED_MORE_INFO
REASON: Cluster configuration could not be retrieved. The cluster name
  may be incorrect, the region may differ, or IAM may deny
  eks:DescribeCluster. Cannot assess security posture without cluster
  configuration data.
RECOMMENDATION:
  Current: unknown configuration — pending data
  Proposed: pending data
  Confidence: LOW — no metrics to evaluate.
SEVERITY: N/A
ESTIMATED_RISK: Unknown — cannot assess without cluster configuration.
REMEDIATION_STEPS:
  1. Verify the cluster name and region:
     aws eks list-clusters --region <region>
  2. Verify IAM permissions for eks:DescribeCluster:
     aws iam get-role-policy --role-name <role> --policy-name <policy>
  3. Once cluster config is retrieved, re-evaluate all eight dimensions.
  Do NOT assess security based on assumed configuration.
```

## End-to-end hardening walkthrough

This example walks through the complete workflow: assess all dimensions,
identify gaps by severity, prioritise remediation, and provide staged
migration steps.

**Cluster profile:**
- Cluster: `legacy-prod-cluster`
- Version: 1.30
- Region: us-east-1
- Pod Security Admission: not configured
- IRSA: 2 of 12 namespaces (10 use node IAM)
- Network Policies: none
- KMS Encryption: not configured
- ECR Scanning: basic scan (not enhanced)
- GuardDuty: detector enabled but EKS runtime addon not installed
- Admission Webhook: none
- mTLS: none
- Audit Logging: api + audit only (missing 3 types)
- API Server: public (0.0.0.0/0)
- IMDSv2: not enforced (hop-limit=2)

**Step 1 — Assess severity per dimension:**
```
PSA:        CRITICAL (no pod security enforcement)
IRSA:       CRITICAL (node IAM on 10/12 namespaces)
Network:    HIGH (no network policies, default allow all)
KMS:        HIGH (no secrets encryption)
Images:     MEDIUM (basic scan, no enhanced)
Runtime:    MEDIUM (detector enabled but no EKS addon)
Admission:  MEDIUM (no policy enforcement)
mTLS:       MEDIUM (no pod-to-pod encryption)
Audit:      MEDIUM (missing 3 of 5 log types)
API Server: HIGH (unrestricted public endpoint)
IMDSv2:     CRITICAL (credential theft via SSRF)
```

**Step 2 — Prioritise by severity:**
```
Phase 1 (CRITICAL): IMDSv2 enforcement, IRSA migration, PSA enable
Phase 2 (HIGH): Network policies, KMS encryption, API server restriction
Phase 3 (MEDIUM): GuardDuty addon, enhanced scanning, admission policies, mTLS, audit logging
```

**Step 3 — Phase 1 remediation:**
```bash
# IMDSv2 enforcement (per node)
aws ec2 modify-instance-metadata-options --instance-id <id> \
  --http-tokens required --http-put-response-hop-limit 1

# PSA enable (audit first, then enforce)
kubectl label namespace default \
  pod-security.kubernetes.io/audit=baseline \
  pod-security.kubernetes.io/warn=baseline
# After verifying no violations:
kubectl label namespace default \
  pod-security.kubernetes.io/enforce=baseline

# IRSA migration (per namespace)
# ... create roles, annotate service accounts, restart pods ...
```

**Step 4 — Phase 2 remediation:**
```bash
# Network policies
helm install calico projectcalico/tigera-operator -n tigera-operator --create-namespace
kubectl apply -f default-deny.yaml -n <namespace>

# KMS encryption
aws eks update-cluster-config --name legacy-prod-cluster \
  --encryption-config '{"resources":["secrets"],"provider":{"keyArn":"..."}}'
```

**Step 5 — Emit final assessment:** (after all phases complete, the
cluster would emit VERDICT: OPTIMIZED with all eight dimensions ✓)
