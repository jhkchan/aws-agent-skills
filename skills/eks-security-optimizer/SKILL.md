---
name: eks-security-optimizer
description: 'Optimises Amazon EKS cluster security posture across eight dimensions: pod security standards (Pod Security Admission — privileged/baseline/restricted PSS profiles enforced via admission controller replacing deprecated PodSecurityPolicy), IAM identity (IRSA — IAM Roles for Service Accounts over node IAM role for least privilege; EKS Pod Identity as the newer alternative), network policies (Calico/Cilium network policies for east-west traffic segmentation; default deny recommended), secrets encryption (KMS envelope encryption for Kubernetes secrets via --encryption-config), image scanning (ECR scan-on-push with enhanced scanning via Inspector for vulnerability detection), runtime security (GuardDuty EKS runtime monitoring for lateral movement and credential theft detection; Falco for syscall-level detection), admission webhook policies (OPA Gatekeeper / Kyverno for policy-as-code enforcement), and service mesh mTLS (App Mesh or Istio with ACM PCA for mutual TLS between pods). Reads cluster configuration vi...'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline classification works from pasted cluster configuration and kubectl output. Live-account optimization uses aws eks describe-cluster, aws eks list-addons, aws eks describe-addon, aws kms describe-key, aws ecr describe-images, aws ecr describe-image-scan-findings, aws guardduty list-findings, aws guardduty get-findings, kubectl get/describe/apply (kubectl v1.28+, AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '3'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Compute
  task_type: optimize
  skill_class: capability
  lifecycle_status: active
  verdict_shape: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
  when_to_use: Optimising EKS security posture, triaging pod security standards, evaluating IRSA vs node IAM role, implementing network policies for east-west segmentation, enabling KMS secrets encryption, configuring ECR scan-on-push, enabling GuardDuty EKS runtime monitoring, deploying OPA Gatekeeper or Kyverno admission policies, implementing service mesh mTLS, preparing for compliance audit, or hardening a cluster before production.
  when_not_to_use: EKS cluster troubleshooting (pod crashes, scheduling failures, control plane errors — use the EKS troubleshooter), EC2 security group auditing (use ec2-security-audit), IAM policy analysis for non-EKS resources (use iam-policy-analyzer), or general Kubernetes application debugging. This skill focuses on security posture optimization, not functional debugging.
  activation_triggers: optimise EKS security, EKS pod security standards, EKS IRSA configuration, EKS Pod Identity, EKS network policies, EKS secrets encryption KMS, ECR scan-on-push, GuardDuty EKS runtime, OPA Gatekeeper EKS, Kyverno EKS policies, EKS service mesh mTLS, EKS audit logging, EKS IMDSv2 enforcement, EKS privilege escalation, EKS kubelet anonymous auth, EKS API server endpoint, EKS cluster hardening, container security review, EKS compliance audit
  invocation_schema: 'Input: either (a) a cluster identifier + live-account context, (b) a kubectl configuration dump, OR (c) a security finding document (GuardDuty/Inspector/Config) with cluster details. Output: a deterministic TARGET/VERDICT/REASON/RECOMMENDATION/ SEVERITY/REMEDIATION_STEPS block per cluster, where VERDICT is one of OPTIMIZED, FURTHER_OPTIMIZATION_AVAILABLE.'
  invocation_example: 'ClusterName: prod-cluster-1

    Region: us-east-1

    KubernetesVersion: 1.30


    Pod Security Admission: not configured (no PSS profiles enforced)

    IRSA: enabled on 3 of 15 namespaces (remaining use node IAM role)

    Network Policies: none (default allow all east-west traffic)

    Secrets Encryption: KMS not configured (uses default encryption)

    ECR Image Scanning: scan-on-push disabled

    GuardDuty EKS Runtime: not enabled

    Audit Logging: enabled (api, audit, authenticator, controllerManager, scheduler)

    API Server Endpoint: public (0.0.0.0/0)

    IMDSv2: not enforced (IMDSv1 still accessible)


    Emit the standard security optimization block.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: EKS, Kubernetes, pod security, Pod Security Admission, IRSA, IAM Roles for Service Accounts, EKS Pod Identity, network policies, Calico, Cilium, secrets encryption, KMS, image scanning, ECR scan-on-push, runtime security, GuardDuty EKS, Falco, admission webhook, OPA Gatekeeper, Kyverno, service mesh, mTLS, App Mesh, ACM PCA, audit logging, IMDSv2, privilege escalation, container security, cluster hardening
  tags: eks, compute, security, kubernetes, container-security, cluster-hardening
---

# EKS Security Optimizer

## What this skill does

Translates an EKS cluster's security configuration into a concrete
hardening recommendation with severity ratings and exact remediation
steps. The verdict is the highest-leverage action across eight
dimensions — pod security standards, IAM identity, network policies,
secrets encryption, image scanning, runtime security, admission webhook
policies, and service mesh mTLS — applied in priority order by severity.
Always pairs the recommendation with exact kubectl and AWS CLI commands.

## Quick navigation

| Section | What it covers | When to jump here |
|---|---|---|
| Quick start | Five headline rules and the severity model | First read |
| Mindset | Why IRSA + PSA are the #1 levers | Understanding the approach |
| Quick reference — verdict thresholds | Decision matrix at a glance | Classifying a cluster |
| Pre-flight data gate | Cluster config, addon status, findings | Before any recommendation |
| Step 0 non-obvious behaviours | PSA replacement of PSP, Pod Identity, IMDSv2 | Edge cases |
| Step 1 Pod Security Standards | PSA privileged/baseline/restricted | Workload isolation |
| Step 2 IAM identity | IRSA vs node role vs Pod Identity | Least privilege |
| Step 3 Network policies | Calico/Cilium, default deny | East-west segmentation |
| Step 4 Secrets encryption | KMS envelope encryption | Secret protection |
| Step 5 Image scanning | ECR scan-on-push, Inspector | Vulnerability detection |
| Step 6 Runtime security | GuardDuty EKS, Falco | Threat detection |
| Step 7 Admission policies | OPA Gatekeeper / Kyverno | Policy-as-code |
| Step 8 Service mesh mTLS | App Mesh, Istio, ACM PCA | Pod-to-pod encryption |
| Step 9 Impact estimation | Severity scoring | Every recommendation |
| Output format | VERDICT block + worked examples | Emitting the result |
| Anti-Patterns — NEVER | Common misclassifications | Self-check before emit |
| Pre-flight safety checks | CONFIRM gate, canary deploy, rollback | Before any apply |

## Quick start

- **IRSA over node IAM role is the #1 IAM lever.** When all pods use
  the node IAM role, every pod has every AWS permission the node has.
  IRSA scopes IAM permissions to individual Kubernetes service accounts,
  achieving true least privilege. EKS Pod Identity (2024) is the newer,
  simpler alternative to IRSA.
- **Pod Security Admission replaced PodSecurityPolicy.** PSP was removed
  in Kubernetes 1.25. PSA enforces privileged/baseline/restricted
  profiles at the namespace level via labels. Restricted is the target
  for production workloads.
- **Default network policy is allow-all.** Without Calico or Cilium
  network policies, any pod can reach any other pod. A default-deny
  policy is the minimum baseline for production clusters.
- **KMS secrets encryption is one command.** `eks update-cluster-config
  --encryption-config` enables KMS envelope encryption for Kubernetes
  secrets. Without it, secrets are encrypted with a shared key that any
  cluster user can access.
- **IMDSv2 enforcement prevents credential theft.** Pod access to the
  node's IMDS (Instance Metadata Service) allows credential theft.
  Enforce IMDSv2 (which requires token-based requests) and set
  `hop-limit=1` to block pod access.

## Mindset

Moved verbatim to `references/advanced-patterns.md` — see "**Mindset — four principles**" (load on demand).
Applies when: you need the reasoning behind the highest-leverage-first approach.

## Quick reference — verdict thresholds

| Observation | Verdict | Recommendation |
|---|---|---|
| Pod Security Admission not configured (no PSS labels on namespaces) | **FURTHER_OPTIMIZATION_AVAILABLE** (pod security) | Step 1 — enable PSA with baseline/restricted profiles |
| Pods using node IAM role (IRSA not configured for most namespaces) | **FURTHER_OPTIMIZATION_AVAILABLE** (IAM) | Step 2 — migrate to IRSA or EKS Pod Identity |
| No network policies (default allow all east-west traffic) | **FURTHER_OPTIMIZATION_AVAILABLE** (network) | Step 3 — install Calico/Cilium, apply default deny |
| KMS secrets encryption not enabled (uses default encryption) | **FURTHER_OPTIMIZATION_AVAILABLE** (secrets) | Step 4 — enable KMS envelope encryption |
| ECR scan-on-push disabled OR images with CRITICAL findings deployed | **FURTHER_OPTIMIZATION_AVAILABLE** (images) | Step 5 — enable scan-on-push, block CRITICAL findings |
| GuardDuty EKS runtime monitoring not enabled | **FURTHER_OPTIMIZATION_AVAILABLE** (runtime) | Step 6 — enable GuardDuty EKS runtime protection |
| No admission webhook (Gatekeeper/Kyverno) for policy enforcement | **FURTHER_OPTIMIZATION_AVAILABLE** (admission) | Step 7 — deploy Gatekeeper or Kyverno with baseline policies |
| mTLS not enforced between pods (no service mesh or mutual TLS) | **FURTHER_OPTIMIZATION_AVAILABLE** (mTLS) | Step 8 — deploy App Mesh or Istio with mTLS |
| API server endpoint public (0.0.0.0/0) AND no private endpoint | **FURTHER_OPTIMIZATION_AVAILABLE** (API server) | Restrict endpoint or enable private endpoint |
| IMDSv2 not enforced (IMDSv1 accessible, hop-limit > 1) | **FURTHER_OPTIMIZATION_AVAILABLE** (IMDS) | Enforce IMDSv2, set hop-limit=1 |
| Audit logging disabled OR missing critical log types | **FURTHER_OPTIMIZATION_AVAILABLE** (logging) | Enable all log types (api, audit, authenticator, etc.) |
| All dimensions verified AND PSA enforced AND IRSA on all namespaces AND network policies in place | **OPTIMIZED** | None — continue monitoring |

## Pre-flight: data gate (run before any optimization decision)

Security assessment is only as good as the underlying data. Pull these
inputs before any recommendation. Full CLI sequences are in
`references/eks-security-config-reference.md`.

**Required data sources** (summarized — see reference for full CLI):
Moved verbatim to `references/eks-security-config-reference.md` — see "**Pre-flight data gate — required data sources**" (load on demand).
Applies when: gathering the nine pre-flight data sources on a live account.

### Data-quality short-circuits

| Condition | Effect on optimization |
|---|---|
| `describe-cluster` fails (cluster not found) | **NEED_MORE_INFO**. Verify cluster name and region. |
| kubectl not configured or context wrong | Fall back to AWS CLI only; mark network/pod findings MEDIUM confidence. |
| GuardDuty detector not enabled | Cannot assess runtime threats. Surface as finding: "enable GuardDuty." |
| ECR repository not using scan-on-push | Cannot assess image vulnerabilities. Surface as finding. |
| `logging.clusterLogging` shows disabled types | Surface as finding; cannot correlate events without audit logs. |

## Process — Optimization logic (apply in order)

### Step 0: Non-obvious behaviours that change the recommendation

These operational gotchas route a recommendation away from the obvious:

Moved verbatim to `references/advanced-patterns.md` — see "**Step 0 — non-obvious behaviours that change the recommendation**" (load on demand).
Applies when: a recommendation hinges on PSA/PSP, Pod Identity, IMDSv2 hop-limit, KMS re-encryption, audit-log cost, or IRSA audience behaviour.

### Step 1: Pod Security Standards (PSA)

PSA enforces three profiles at the namespace level via labels:

| Profile | What it blocks | Target workloads |
|---|---|---|
| privileged | Nothing (all capabilities allowed) | System namespaces (kube-system) |
| baseline | Privilege escalation, host PID/IPC, hostNetwork, additional capabilities | Non-production, legacy |
| restricted | All of baseline + runAsNonRoot required, seccomp required, specific capabilities dropped | Production workloads |

**Enforcement modes:**
- `enforce` — rejects pods that violate the profile
- `audit` — logs violations but allows the pod
- `warn` — warns the user but allows the pod

**Recommendation:** Apply `baseline` as `enforce` on all namespaces,
`restricted` as `audit` on production namespaces, and `restricted` as
`enforce` on new namespaces.

Moved verbatim to `references/eks-security-config-reference.md` — see "**Step 1 — PSA namespace labels (bash)**" (load on demand).
Applies when: applying PSA labels to a namespace.

### Step 2: IAM identity (IRSA / Pod Identity)

**Node IAM role problem:** All pods inherit the node IAM role's
permissions. If the node role has `s3:*`, every pod can access S3.

**IRSA solution:** Creates a 1:1 mapping between a Kubernetes ServiceAccount
and an IAM Role via OIDC federation. Pods using that ServiceAccount get
only the IAM role's scoped permissions.

**EKS Pod Identity (2024):** Simpler alternative to IRSA using an
agent-based approach. No OIDC provider required.

Moved verbatim to `references/eks-security-config-reference.md` — see "**Step 2 — IRSA / Pod Identity detection (bash)**" (load on demand).
Applies when: detecting which service accounts use IRSA or Pod Identity.

**Recommendation:** Migrate all non-system workloads from node IAM role
to IRSA or Pod Identity. For new clusters, use Pod Identity. For existing
clusters, migrate incrementally.

Moved verbatim to `references/eks-security-config-reference.md` — see "**Step 2 — IRSA setup (bash)**" (load on demand).
Applies when: creating an IRSA role and annotating a service account.

### Step 3: Network policies (east-west segmentation)

Without network policies, any pod can reach any other pod in the cluster.
This enables lateral movement after a single pod compromise.

Moved verbatim to `references/eks-security-config-reference.md` — see "**Step 3 — Calico/Cilium install + default-deny NetworkPolicy**" (load on demand).
Applies when: installing a network-policy CNI or applying a default-deny baseline.

Then add explicit allow rules for required flows (e.g., frontend → backend
on port 8080).

### Step 4: Secrets encryption (KMS envelope encryption)

Without KMS encryption, Kubernetes secrets are encrypted with a
cluster-wide key derivable by any etcd access. KMS envelope encryption
uses a customer-managed KMS key.

Moved verbatim to `references/eks-security-config-reference.md` — see "**Step 4 — KMS detection + enable (bash)**" (load on demand).
Applies when: detecting or enabling KMS secrets encryption.

**Important:** Existing secrets are NOT automatically re-encrypted. After
enabling, rotate secrets:
```bash
kubectl get secrets -A -o json | kubectl replace -f -
```

### Step 5: Image scanning (ECR scan-on-push)

Without image scanning, vulnerable container images are deployed without
detection.

Moved verbatim to `references/eks-security-config-reference.md` — see "**Step 5 — ECR scanning detection + enable (bash)**" (load on demand).
Applies when: detecting or enabling ECR scan-on-push / enhanced scanning.

**Block CRITICAL findings at admission:** Use Gatekeeper or Kyverno to
verify image scan status before allowing deployment.

### Step 6: Runtime security (GuardDuty EKS)

GuardDuty EKS runtime monitoring detects:
- Credential theft (IMDS access from pods)
- Lateral movement (unexpected pod-to-pod connections)
- Anomalous process execution (reverse shells, cryptominers)
- Container escape attempts

Moved verbatim to `references/eks-security-config-reference.md` — see "**Step 6 — enable GuardDuty EKS runtime (bash)**" (load on demand).
Applies when: enabling the GuardDuty EKS runtime addon.

Ensure the GuardDuty detector is enabled and EKS runtime coverage is
active in the GuardDuty console.

### Step 7: Admission webhook policies (OPA Gatekeeper / Kyverno)

Admission webhooks enforce policy-as-code at pod creation time. This is
the Kubernetes-native way to prevent misconfigured workloads.

Moved verbatim to `references/eks-security-config-reference.md` — see "**Step 7 — install Gatekeeper / Kyverno (bash)**" (load on demand).
Applies when: installing Gatekeeper or Kyverno.

**Baseline policies to enforce:**
- Disallow privileged containers
- Disallow hostPath volumes
- Require resource limits
- Require image scan verification (ECR)
- Disallow default namespace for production workloads

### Step 8: Service mesh mTLS

Service mesh mTLS encrypts pod-to-pod communication and authenticates
workload identity. Without mTLS, any pod on the network can impersonate
any other pod.

Moved verbatim to `references/eks-security-config-reference.md` — see "**Step 8 — install App Mesh / Istio (bash)**" (load on demand).
Applies when: installing a service mesh for mTLS.

**ACM PCA for certificate authority:** Use AWS Private Certificate
Authority for managed certificate issuance in the mesh.

### Step 9: Severity scoring

Score each finding by severity to prioritize remediation:

| Severity | Criteria | Examples |
|---|---|---|
| CRITICAL | Direct path to credential theft or cluster takeover | Node IAM role on all pods, IMDSv1 accessible, API server public with no restrictions |
| HIGH | Significant attack surface expansion | No network policies, no PSA, no KMS secrets encryption, no image scanning |
| MEDIUM | Defense-in-depth gap | No GuardDuty runtime, no admission webhook, no mTLS, audit logging incomplete |
| LOW | Hardening recommendation | PSA warn instead of enforce, basic scan instead of enhanced |

### Step 10: Final verdict

- Any dimension has a CRITICAL or HIGH finding → **FURTHER_OPTIMIZATION_AVAILABLE**.
- All CRITICAL/HIGH findings remediated, only MEDIUM/LOW remain → **FURTHER_OPTIMIZATION_AVAILABLE**.
- All dimensions verified (PSA enforced, IRSA on all namespaces, network policies in place, KMS encryption enabled, scanning active, GuardDuty enabled) → **OPTIMIZED**.
- Change applied and verified this session → **OPTIMIZED** (post-state).
- Data insufficient (cluster config absent, kubectl not available) → **NEED_MORE_INFO**.

## Output format

```text
TARGET: <cluster-name>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences naming the recommendation and the supporting data>
RECOMMENDATION:
  Current: <PSA status>, <IAM status>, <network policy status>, <KMS status>, <scan status>, <runtime status>
  Proposed: <specific changes per dimension>
  Dimensions changed: <psa | iam | network | secrets | images | runtime | admission | mtls>
  Dimensions checked: <list ALL eight, each ✓ (no finding) or → (finding)>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
SEVERITY: <CRITICAL | HIGH | MEDIUM | LOW>
ESTIMATED_RISK: <1-2 sentences describing the attack scenario this finding exposes>
REMEDIATION_STEPS:
  1. <specific action with CLI command>
  2. <verification step>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <cluster-name> in <region>.
  Proceed? (yes/no)"
```

Full worked examples (PSA enable, IRSA migration, network policy default
deny, already-secured, NEED_MORE_INFO, and end-to-end walkthrough) are
in `references/worked-examples.md`.

## STRICT output contract

The rules below are hard constraints. Violating any one produces a
misclassification that breaks downstream security automation. Self-check
EVERY emitted block before returning.

### Required output structure

Every response MUST be a single block using these literal labels, in this
order. Do NOT substitute markdown headings, camelCase, or bold variants.

```text
TARGET: <cluster-name>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences naming the recommendation and the supporting data>
RECOMMENDATION:
  Current: <PSA status>, <IAM status>, <network policy status>, <KMS status>, <scan status>, <runtime status>
  Proposed: <specific changes per dimension>
  Dimensions changed: <psa | iam | network | secrets | images | runtime | admission | mtls>
  Dimensions checked: <list ALL eight, each ✓ (no finding) or → (finding)>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
SEVERITY: <CRITICAL | HIGH | MEDIUM | LOW>
ESTIMATED_RISK: <1-2 sentences describing the attack scenario>
REMEDIATION_STEPS:
  1. <specific action with CLI command>
  2. <verification step>
CONFIRM: <confirmation prompt text>
```

### FORBIDDEN output patterns

1. **NEVER emit `VERDICT: FURTHER_OPTIMIZATION_AVAILABLE` without a
   SEVERITY rating.** Every finding must be scored CRITICAL/HIGH/MEDIUM/LOW.

2. **NEVER recommend a security change without verifying it won't break
   workloads.** PSA `enforce=restricted` can reject running pods. Always
   recommend `audit` mode first, then `enforce` after verifying no
   violations.

3. **NEVER emit scratch lines** ("WAIT — let me check", "Hmm, I need to
   verify") in the output. Finalize the assessment before emitting.

4. **NEVER recommend IRSA migration without identifying all IAM
   permissions each workload needs.** An IRSA role with insufficient
   permissions will cause pod failures.

5. **NEVER omit a dimension from the RECOMMENDATION block.** The
   `Dimensions checked` line MUST list all eight dimensions, each marked
   ✓ (no finding) or → (finding).

6. **NEVER recommend network policy default-deny without warning that
   it will break existing traffic flows.** Always apply in audit/test
   mode first.

7. **NEVER round severity down.** If a finding could be CRITICAL or
   HIGH, rate it CRITICAL. Under-rating security findings is worse than
   over-rating.

### Perfect example output — FURTHER_OPTIMIZATION_AVAILABLE

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

**Self-check before emit:**
- [ ] All eight dimensions listed in `Dimensions checked`?
- [ ] SEVERITY rating present and justified by ESTIMATED_RISK?
- [ ] Every `→` dimension has a corresponding REMEDIATION_STEPS entry?
- [ ] No scratch/recompute text in the block?
- [ ] PSA recommendation includes audit-mode-first guidance?

## Verdict semantics

| Verdict | When to emit |
|---|---|
| `FURTHER_OPTIMIZATION_AVAILABLE` | At least one dimension has a CRITICAL, HIGH, or MEDIUM finding. |
| `OPTIMIZED` | All dimensions verified (PSA enforced, IRSA/Pod Identity on all namespaces, network policies in place, KMS encryption enabled, scanning active, GuardDuty enabled, admission policies deployed). |
| `NEED_MORE_INFO` | Data gate failed: cluster not found, kubectl not configured, or critical config missing. |

## Anti-Patterns — NEVER (top 5)

1. **NEVER recommend PSA `enforce` mode without first running `audit`
   mode.** Enforce mode rejects pods that violate the profile, which can
   break running workloads. Always audit first, identify violations,
   fix them, then switch to enforce.

2. **NEVER recommend IRSA migration without mapping all AWS permissions
   each workload uses.** The node IAM role may grant permissions the
   workload relies on implicitly. The IRSA role must include all
   required permissions or pods will fail with AccessDenied.

3. **NEVER apply network policy default-deny in production without a
   test period.** Default-deny immediately breaks all non-explicitly-
   allowed traffic. Apply in a staging namespace first, verify flows,
   then roll out.

4. **NEVER recommend enabling KMS encryption without warning that
   existing secrets need re-encryption.** New secrets are encrypted
   with KMS, but existing secrets remain with the old encryption until
   rotated.

5. **NEVER recommend disabling the public API server endpoint without
   verifying that kubectl access is available via VPN/bastion.** Switching
   to private-only endpoint immediately breaks all external kubectl
   access.

Extended anti-patterns and error-handling tables in
`references/eks-security-config-reference.md`.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation,
  emit and await operator approval. Security changes can break workloads.
- **PSA changes require audit-first.** Never apply `enforce` without
  first running `audit` mode and resolving all violations.
- **IRSA migration requires per-workload IAM policy mapping.** Test each
  namespace independently before cutover.
- **Network policy changes require canary.** Apply in a staging namespace
  first; verify all required traffic flows before production rollout.
- **KMS encryption requires cluster update.** The cluster enters
  `UPDATING` state during the KMS config change. Plan for brief
  disruption.
- **GuardDuty addon requires node IAM permissions.** The
  `aws-guardduty-agent` addon needs permissions to communicate with
  GuardDuty. Verify the addon role before installation.
- **Gatekeeper/Kyverno policies can block deployments.** Test policies
  in `warn` or `audit` mode before switching to `deny`.
- **Service mesh mTLS rollout should be progressive.** Start with
  `permissive` mTLS mode (accept both mTLS and plaintext), then switch
  to `strict` after all workloads are enrolled.
- **Bulk-operation limit:** Process at most 3 security changes per
  batch. Sort by severity (CRITICAL first), verify each batch before
  proceeding.

## Recent AWS features (2024-2026)

Moved verbatim to `references/advanced-patterns.md` — see "**Recent AWS features (2024-2026)**" (load on demand).
Applies when: the cluster uses Pod Identity, GuardDuty runtime monitoring, ECR enhanced scanning, Auto Mode, or VPC CNI network policies.

## References

- `references/eks-security-config-reference.md` — CLI commands for each
  security dimension, IAM policy templates for IRSA, PSA label reference,
  network policy examples, Calico/Cilium install guides, KMS encryption
  setup, ECR scanning config, GuardDuty EKS setup, Gatekeeper/Kyverno
  policy examples, error-handling tables, extended NEVER list.
- `references/worked-examples.md` — full worked examples (PSA enable,
  IRSA migration, network policy default deny, KMS encryption, already-
  secured, NEED_MORE_INFO, end-to-end walkthrough).

## References (load on demand)

- [references/eks-security-config-reference.md](references/eks-security-config-reference.md) — CLI commands for each security dimension (including the per-step bash blocks moved verbatim from this file), IAM policy templates, error-handling tables, extended NEVER list.
- [references/worked-examples.md](references/worked-examples.md) — full worked examples (PSA enable, IRSA migration, network policy default deny, KMS encryption, already-secured, NEED_MORE_INFO, end-to-end walkthrough).
- [references/advanced-patterns.md](references/advanced-patterns.md) — Step 0 non-obvious behaviours, mindset principles, and recent AWS features (moved verbatim from this file).

## Domain

AWS CloudOps / EKS Container Security Optimization & Hardening.

## AWS documentation

- **EKS User Guide** — https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html
- **EKS security** — https://docs.aws.amazon.com/eks/latest/userguide/security.html
- **Pod Security Admission** — https://kubernetes.io/docs/concepts/security/pod-security-standards/
- **IRSA** — https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html
- **EKS Pod Identity** — https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html
- **EKS KMS encryption** — https://docs.aws.amazon.com/eks/latest/userguide/encrypting-secrets.html
- **ECR image scanning** — https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-scanning.html
- **GuardDuty EKS protection** — https://docs.aws.amazon.com/guardduty/latest/ug/protection-resources-eks.html
- **Calico for EKS** — https://docs.tigera.io/calico/latest/getting-started/kubernetes/eks
- **Cilium for EKS** — https://docs.cilium.io/en/latest/installation/k8s-install-helm/
- **Well-Architected Security Pillar** — https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html
