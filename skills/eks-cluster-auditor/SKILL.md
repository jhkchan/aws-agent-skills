---
name: eks-cluster-auditor
description: Audits AWS EKS cluster configurations for public API endpoint exposure, disabled control-plane logging, IAM auth mapRoles misconfiguration (system:masters to broad principals), security group ingress exposure on critical ports, and outdated Kubernetes version drift. Emits a deterministic categorical verdict per cluster. Use when reviewing EKS cluster security posture, checking API endpoint exposure, validating control-plane logging, auditing aws-auth ConfigMap, inspecting node security groups, or assessing version lifecycle status before production deployment.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline config classification. Live-account audits use aws eks describe-cluster, aws eks list-access-entries, kubectl describe configmap aws-auth -n kube-system, and aws ec2 describe-security-groups (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Compute
  verdict_shape: PUBLIC_ENDPOINT | LOGGING_DISABLED | CONFIG_GAP | OUTDATED | OK
  when_to_use: Reviewing an EKS cluster before production deployment, checking API endpoint public exposure, validating control-plane logging enablement, auditing the aws-auth ConfigMap for over-permissive IAM-to-RBAC mappings, inspecting node/cluster security group ingress rules, or assessing Kubernetes version lifecycle status.
  activation_triggers: audit this EKS cluster, is my EKS API server public, check control plane logging, audit aws-auth ConfigMap, system:masters mapping, check EKS security groups, is my Kubernetes version outdated, harden EKS cluster
  invocation_schema: 'Input: either (a) an EKS cluster configuration (describe-cluster output or equivalent JSON), optionally paired with aws-auth ConfigMap data and security group rules, OR (b) a cluster name/ARN for live-account audit. Output: deterministic CLUSTER/VERDICT/REASON/FINDINGS/REMEDIATION block per cluster, where VERDICT is one of PUBLIC_ENDPOINT, LOGGING_DISABLED, CONFIG_GAP, OUTDATED, OK.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: EKS, Kubernetes, cluster audit, public endpoint, API server, control plane logging, aws-auth, ConfigMap, mapRoles, system:masters, security group, kubelet, outdated version, Kubernetes version, endpointPublicAccess, endpointPrivateAccess, publicAccessCidrs, IRSA, node IAM role, cluster hardening, access entries
  tags: eks, kubernetes, security, cluster-audit, public-endpoint, logging, iam-auth, security-group, version-drift, audit
---

# EKS Cluster Auditor

## Mindset

**One-line takeaway:** the verdict is always the **first matching condition**
in priority order — PUBLIC_ENDPOINT beats LOGGING_DISABLED beats CONFIG_GAP
beats OUTDATED beats OK. An internet-exposed API server dwarfs every other
finding because it grants unauthenticated network access to the Kubernetes
control plane.

EKS runs a managed Kubernetes control plane inside an AWS VPC. Five
dimensions determine the cluster's security posture, and their severity is
NOT equal:

- **Public API endpoint** is the only dimension that exposes the control
  plane to the entire internet. If the API server accepts connections from
  `0.0.0.0/0`, every other control (RBAC, IAM auth, logging) is defense-in-
  depth against a network-accessible attack surface.
- **Control-plane logging** is the forensic record. With it disabled you
  cannot answer "who called what API and when" during an incident.
- **IAM auth mapRoles** is the bridge between AWS IAM and Kubernetes RBAC.
  A misconfigured `system:masters` mapping grants unrestricted cluster-admin
  to principals who should never have it.
- **Security groups** govern which IP ranges can reach the kubelet, SSH,
  and API ports on worker nodes.
- **Version drift** determines whether the control plane still receives
  security patches or has entered paid extended-support territory.

## Quick reference — verdict priority matrix

| # | Condition | Verdict | Priority |
|---|---|---|---|
| 1 | `endpointPublicAccess: true` + `publicAccessCidrs` includes `0.0.0.0/0` or is empty | **PUBLIC_ENDPOINT** | Highest |
| 2 | All control-plane log types disabled (`enabled: false` for every type) | **LOGGING_DISABLED** | |
| 3 | `aws-auth` maps `system:masters` to node IAM role, wildcard username, or broad role ARN; OR node SG allows `0.0.0.0/0` on port 10250/443/22 | **CONFIG_GAP** | |
| 4 | Cluster version is N-3 or older relative to the latest available EKS version | **OUTDATED** | |
| 5 | All dimensions pass | **OK** | Lowest |

The first matching row is the final verdict — subsequent dimensions produce
additional findings in the FINDINGS list but do not change the verdict.

## Pre-flight: cluster metadata gate (run before classification)

Several cluster attributes short-circuit the audit or change the
classification logic. Misclassifying them produces false positives.

| Attribute | Value | Effect on audit |
|---|---|---|
| `status` | `CREATING` | Cluster not yet live — skip audit, output advisory. |
| `status` | `DELETING` | Cluster is being torn down — skip audit, output advisory. |
| `resourcesVpcConfig` | absent | Fargate-only cluster with no VPC config — may still have public endpoint. Check `endpointPublicAccess` at the top level. |
| `accessConfig` | present with `authenticationMode: API` | Cluster uses **EKS access entries** instead of the `aws-auth` ConfigMap. Audit `accessEntries` (via `aws eks list-access-entries`), not the ConfigMap. |
| `accessConfig` | absent or `authenticationMode: CONFIG_MAP` | Cluster uses the legacy `aws-auth` ConfigMap. Proceed with ConfigMap audit. |

**If the cluster JSON is malformed** (invalid JSON, missing required fields
like `name` or `version`), output:

```text
CLUSTER: <name or "unknown">
VERDICT: ERROR
REASON: Cluster configuration is not valid JSON or is missing required fields — cannot classify.
REMEDIATION: Retrieve the canonical config with `aws eks describe-cluster --name <name> --output json` and re-audit.
```

## Process — Classification logic (apply in order, first match is the verdict)

### Step 0: Expert knowledge — non-obvious EKS behaviors that change classification

Step 0 expert-knowledge deep dive (empty publicAccessCidrs semantics, private+public endpoints, restricted-CIDR advisory, log-type priorities, system:masters escalation paths, kubelet port 10250, version lifecycle N-3, access entries, Fargate, 40-CIDR limit, ConfigMap non-reconciliation, async log delivery) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand before classifying edge-case cluster configurations.

### Step 1: Public API endpoint evaluation (PUBLIC_ENDPOINT)

Check `resourcesVpcConfig` (or top-level VPC config for Fargate):

1. If `endpointPublicAccess` is `false` → endpoint is private-only. No
   PUBLIC_ENDPOINT risk. Proceed to Step 2.

2. If `endpointPublicAccess` is `true`:
   - If `publicAccessCidrs` contains `"0.0.0.0/0"` OR `publicAccessCidrs`
     is empty/absent → **PUBLIC_ENDPOINT**. The API server accepts
     connections from any IP on the internet.
   - If `publicAccessCidrs` contains ONLY specific CIDRs (not
     `0.0.0.0/0`) → endpoint is network-scoped. Note as an advisory
     finding but do NOT classify as PUBLIC_ENDPOINT. Proceed to Step 2.

### Step 2: Control-plane logging evaluation (LOGGING_DISABLED)

Examine `logging.clusterLogging`:

1. If `logging` is absent or `clusterLogging` is empty → all logging is
   disabled → **LOGGING_DISABLED**.

2. If ALL entries have `enabled: false` → **LOGGING_DISABLED**.

3. If `api`, `audit`, AND `authenticator` are all `enabled: true` → logging
   dimension passes (note any missing `controllerManager`/`scheduler` as
   a minor gap in FINDINGS but do NOT trigger LOGGING_DISABLED).

4. If `api` OR `audit` OR `authenticator` is `enabled: false` (but not
   all) → partial logging gap. Classify as **CONFIG_GAP** (not
   LOGGING_DISABLED — LOGGING_DISABLED is reserved for total logging
   absence).

### Step 3: Configuration gap evaluation (CONFIG_GAP)

This step covers two sub-dimensions. If EITHER sub-dimension triggers,
the verdict is CONFIG_GAP.

#### 3a: IAM auth mapRoles / access entries

Examine `aws-auth` ConfigMap `mapRoles` (or access entries for API mode):

1. If `system:masters` is granted to the **node IAM role** → **CONFIG_GAP**.
   This is a privilege-escalation path: every pod on the node inherits
   the node's IAM identity.

2. If any mapRoles entry has `username: "*"` combined with `groups:
   ["system:masters"]` → **CONFIG_GAP**. Wildcard identity mapping to
   cluster-admin.

3. If `system:masters` is granted to a role ARN with a wildcard pattern
   (e.g., `arn:aws:iam::111:role/*`) → **CONFIG_GAP**. Broad role mapping.

4. If `system:masters` is granted to a specific, named admin role with a
   concrete username → this is the **expected pattern**. Do NOT flag.

#### 3b: Security group ingress exposure

Examine node and cluster security groups:

1. If any node SG has inbound `0.0.0.0/0` on port **10250** (kubelet)
   → **CONFIG_GAP**. The kubelet API is reachable from the internet.

2. If any node SG has inbound `0.0.0.0/0` on port **443** → **CONFIG_GAP**.
   Node HTTPS port exposed.

3. If any node SG has inbound `0.0.0.0/0` on port **22** (SSH)
   → **CONFIG_GAP**. SSH to worker nodes from the internet.

4. If inbound rules are scoped to VPC CIDRs (e.g., `10.0.0.0/16`) or
   specific corporate CIDRs → security group dimension passes.

### Step 4: Version lifecycle evaluation (OUTDATED)

Compare the cluster's `version` against the latest available EKS version
in the cluster's region:

1. If the cluster version is **N-3 or older** (3+ minor versions behind
   latest) → **OUTDATED**. The version is past or approaching end-of-
   standard-support. Extended support charges apply.

2. If the cluster version is **N-2** → advisory finding only. Note in
   FINDINGS: "Cluster is N-2 from latest — plan upgrade within standard
   support window." Do NOT trigger OUTDATED.

3. If the cluster version is **N-1 or N** (current or latest) → version
   dimension passes.

### Step 5: Aggregation — first match wins

The verdict is the **first matching condition** in priority order:

```text
if PUBLIC_ENDPOINT conditions met → verdict = PUBLIC_ENDPOINT
elif LOGGING_DISABLED conditions met → verdict = LOGGING_DISABLED
elif CONFIG_GAP conditions met → verdict = CONFIG_GAP
elif OUTDATED conditions met → verdict = OUTDATED
else → verdict = OK
```

All triggered dimensions are listed as findings regardless of which
becomes the verdict.

## Output format (per cluster)

```text
CLUSTER: <cluster-name>
VERDICT: PUBLIC_ENDPOINT | LOGGING_DISABLED | CONFIG_GAP | OUTDATED | OK
REASON: <1-2 sentences citing the worst finding and its step number>
FINDINGS:
  - [PUBLIC_ENDPOINT] <finding description (Step 1)>
  - [LOGGING_DISABLED] <finding description (Step 2)>
  - [CONFIG_GAP] <finding description (Step 3a/3b)>
  - [OUTDATED] <finding description (Step 4)>
  - [OK] <dimension that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — public endpoint with logging off

```text
CLUSTER: prod-cluster-01
VERDICT: PUBLIC_ENDPOINT
REASON: API server endpoint is public with unrestricted CIDR 0.0.0.0/0
(Step 1). Control-plane logging is also fully disabled (Step 2).
FINDINGS:
  - [PUBLIC_ENDPOINT] endpointPublicAccess: true with publicAccessCidrs:
    0.0.0.0/0 — API server reachable from the internet (Step 1)
  - [LOGGING_DISABLED] All 5 control-plane log types are disabled (Step 2)
REMEDIATION:
  1. Disable public endpoint or restrict CIDRs:
     aws eks update-cluster-config --name prod-cluster-01 \
       --resources-vpc-config endpointPublicAccess=false
  2. Enable all control-plane log types:
     aws eks update-cluster-config --name prod-cluster-01 \
       --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
```

## Anti-Patterns — NEVER

- NEVER classify a cluster with `endpointPublicAccess: true` and
  `publicAccessCidrs: ["0.0.0.0/0"]` as anything other than
  PUBLIC_ENDPOINT. An internet-reachable Kubernetes API server is the
  highest-severity finding — it exposes the control plane to
  unauthenticated network access, credential brute-force, and API-server
  CVE exploitation.

- NEVER treat an empty `publicAccessCidrs` list `[]` as "no public
  access." EKS treats an empty list as `["0.0.0.0/0"]`. This is a common
  misconfiguration where operators clear the list thinking they are
  restricting access.

- NEVER assume that `endpointPrivateAccess: true` means the public
  endpoint is off. Both can be true simultaneously. Only
  `endpointPublicAccess: false` removes the public attack surface.

- NEVER classify a cluster with restricted CIDRs on the public endpoint
  (e.g., `["203.0.113.0/24"]`) as PUBLIC_ENDPOINT. The CIDR restriction
  is a valid network-layer control. Note it as advisory and proceed to
  later steps.

- NEVER classify partially disabled logging (e.g., `controllerManager`
  off but `api`/`audit`/`authenticator` on) as LOGGING_DISABLED.
  LOGGING_DISABLED is reserved for total logging absence. Partial gaps
  are CONFIG_GAP at most.

- NEVER treat the `aws-auth` root-access mapping
  (`system:masters` to a specific admin role with a concrete username) as
  a CONFIG_GAP. This is the expected pattern for cluster administration.
  Flagging it is a false positive that causes unnecessary ConfigMap churn.

- NEVER map the EKS node IAM role to `system:masters` and consider it
  safe "because pods use IRSA." Without IRSA on a specific service account,
  every pod inherits the node IAM identity. Even with IRSA, the node role
  retains its Kubernetes identity — a pod that escapes its namespace or
  compromises the kubelet can escalate via the node's cluster-admin.

- NEVER skip auditing security groups for Fargate profiles. While
  Fargate pods do not use EC2 security groups in the traditional sense,
  the Fargate pod execution role and any associated security group
  still govern network access. Check the Fargate profile's subnet and
  security group assignments.

- NEVER assume the cluster is running the latest version without
  checking. EKS does not auto-upgrade minor versions (only patch versions
  within a minor). A cluster created 18 months ago at version 1.28 is
  still 1.28 today unless manually upgraded.

- NEVER recommend upgrading a cluster without checking add-on
  compatibility first. EKS add-ons (vpc-cni, coredns, kube-proxy) have
  version-specific compatibility matrices. Upgrading the cluster without
  upgrading add-ons first can break pod networking or DNS resolution.

- NEVER attempt to edit the `aws-auth` ConfigMap without backing it up
  first. A malformed ConfigMap can lock out ALL IAM-based access to the
  cluster. The only recovery is via the EKS API (the cluster creator
  retains implicit `system:masters`), which may require AWS Support.

- NEVER confuse EKS control-plane logs with CloudTrail. CloudTrail logs
  EKS management API calls (CreateCluster, UpdateClusterConfig). EKS
  control-plane logs capture Kubernetes API calls (create pod, exec,
  apply manifest). They are complementary, not substitutes.

- NEVER enable control-plane logging without setting a CloudWatch Logs
  retention policy. Without retention, logs accumulate indefinitely — a
  busy production cluster generates 50-200 GB/day of audit logs, and the
  CloudWatch ingestion + storage charges compound silently. Always pair
  logging enablement with `aws logs put-retention-policy` (90 days is a
  practical default; compliance frameworks may require longer).

- NEVER ignore the IAM role trust policy behind an access entry or
  `aws-auth` mapRoles entry. A `system:masters` mapping to a role whose
  trust policy allows `Principal: "*"` or a broad cross-account principal
  is a backdoor — any identity that can assume the role gains cluster-
  admin. When auditing `system:masters` mappings, always cross-reference
  the role's trust policy (`aws iam get-role --role-name <name>`) for
  wildcard or cross-account principals.

## Pre-flight safety checks (run before any remediation CLI)

Pre-flight safety checks (CONFIRM gate, aws-auth ConfigMap backup, endpoint-change blast radius, logging cost, version-upgrade prerequisites) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand before emitting or executing any remediation CLI.

## Remediation guidance

### For PUBLIC_ENDPOINT — internet-exposed API server

1. **Preferred:** disable public endpoint entirely:
   ```bash
   aws eks update-cluster-config --name <cluster> \
     --resources-vpc-config endpointPublicAccess=false,endpointPrivateAccess=true \
     --region <region>
   ```
   This restricts the API server to VPC-internal access. Ensure VPN,
   bastion, or Direct Connect connectivity before making this change.

2. **Alternative:** restrict public CIDRs to known corporate ranges:
   ```bash
   aws eks update-cluster-config --name <cluster> \
     --resources-vpc-config publicAccessCidrs=["203.0.113.0/24","198.51.100.0/24"] \
     --region <region>
   ```

3. **Verify** the change took effect:
   ```bash
   aws eks describe-cluster --name <cluster> --query 'cluster.resourcesVpcConfig.{endpointPublicAccess:endpointPublicAccess,publicAccessCidrs:publicAccessCidrs}'
   ```

### For LOGGING_DISABLED — no control-plane logs

1. Enable all five log types:
   ```bash
   aws eks update-cluster-config --name <cluster> \
     --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}' \
     --region <region>
   ```

2. Verify log groups are being created:
   ```bash
   aws logs describe-log-groups \
     --log-group-name-prefix "/aws/eks/<cluster>/cluster"
   ```

3. Set a retention policy to control costs:
   ```bash
   aws logs put-retention-policy \
     --log-group-name "/aws/eks/<cluster>/cluster/audit" \
     --retention-in-days 90
   ```

### For CONFIG_GAP — IAM auth mapRoles

1. **Node role mapped to system:masters:** remove the mapping immediately.
   Back up the ConfigMap first (see Pre-flight). The node role should be
   in `system:nodes` and `system:bootstrappers`, never `system:masters`.

2. **Wildcard username:** replace `"*"` with a specific username pattern
   (e.g., `"admin"` or `"{{SessionName}}"`).

3. **Broad role ARN:** replace wildcard patterns with the specific role
   ARN that should have admin access.

4. Apply the corrected ConfigMap:
   ```bash
   kubectl apply -f /tmp/aws-auth-corrected.yaml
   ```

5. For clusters on EKS 1.29+, migrate to access entries:
   ```bash
   aws eks create-access-entry --cluster-name <cluster> \
     --principal-arn arn:aws:iam::<account>:role/<admin-role> \
     --access-policy-arn arn:aws:eks::aws:cluster-access-policy/AML2 \
     --access-scope type=cluster
   ```

### For CONFIG_GAP — security group exposure

1. Remove `0.0.0.0/0` inbound rules on critical ports:
   ```bash
   aws ec2 revoke-security-group-ingress --group-id <sg-id> \
     --protocol tcp --port 10250 --cidr 0.0.0.0/0
   ```

2. Replace with VPC-scoped or specific CIDR rules:
   ```bash
   aws ec2 authorize-security-group-ingress --group-id <sg-id> \
     --protocol tcp --port 10250 --cidr 10.0.0.0/16
   ```

3. For SSH access, use AWS Systems Manager Session Manager instead of
   opening port 22:
   ```bash
   aws ssm start-session --target <instance-id>
   ```

### For OUTDATED — version past standard support

1. Check available versions:
   ```bash
   aws eks describe-addon-versions --kubernetes-version <target> \
     --query 'addons[].addonName'
   ```

2. Upgrade add-ons FIRST (before cluster version):
   ```bash
   aws eks update-addon --cluster-name <cluster> --addon-name vpc-cni \
     --addon-version <compatible-version> --resolve-conflicts OVERWRITE
   ```

3. Upgrade the cluster:
   ```bash
   aws eks update-cluster-version --name <cluster> \
     --kubernetes-version <target-version>
   ```

4. Wait for the update to complete (10-30 minutes), then verify:
   ```bash
   aws eks describe-cluster --name <cluster> \
     --query 'cluster.version'
   ```

### For OK

1. No remediation required for the current posture.
2. Recommend periodic re-audit (quarterly) as new versions are released.
3. Consider enabling EKS Auto Mode or Karpenter for node lifecycle
   management to reduce operational overhead.

## Recent AWS features (2024-2026)

Recent AWS features (EKS access entries, Auto Mode, Pod Identity, Hybrid Nodes, PSS) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when auditing clusters on recent EKS versions.

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — Step 0 expert-knowledge deep dive and Recent AWS features (2024-2026), moved from SKILL.md
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — pre-flight safety checks (run before any remediation CLI), moved from SKILL.md

## Domain

AWS CloudOps / EKS Compute Security & Compliance.

## AWS documentation

- **Amazon EKS User Guide** — https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html
- **EKS Security** — https://docs.aws.amazon.com/eks/latest/userguide/security.html
- **EKS API Reference** — https://docs.aws.amazon.com/eks/latest/APIReference/
- **EKS CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/eks/
- **EKS Access Entries** — https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html
- **EKS Pod Identity** — https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html
