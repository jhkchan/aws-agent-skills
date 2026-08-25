---
name: eks-add-on-deployer
description: 'Provisions Amazon EKS add-ons with production defaults: add-on types (vpc-cni, coredns, kube-proxy, aws-ebs-csi-driver, metrics-server, adot, guardduty-agent), version management (EKS-managed vs self-managed add-ons and conflict resolution), configuration values (override existing add-on config via --configuration-values), IAM roles for service accounts (IRSA), EKS Pod Identity (newest credential method), EKS Auto Mode add-ons (auto-managed lifecycle), and EKS Hybrid Nodes add-on support. Emits a READY_TO_DEPLOY checklist with verification commands. Use when provisioning EKS add-ons, resolving EKS-managed vs self-managed conflicts, configuring IRSA for add-ons, migrating to EKS Pod Identity, or enabling EKS Auto Mode add-ons. Triggers: create EKS add-on, vpc-cni, coredns, kube-proxy, aws-ebs-csi-driver, EKS Pod Identity, EKS Auto Mode, EKS Hybrid Nodes, IRSA add-on, adot guardduty-agent, metrics-server EKS.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with eks, iam access. Works with Terraform aws_eks_add_on resource and CloudFormation AWS::EKS::Addon templates. Requires kubectl for post-deploy verification.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Compute
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, eks, kubernetes, addon, compute, cloudops, deploy, provisioning, irsa, eks-pod-identity, eks-auto-mode
  dependencies: aws-orchestrator
  keywords: aws, eks, kubernetes, add-on, addon, vpc-cni, coredns, kube-proxy, aws-ebs-csi-driver, metrics-server, adot, guardduty-agent, cloudops, deploy, provisioning, irsa, iam roles for service accounts, eks pod identity, eks auto mode, eks hybrid nodes, configuration values
  when_to_use: Invoke when the user wants to create or update EKS add-ons (vpc-cni, coredns, kube-proxy, aws-ebs-csi-driver, metrics-server, adot, guardduty-agent), resolve EKS-managed vs self-managed add-on conflicts, configure IAM roles for add-ons (IRSA or EKS Pod Identity), set add-on configuration values, enable EKS Auto Mode add-ons, or deploy add-ons for EKS Hybrid Nodes. Do NOT invoke for creating the EKS cluster itself (use eks-cluster-deployer if available), for installing Helm charts that are not EKS add-ons, for self-managed Kubernetes controllers outside the EKS add-on framework, or for auditing EKS add-on versions (use eks-cluster-auditor).
---

# EKS Add-On Deployer

An AWS CloudOps agent skill that provisions Amazon EKS add-ons with
correct defaults. Walks the operator through add-on type selection,
version management, IAM role configuration, configuration values, and
conflict resolution, and emits a READY_TO_DEPLOY checklist with
verification commands.

## Activation keywords

create EKS add-on, vpc-cni EKS add-on, coredns EKS add-on, kube-proxy
EKS add-on, aws-ebs-csi-driver EKS, metrics-server EKS, adot EKS
add-on, guardduty-agent EKS, EKS Pod Identity add-on, EKS Auto Mode
add-on, EKS Hybrid Nodes add-on, IRSA EKS add-on, EKS add-on
configuration values, EKS-managed vs self-managed add-on.

## STRICT output contract

When this skill is invoked with an EKS-add-on-provisioning request
(add-on creation, version update, IAM role configuration, configuration
values, conflict resolution, or a partial configuration), the agent
MUST respond with the READY_TO_DEPLOY checklist defined in the "Output
format" section using the literal all-caps labels `EKS_ADDON:`,
`VERDICT:`, `CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface
the checklist with prose, headings, or disclaimers — emit the block as
the first lines of the response. This contract is what assertion-based
evals and downstream provisioning pipelines rely on; deviating from the
literal labels breaks automation silently.

If any prerequisite is missing, the verdict is
`PREREQUISITES_MISSING` with a specific gap citation in the checklist
(marked `[✗]`), and `READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Add-on types (vpc-cni, coredns, kube-proxy, etc.) | Type selection |
| Step 2 — Version management (EKS-managed vs self-managed) | Version conflicts |
| Step 3 — Configuration values (override existing config) | Custom config |
| Step 4 — IAM roles for add-ons (IRSA) | IAM setup |
| Step 5 — EKS Pod Identity (latest credential method) | Pod Identity |
| Step 6 — EKS Auto Mode add-ons | Auto-managed lifecycle |
| Step 7 — EKS Hybrid Nodes add-ons | Hybrid node support |
| Step 8 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/addon-version-management.md | Version conflict detail |
| references/provisioning-cli-commands.md | Copy-pasteable CLI sequence |

## Mindset

**One-line takeaway:** EKS add-ons are managed Kubernetes components
(vpc-cni, coredns, kube-proxy, CSI drivers, etc.) that EKS maintains on
your cluster. The key decisions are: which add-ons to use, what version
matches your EKS version, whether to let EKS or your own tooling
manage them, and which IAM credential method to use (IRSA vs Pod
Identity).

Three misconceptions dominate EKS add-on misdesign at provisioning time:

- **"EKS-managed and self-managed add-ons are interchangeable."** They
  are not. If you install a self-managed version of an add-on (e.g., via
  Helm) and then enable the EKS-managed add-on, you get a CONFLICT. EKS
  add-ons use `ResolveConflicts` to determine who wins, but misconfigured
  conflicts can silently overwrite your customizations.

- **"The add-on version doesn't matter as long as it's recent."** Each
  EKS add-on version is validated against specific EKS/Kubernetes
  versions. An incompatible add-on version can break pod networking
  (vpc-cni), DNS resolution (coredns), or storage (EBS CSI). Always
  match the add-on version to the cluster's Kubernetes version.

- **"IRSA and EKS Pod Identity are the same thing."** They are not. IRSA
  (IAM Roles for Service Accounts) uses OIDC federation and trust
  policies. EKS Pod Identity (2024+) uses the EKS Pod Identity Agent and
  a simpler IAM mapping without OIDC. Newer add-ons support Pod Identity;
  older ones require IRSA.

## Configuration dependency graph (novel heuristic)

EKS add-on configurations are NOT independent. The add-on type, cluster
version, IAM credential method, and management mode interact in ways
that silently break cluster functionality. Use this graph both to
sequence provisioning and to debug "why is my add-on in DEGRADED
status?" later.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Add-on type | cluster must exist + match supported add-on list | some add-ons require specific node OS (AL2 vs AL2023 vs Bottlerocket) | cluster networking, DNS, storage |
| Add-on version | must match cluster's Kubernetes version | incompatible version → `CREATE_FAILED` or silent pod crashes | stable cluster operation |
| Management mode | `--resolve-conflicts` flag on create/update | `OVERWRITE` destroys self-managed config; `NONE` leaves conflict unresolved | EKS-managed vs self-managed coexistence |
| IRSA role | OIDC provider exists on cluster + trust policy with service account | wrong trust policy → pods get `AccessDenied` on AWS API calls | add-on AWS permissions (EBS CSI, etc.) |
| Pod Identity | EKS Pod Identity Agent add-on installed + IAM role + association | agent not running → pods get no credentials | newer credential path (no OIDC) |
| Configuration values | valid JSON matching add-on's schema | invalid JSON → `InvalidParameterException`; wrong keys silently ignored | add-on behavior tuning |
| Health check | add-on pods running + healthy | `DEGRADED` status means some pods are unhealthy | operational readiness |

**The version and conflict rows are the ones a baseline model misses.**
An add-on version that doesn't match the cluster's Kubernetes version
can silently break networking. And the `ResolveConflicts` setting
determines whether your self-managed customizations survive — `OVERWRITE`
silently destroys them.

**Cross-dependency gotchas:**
- The add-on version MUST be compatible with the cluster's Kubernetes
  version. Use `describe-addon-versions` to list valid versions.
- If a self-managed version of the add-on already exists (e.g.,
  `kube-system/aws-node` for vpc-cni), enabling the EKS add-on creates a
  conflict. Use `--resolve-conflicts OVERWRITE|RETAIN|NONE`.
- IRSA and Pod Identity are mutually exclusive for a given add-on
  service account. An add-on can use one or the other, not both.
- EKS Auto Mode manages some add-ons automatically (vpc-cni, kube-proxy,
  coredns). Do NOT manually manage these on Auto Mode clusters.
- EKS Hybrid Nodes may require specific add-on configurations for
  on-premises node networking.

## Expert heuristic: EKS-managed vs self-managed conflict lifecycle

The most common EKS add-on failure is a conflict between the EKS-managed
add-on and a pre-existing self-managed installation. A baseline model
may say "just create the add-on"; the conflict resolution strategy
determines whether your customizations survive.

```text
Scenario: cluster already has self-managed vpc-cni (aws-node DaemonSet)

create-addon --addon-name vpc-cni
  --resolve-conflicts OVERWRITE  → EKS replaces self-managed config (YOUR CUSTOMIZATIONS LOST)
  --resolve-conflicts RETAIN     → EKS keeps self-managed config (your customizations survive, but EKS may not fully manage)
  --resolve-conflicts NONE       → CONFLICT reported, add-on status = DEGRADED

update-addon --addon-name vpc-cni
  --resolve-conflicts OVERWRITE  → EKS overwrites on every update (not recommended for customized add-ons)
  --resolve-conflicts PRESERVE   → preserves existing fields, applies new defaults for unset fields
```

**Key implication:** if you have customized a self-managed add-on (e.g.,
custom env vars on `aws-node`), use `RETAIN` on first create and
`PRESERVE` on updates. `OVERWRITE` silently destroys your customizations.
The safe pattern is: export current config, create the EKS add-on with
`RETAIN`, then migrate customizations to `--configuration-values`.

**Operational pattern for migration from self-managed to EKS-managed:**
1. Export the current self-managed add-on config (e.g., `kubectl get
   ds aws-node -n kube-system -o yaml`).
2. Create the EKS add-on with `--resolve-conflicts OVERWRITE` to take
   control.
3. Re-apply customizations via `--configuration-values` using the EKS
   add-on API (not kubectl).
4. Verify the add-on status is `ACTIVE`.

## Expert heuristic: add-on version compatibility matrix

Each EKS add-on version is validated against specific EKS platform
versions and Kubernetes minor versions. A baseline model may pick the
latest version; this can break cluster networking if it's incompatible.

```text
describe-addon-versions --addon-name vpc-cni --kubernetes-version 1.30
  → Returns only versions validated for K8s 1.30
  → Includes "DEFAULT" flag for the recommended version
  → Includes compatibility info (addonVersion, platformVersions)

Rule: ALWAYS use describe-addon-versions to validate before create-addon.
      NEVER assume the latest version is compatible.
```

**Key implication:** the EKS API enforces version compatibility at
creation time, but a version that passes the API check may still have
runtime issues if the cluster uses an unusual configuration (custom
CNI, Fargate-only, etc.). Test add-on updates in a staging cluster first.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites.
If any are missing, the verdict is **PREREQUISITES_MISSING** with a
specific gap citation.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| EKS cluster exists and is ACTIVE | Add-ons attach to a cluster | `aws eks describe-cluster --name <name>` |
| Cluster Kubernetes version known | Add-on version must match | `aws eks describe-cluster --name <name> --query 'cluster.version'` |
| Add-on supported on cluster | Not all add-ons work on all clusters | `aws eks describe-addon-versions --addon-name <name>` |
| IAM permissions for add-on | Some add-ons need AWS API access | Check IRSA or Pod Identity setup |
| OIDC provider (for IRSA) | IRSA requires cluster OIDC | `aws eks describe-cluster --name <name> --query 'cluster.identity.oidc.issuer'` |
| Pod Identity Agent (for Pod Identity) | Pod Identity requires the agent add-on | `aws eks list-addons --name <name>` (look for `eks-pod-identity-agent`) |
| Self-managed add-on status | Existing self-managed add-ons conflict | `kubectl get ds -n kube-system` |
| Node group health | Add-ons schedule pods on nodes | `aws eks describe-nodegroup --cluster-name <name>` |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Add-on types (vpc-cni, coredns, kube-proxy, etc.)

EKS add-ons are categorized by function. Each type has specific
prerequisites and configuration patterns.

**Core networking add-ons (required for cluster operation):**

| Add-on | Purpose | Required | Default |
|---|---|---|---|
| `vpc-cni` | Pod networking (IP allocation via VPC) | Yes | Pre-installed on new clusters |
| `coredns` | Cluster DNS resolution | Yes | Pre-installed on new clusters |
| `kube-proxy` | Service routing and load balancing | Yes | Pre-installed on new clusters |

**Storage add-ons:**

| Add-on | Purpose | Required When |
|---|---|---|
| `aws-ebs-csi-driver` | EBS volume provisioning for pods | Using PersistentVolumes with EBS |

**Observability and security add-ons:**

| Add-on | Purpose |
|---|---|
| `metrics-server` | Resource metrics for HPA/VPA |
| `adot` | AWS Distro for OpenTelemetry collector |
| `guardduty-agent` | Amazon GuardDuty runtime threat detection |

**Infrastructure add-ons:**

| Add-on | Purpose |
|---|---|
| `eks-pod-identity-agent` | EKS Pod Identity credential agent |

**List available add-ons for a cluster:**

```bash
aws eks describe-addon-versions \
  --kubernetes-version 1.30 \
  --query 'addons[*].addonName' --output table
```

**Check which add-ons are already installed:**

```bash
aws eks list-addons --name my-cluster --output table
```

**Common mistake:** installing the `metrics-server` EKS add-on when
Metrics Server is already deployed via Helm. This creates a conflict
where two Metrics Server instances compete for the same API endpoints.

## Step 2 — Version management (EKS-managed vs self-managed)

The version management model determines who controls the add-on's
lifecycle and configuration.

**EKS-managed add-ons:** Created/managed via the EKS API
(`create-addon`, `update-addon`). EKS handles updates, patches, and
reconciliation. Config via `--configuration-values` (JSON). Version
pinned to a specific add-on version. Conflicts resolved via
`--resolve-conflicts`.

**Self-managed add-ons:** Installed via Helm, kubectl, or other
tooling. Operator handles all updates. Config via Helm values or
kubectl patches. Can coexist with EKS-managed add-ons IF conflicts
are resolved.

**Check add-on version compatibility:**

```bash
aws eks describe-addon-versions \
  --addon-name vpc-cni \
  --kubernetes-version 1.30 \
  --query 'addons[0].addonVersions[*].{Version:addonVersion,Default:compatibilities[0].defaultVersion}' \
  --output table
```

**Create an EKS-managed add-on with conflict resolution:**

```bash
aws eks create-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni \
  --addon-version v1.18.1-eksbuild.3 \
  --resolve-conflicts OVERWRITE \
  --service-account-role-arn arn:aws:iam::123456789012:role/AmazonEKSVPCCNIRole
```

**Conflict resolution strategies:**

| Strategy | Behavior | When to use |
|---|---|---|
| `OVERWRITE` | EKS replaces self-managed config entirely | Migrating from self-managed to EKS-managed |
| `RETAIN` | EKS keeps existing self-managed config | Coexistence with custom configurations |
| `NONE` | Report conflict without resolving | Diagnostic; leaves add-on in DEGRADED |
| `PRESERVE` (update only) | Keep existing fields, apply new defaults | Safe updates with customizations |

**Common mistake:** using `OVERWRITE` on an add-on with custom env vars
(e.g., custom `AWS_VPC_K8S_CNI_*` settings on vpc-cni). The overwrite
silently removes all customizations. Always export config first.

## Step 3 — Configuration values (override existing config)

EKS add-ons support JSON-based configuration overrides via
`--configuration-values`. These replace or supplement the add-on's
default configuration.

**Set configuration values on creation:**

```bash
aws eks create-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni \
  --addon-version v1.18.1-eksbuild.3 \
  --configuration-values '{"env":{"AWS_VPC_K8S_CNI_LOGLEVEL":"DEBUG","ENABLE_PREFIX_DELEGATION":"true"}}' \
  --resolve-conflicts OVERWRITE
```

**Update configuration values:**

```bash
aws eks update-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni \
  --configuration-values '{"env":{"ENABLE_PREFIX_DELEGATION":"true","WARM_PREFIX_TARGET":"1"}}' \
  --resolve-conflicts PRESERVE
```

**Configuration values by add-on type:**

| Add-on | Common configuration values |
|---|---|
| `vpc-cni` | `env.AWS_VPC_K8S_CNI_LOGLEVEL`, `env.ENABLE_PREFIX_DELEGATION`, `env.WARM_PREFIX_TARGET`, `env.ENABLE_IPv6` |
| `coredns` | `replicaCount`, `computeType`, `corefile` (custom DNS zones) |
| `kube-proxy` | `metricsBindAddress`, `mode` (iptables/ipvs) |
| `aws-ebs-csi-driver` | `controller.replicaCount`, `storageClasses`, `volumeSnapshotClass` |
| `metrics-server` | `metrics.args` (resource limits, scraping intervals) |

**Verify current configuration values:**

```bash
aws eks describe-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni \
  --query 'addon.configurationValues'
```

**Important:** `--configuration-values` replaces the entire
configuration block, not individual fields. To modify one value, you
must include all existing values. Query the current config first, modify,
then update.

**Common mistake:** setting `--configuration-values '{}'` (empty JSON)
which resets ALL configuration to defaults, losing custom env vars.
Always merge new values with existing configuration.

## Step 4 — IAM roles for add-ons (IRSA)

Some add-ons (vpc-cni, EBS CSI driver, adot) need AWS IAM permissions.
IRSA (IAM Roles for Service Accounts) is the traditional method.

**IRSA prerequisites:**
1. Cluster OIDC provider exists.
2. IAM role with a trust policy for the OIDC provider and the add-on's
   service account.

**Create an IAM role for vpc-cni (IRSA):**

```bash
CLUSTER_NAME=my-cluster
ACCOUNT_ID=123456789012
OIDC_URL=$(aws eks describe-cluster --name $CLUSTER_NAME \
  --query 'cluster.identity.oidc.issuer' --output text | sed 's|https://||')

# Create trust policy
cat > trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::${ACCOUNT_ID}:oidc-provider/${OIDC_URL}"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "${OIDC_URL}:aud": "sts.amazonaws.com",
        "${OIDC_URL}:sub": "system:serviceaccount:kube-system:aws-node"
      }
    }
  }]
}
EOF

aws iam create-role \
  --role-name AmazonEKSVPCCNIRole \
  --assume-role-policy-document file://trust-policy.json

# Attach the managed policy
aws iam attach-role-policy \
  --role-name AmazonEKSVPCCNIRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy
```

**Create add-on with IRSA role:**

```bash
aws eks create-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni \
  --service-account-role-arn arn:aws:iam::${ACCOUNT_ID}:role/AmazonEKSVPCCNIRole \
  --resolve-conflicts OVERWRITE
```

**IRSA vs Pod Identity comparison:**

| Feature | IRSA | EKS Pod Identity |
|---|---|---|
| Credential delivery | OIDC federation + projected token | Pod Identity Agent + ephemeral credentials |
| Setup complexity | OIDC provider + trust policy per SA | Agent add-on + IAM association |
| OIDC provider required | Yes | No |
| Multi-account support | Complex trust policies | Simpler cross-account |
| Migration status | Mature, widely supported | Newer (2024+), growing support |

**Common mistake:** using the wrong service account name in the trust
policy. vpc-cni uses `aws-node` in `kube-system`. EBS CSI uses
`ebs-csi-controller-sa`. A wrong SA name means the add-on's pods get
`AccessDenied` on every AWS API call.

## Step 5 — EKS Pod Identity (latest credential method)

EKS Pod Identity is the newest (2024+) method for granting AWS
permissions to Kubernetes pods. It uses an agent-based approach that
simplifies IAM mapping compared to IRSA.

**Prerequisites for EKS Pod Identity:**
1. The `eks-pod-identity-agent` add-on must be installed.
2. An IAM role with a Pod Identity trust policy.
3. A Pod Identity association linking the role to a service account.

**Install the Pod Identity Agent:**

```bash
aws eks create-addon \
  --cluster-name my-cluster \
  --addon-name eks-pod-identity-agent \
  --resolve-conflicts OVERWRITE
```

**Create a Pod Identity IAM role:**

```bash
cat > pod-identity-trust.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "pods.eks.amazonaws.com" },
    "Action": ["sts:AssumeRole", "sts:TagSession"]
  }]
}
EOF

aws iam create-role \
  --role-name MyAddonRole \
  --assume-role-policy-document file://pod-identity-trust.json
```

**Create a Pod Identity association:**

```bash
aws eks create-pod-identity-association \
  --cluster-name my-cluster \
  --namespace kube-system \
  --service-account aws-node \
  --role-arn arn:aws:iam::123456789012:role/MyAddonRole
```

**Key advantages of Pod Identity over IRSA:**
- No OIDC provider configuration needed.
- Simpler trust policy (`pods.eks.amazonaws.com` instead of per-cluster
  OIDC URL).
- Easier cross-account role assumption.
- Tag-based access control via session tags.
- The agent handles credential rotation automatically.

**Migration from IRSA to Pod Identity:**
1. Install `eks-pod-identity-agent`.
2. Create a new IAM role with Pod Identity trust policy.
3. Create Pod Identity association for the service account.
4. Remove the old IRSA role annotation from the service account.
5. Verify pods pick up the new credentials (pod restart required).

**Common mistake:** installing the Pod Identity Agent but forgetting
to create the Pod Identity association. The agent runs but pods still
have no credentials because no role is mapped to their service account.

## Step 6 — EKS Auto Mode add-ons

EKS Auto Mode (2024+) automatically manages cluster infrastructure,
including core add-ons. When Auto Mode is enabled, `vpc-cni`,
`kube-proxy`, and `coredns` are managed by EKS automatically.

**Rules for Auto Mode clusters:**
- Do NOT manually create or update Auto Mode-managed add-ons — manual
  changes are silently overwritten by Auto Mode reconciliation.
- Additional add-ons (EBS CSI, metrics-server, adot, guardduty-agent)
  are still managed manually.
- The `--resolve-conflicts` flag is irrelevant for Auto Mode-managed
  add-ons since EKS always wins.

**Check if a cluster uses Auto Mode:**

```bash
aws eks describe-cluster --name my-cluster --query 'cluster.computeConfig'
```

**Common mistake:** manually updating vpc-cni on an Auto Mode cluster.
Auto Mode reconciles it back to its managed state, silently reverting
your changes. Use cluster-level settings for custom networking config.

## Step 7 — EKS Hybrid Nodes add-ons

EKS Hybrid Nodes (2024+) allows on-premises or edge nodes to join an
EKS cluster. Add-ons on Hybrid Nodes require specific configurations.

**Hybrid Nodes add-on considerations:**
- `vpc-cni` may require custom networking for non-VPC topologies
  (`AWS_VPC_K8S_CNI_EXTERNALSNAT`, `CUSTOM_NETWORK_CFG`).
- `coredns` may need custom upstream DNS for on-prem environments.
- Storage add-ons (EBS CSI) are not applicable for on-prem nodes.
- Not all EKS add-ons support Hybrid Nodes — check
  `describe-addon-versions` for compatibility annotations.

```bash
# vpc-cni with custom networking for hybrid nodes
aws eks update-addon \
  --cluster-name my-hybrid-cluster \
  --addon-name vpc-cni \
  --configuration-values '{"env":{"AWS_VPC_K8S_CNI_EXTERNALSNAT":"true","CUSTOM_NETWORK_CFG":"true"}}' \
  --resolve-conflicts PRESERVE
```

## Step 8 — Recent features

- **EKS Pod Identity (2024):** New credential delivery method using
  the `eks-pod-identity-agent` add-on. Simpler than IRSA — no OIDC
  provider required. Uses `pods.eks.amazonaws.com` trust principal.
- **EKS Auto Mode (2024-2025):** Automatically manages vpc-cni,
  kube-proxy, coredns, and node lifecycle. Manual add-on management is
  not needed for these on Auto Mode clusters.
- **EKS Hybrid Nodes (2024-2025):** On-premises nodes join EKS clusters.
  Add-ons require hybrid-specific configurations for non-VPC networking.
- **Add-on configuration values schema validation (2024-2025):** EKS
  now validates `--configuration-values` JSON against the add-on's
  schema. Invalid keys are reported at creation/update time.
- **GuardDuty Agent EKS add-on (2024-2025):** Runtime threat detection
  as a managed EKS add-on. Requires Pod Identity or IRSA for the
  GuardDuty security account.
- **ADOT Operator add-on (2024-2025):** AWS Distro for OpenTelemetry
  as a managed EKS add-on with Operator pattern for automated
  collector deployment.

## NEVER do these things

1. **NEVER use `--resolve-conflicts OVERWRITE` on a customized
   self-managed add-on without exporting config first.** `OVERWRITE`
   silently destroys all customizations. Export with `kubectl get`,
   then migrate customizations to `--configuration-values`.

2. **NEVER install an add-on version without checking compatibility.**
   Use `describe-addon-versions --kubernetes-version <version>` to
   verify the add-on version is validated for your cluster's Kubernetes
   version. Incompatible versions cause silent pod crashes.

3. **NEVER use the wrong service account name in an IRSA trust policy.**
   Each add-on has a specific service account (e.g., `aws-node` for
   vpc-cni, `ebs-csi-controller-sa` for EBS CSI). A wrong SA name means
   the add-on gets `AccessDenied` on every AWS API call.

4. **NEVER manually manage Auto Mode-managed add-ons.** On Auto Mode
   clusters, vpc-cni, kube-proxy, and coredns are managed by EKS.
   Manual changes are silently reverted by Auto Mode reconciliation.

5. **NEVER set `--configuration-values '{}'` to reset config.** Empty
   JSON resets ALL configuration to defaults. Always merge new values
   with existing configuration by querying the current config first.

6. **NEVER use IRSA and Pod Identity simultaneously for the same
   service account.** They are mutually exclusive. An add-on can use
   one credential method or the other, not both. Migrate cleanly.

7. **NEVER skip installing the Pod Identity Agent.** Pod Identity
   associations have no effect if the agent add-on is not running.
8. **NEVER assume all add-ons support Pod Identity.** Newer add-ons
   (2024+) support it; older ones require IRSA.

9. **NEVER install the EBS CSI driver without an IRSA or Pod Identity
   role.** Without IAM permissions, PVC provisioning silently fails
   with `failed to provision volume with StorageClass`.

## Output format

```text
EKS_ADDON: <addon-name> (version <addon-version>) on cluster <cluster-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Cluster: <name> — ACTIVE, Kubernetes <version>
  [✓|✗] Add-on type: <vpc-cni|coredns|kube-proxy|aws-ebs-csi-driver|metrics-server|adot|guardduty-agent|eks-pod-identity-agent>
  [✓|✗] Add-on version: <version> (compatible with K8s <version>)
  [✓|✗] Management mode: EKS-managed | Self-managed migration | Auto Mode
  [✓|✗] Conflict resolution: OVERWRITE | RETAIN | PRESERVE | NONE
  [✓|✗] Configuration values: <JSON or "default">
  [✓|✗] IAM credential method: IRSA (role <role-name>) | Pod Identity (association <id>) | N/A
  [✓|✗] OIDC provider: <url> (for IRSA) | N/A (for Pod Identity)
  [✓|✗] Pod Identity Agent: installed (for Pod Identity) | N/A
  [✓|✗] Self-managed add-on: present (conflict) | absent (clean install)
  [✓|✗] Auto Mode cluster: yes (add-on auto-managed) | no (manual management)
  [✓|✗] Hybrid Nodes: yes (hybrid-specific config) | no
  [✓|✗] Health: ACTIVE | DEGRADED | CREATE_IN_PROGRESS
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws eks describe-addon --cluster-name <name> --addon-name <addon>
  aws eks list-addons --name <name>
  kubectl get pods -n kube-system -l app.kubernetes.io/name=<addon>
  kubectl get ds -n kube-system
```

### Worked example — vpc-cni with IRSA on EKS 1.30

```text
EKS_ADDON: vpc-cni (version v1.18.1-eksbuild.3) on cluster production-cluster
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Cluster: production-cluster — ACTIVE, Kubernetes 1.30
  [✓] Add-on type: vpc-cni
  [✓] Add-on version: v1.18.1-eksbuild.3 (compatible with K8s 1.30)
  [✓] Management mode: EKS-managed (migrated from self-managed)
  [✓] Conflict resolution: OVERWRITE (migration to EKS-managed)
  [✓] Configuration values: {"env":{"ENABLE_PREFIX_DELEGATION":"true"}}
  [✓] IAM credential method: IRSA (role AmazonEKSVPCCNIRole)
  [✓] OIDC provider: oidc.eks.us-east-1.amazonaws.com/id/EXAMPLED539D4633E53DE1B716D3041E
  [✓] Pod Identity Agent: N/A (using IRSA)
  [✓] Self-managed add-on: present (resolving with OVERWRITE)
  [✓] Auto Mode cluster: no (manual management)
  [✓] Hybrid Nodes: no
  [✓] Health: ACTIVE
  [✓] Tags: Environment=production, ManagedBy=eks-add-on-deployer
VERIFICATION_COMMANDS:
  aws eks describe-addon --cluster-name production-cluster --addon-name vpc-cni
  aws eks list-addons --name production-cluster
  kubectl get pods -n kube-system -l k8s-app=aws-node
  kubectl get ds -n kube-system
```

## Error handling

- **`InvalidParameterException` on create-addon:** Add-on version
  incompatible with cluster K8s version. Run `describe-addon-versions`
  to find a valid version. Also check the add-on name spelling.
- **Add-on status `DEGRADED` after creation:** Conflict with self-
  managed add-on. Check `describe-addon --query 'addon.healthIssues'`.
  Resolve by updating with `--resolve-conflicts OVERWRITE` or fixing
  the conflicting resource.
- **Pods get `AccessDenied` / `Unauthorized` on AWS API:** IRSA trust
  policy has wrong service account name or OIDC URL. Verify the trust
  policy matches the add-on's service account. For Pod Identity, verify
  the association exists and the agent is running.
- **`ConfigurationConflict` on update:** `--configuration-values`
  conflicts with existing self-managed config. Use `--resolve-conflicts
  PRESERVE` to merge, or `OVERWRITE` to replace.
- **Add-on reverts to default after manual config:** Cluster uses Auto
  Mode which reconciles managed add-ons. Do not manually configure Auto
  Mode-managed add-ons. Use cluster-level settings instead.
- **PVC provisioning fails after EBS CSI add-on:** Missing IAM role.
  Create an IRSA role for `ebs-csi-controller-sa` with the
  `AmazonEBSCSIDriverPolicy` (or appropriate custom policy) and
  re-create the add-on with `--service-account-role-arn`.

## Domain

AWS CloudOps / Amazon EKS Kubernetes Add-On Management.

## AWS documentation

- **EKS add-ons** — https://docs.aws.amazon.com/eks/latest/userguide/eks-add-ons.html
- **EKS Pod Identity** — https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html
- **EKS Auto Mode** — https://docs.aws.amazon.com/eks/latest/userguide/auto-mode.html
- **EKS Hybrid Nodes** — https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes.html
- **IRSA** — https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html
- **EBS CSI driver** — https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html
- **vpc-cni** — https://docs.aws.amazon.com/eks/latest/userguide/managing-vpc-cni.html
- **Terraform aws_eks_add_on** — https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_addon
