# Example usage: eks-security-optimizer

A walkthrough showing the skill assessing a production EKS cluster with
multiple security gaps, demonstrating the severity-based prioritization,
eight-dimension analysis, IRSA-specific remediation, and the staged
migration with audit-first PSA rollout.

## Input (user prompt)

> Assess our production EKS cluster before the upcoming SOC 2 compliance
> audit. I need to know what security gaps exist and how to fix them.

```text
ClusterName: prod-eks-main
Region: us-east-1
KubernetesVersion: 1.30

Pod Security Admission: not configured (no PSS labels on namespaces)
IRSA: enabled on 3 of 15 namespaces (remaining 12 use node IAM role)
Network Policies: none (default allow all east-west traffic)
Secrets Encryption: KMS not configured (uses default encryption)
ECR Image Scanning: scan-on-push enabled (enhanced scanning via Inspector)
GuardDuty EKS Runtime: enabled (aws-guardduty-agent addon active)
Admission Webhook: OPA Gatekeeper deployed (8 policies enforced)
Service Mesh mTLS: not configured (no App Mesh or Istio)
Audit Logging: enabled (api, audit, authenticator, controllerManager, scheduler)
API Server Endpoint: public (0.0.0.0/0) with private endpoint also enabled
IMDSv2: enforced (HttpPutResponseHopLimit=1)
```

## Skill output

```text
TARGET: prod-eks-main
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
     aws eks update-cluster-config --name prod-eks-main --encryption-config '{...}'
  5. Enable mTLS via App Mesh (MEDIUM priority, can be phased):
     helm install appmesh appmesh/appmesh -n appmesh-system --create-namespace
CONFIRM: About to apply security hardening on prod-eks-main (PSA, IRSA,
  network policies, KMS encryption). This will require pod restarts in
  12 namespaces. Proceed? (yes/no)
```

## What the skill caught that a generic assistant misses

1. **Severity scoring drives prioritization.** A generic assistant lists
   all gaps equally. The skill scores the node IAM role as CRITICAL
   (direct credential theft path), no network policies as HIGH (lateral
   movement), and mTLS absence as MEDIUM (defense-in-depth), so the
   operator knows what to fix first.

2. **PSA audit-first rollout.** A generic assistant says "enable PSA
   restricted-enforce." The skill warns that enforce mode rejects running
   pods and recommends audit mode first to identify violations before
   switching to enforce.

3. **IRSA requires per-workload IAM mapping.** A generic assistant says
   "set up IRSA." The skill identifies that each of the 12 namespaces
   needs a scoped IAM role with the specific permissions that workload
   uses, and recommends auditing CloudTrail to determine those
   permissions.

4. **Network policy default-deny breaks traffic.** A generic assistant
   says "apply default-deny." The skill warns that default-deny
   immediately blocks all non-explicitly-allowed traffic and
   recommends testing in staging first.

5. **KMS requires secret re-encryption.** A generic assistant says
   "enable KMS." The skill notes that existing secrets are not
   automatically re-encrypted and must be rotated via
   `kubectl get secrets -A -o json | kubectl replace -f -`.

6. **All eight dimensions verified.** The skill explicitly checks images,
   runtime, and admission (all passing) alongside the failing dimensions.
   The operator can see the full posture in one block, not just the gaps.

## Slash-command invocation

```
/aws:optimize-eks-security
```

Or via the orchestrator:

```
/aws:pipeline
You: "assess our EKS cluster security for the SOC 2 audit"
```

The orchestrator emits
`[Phase: Optimize | Skills routed: eks-security-optimizer]` and hands off
to this skill for the assessment block.

## Live-account follow-up (optional, requires AWS CLI + kubectl)

After remediating, validate the new configuration:

```bash
# Verify PSA labels are applied
kubectl get namespaces --show-labels | grep pod-security

# Verify IRSA annotations on service accounts
kubectl get serviceaccounts -A -o jsonpath=\
  '{range .items[*]}{.metadata.namespace}{"/"}{.metadata.name}{"\t"}{.metadata.annotations.eks\.amazonaws\.com/role-arn}{"\n"}{end}'

# Verify Calico network policies exist
kubectl get networkpolicies -A

# Verify KMS encryption is enabled
aws eks describe-cluster --name prod-eks-main \
  --query 'cluster.encryptionConfig' --output json

# Check GuardDuty findings post-hardening (should decrease)
aws guardduty list-findings \
  --detector-id <detector-id> \
  --filter '{"criterion":{"service.serviceName":{"eq":["EKS"]}}}'
```

If pod failures occur after IRSA migration, verify the IAM role has all
required permissions by checking CloudTrail for AccessDenied events from
the pod's assumed role.

## Fleet-wide extension

For a fleet of N EKS clusters, run the skill in batch mode:

1. List all clusters with `aws eks list-clusters`.
2. For each, pull configuration via `aws eks describe-cluster`.
3. For each, pull pod-level config via `kubectl` (requires kubeconfig).
4. Score each cluster by severity (CRITICAL findings count).
5. Sort clusters by CRITICAL + HIGH finding count (highest first).
6. Slice into batches of 3 clusters.
7. For each batch: emit per-cluster REMEDIATION_STEPS, then a single
   CONFIRM for the batch.
8. Verify each batch before proceeding to the next.
9. After all batches, produce a fleet-wide posture summary.
