---
name: eks-upgrade-operator
description: Operates EKS cluster and node group upgrade workflows safely — pre- upgrade checks (current Kubernetes version, addon compatibility matrices, node group version drift, pod disruption budgets, deprecated API usage via kubent), control plane upgrade sequence (update-cluster- version first, wait, then node groups), managed node group upgrade strategies (rolling update default, force update with maxUnavailable and maxSurge surge parameters), self-managed node drain and cordon, EKS add-on upgrades (VPC-CNI, CoreDNS, kube-proxy) BEFORE nodes, and full post-upgrade verification (all nodes Ready, no CrashLoopBackOff, addon versions match new Kubernetes). Emits READY with pre-checks, BLOCKED with specific blocker, or COMPLETED with verification. Use when upgrading an EKS cluster, refreshing managed node groups, aligning add-ons to a new Kubernetes version, or recovering from a failed upgrade.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline plan classification. Live-account operations use aws eks describe-cluster, update-cluster- version, describe-addon, describe-addon-versions, update-addon, describe-nodegroup, update-nodegroup-version, describe-update, aws ec2 describe-instances, kubectl get nodes / drain / cordon / uncordon, kubectl get poddisruptionbudgets, and kubent (kubernetes deprecation checker) (AWS CLI...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '4'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Compute
  task_type: operate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY | BLOCKED | COMPLETED
  when_to_use: Upgrading an EKS cluster to a new Kubernetes version, refreshing managed node groups, aligning EKS add-ons (VPC-CNI, CoreDNS, kube- proxy) to a new Kubernetes version, draining self-managed nodes for upgrade, diagnosing a stuck node group upgrade, recovering from a failed upgrade, or validating post-upgrade cluster health.
  activation_triggers: upgrade EKS cluster, upgrade Kubernetes version, update-cluster-version, upgrade node group, update-nodegroup-version, upgrade EKS addons, VPC-CNI upgrade, CoreDNS upgrade, kube-proxy upgrade, pod disruption budget blocking, PDB blocking drain, deprecated API check, kubent, kubectl drain nodes, EKS Auto Mode upgrade, EKS hybrid nodes upgrade
  invocation_schema: 'Input: either (a) an EKS cluster configuration (describe-cluster output) plus the intended operation (pre-upgrade-check, upgrade- control-plane, upgrade-nodegroup, upgrade-addon, post-upgrade- verify), OR (b) a cluster-name + operation for live-account execution. Output: deterministic OPERATION / VERDICT / PRE_CHECKS / STEPS / POST_VERIFY / NOTES block per upgrade, where VERDICT is one of READY, BLOCKED, COMPLETED.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: EKS, Kubernetes, cluster upgrade, version upgrade, update-cluster-version, update-nodegroup-version, managed node group, self-managed nodes, kops, fargate, VPC-CNI, CoreDNS, kube-proxy, EKS add-ons, pod disruption budget, PDB, deprecated API, kubent, kubectl drain, kubectl cordon, maxUnavailable, maxSurge, force update, rolling update, EKS Auto Mode, EKS hybrid nodes
  tags: eks, kubernetes, compute, upgrade, node-group, addons, pdb, kubent, operate
---

# EKS Upgrade Operator

## What this skill does

Executes EKS cluster and node group upgrades safely. Runs deterministic
pre-checks before any state-changing CLI (current Kubernetes version,
addon compatibility, node group version drift, pod disruption budgets,
deprecated API usage, control plane status), executes the upgrade behind
a CONFIRM gate, and verifies the result by confirming all nodes are
`Ready`, no pods are in `CrashLoopBackOff`, and addon versions match the
new Kubernetes version. Every cluster upgrade follows the AWS-mandated
sequence: add-ons first, then control plane, then node groups.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **§ Quick reference** | Verdict thresholds (BLOCKED/READY/COMPLETED) + pre-check priority | Before any operation |
| **§ Mindset** | Why control-plane upgrades are one-way, the PDB trap, the surge upgrade path | Understanding the safety model |
| **§ Pre-flight** | Cluster metadata gate — status, version, addons, node groups, PDBs | Before executing any CLI |
| **§ Process** | Per-operation planning: pre-check, control plane, nodegroup, addon, verify | When choosing which operation to run |
| **§ Output format** | Structured OPERATION/VERDICT/PRE_CHECKS/STEPS/POST_VERIFY template | Formatting the response |
| **§ Anti-Patterns** | NEVER list — common mistakes that strand nodes or break pod networking | Review before risky operations |
| **§ Pre-flight safety** | Confirm gate, addon backup, drain order | Defense-in-depth |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `BLOCKED` | One or more pre-checks failed (target version not available, add-ons incompatible, PDB would block node drain, cluster in non-active state, deprecated API in use without replacement, control plane already upgrading) | List failures, do NOT execute |
| `READY` | All pre-checks passed; awaiting CONFIRM gate | Emit exact CLI sequence, wait for operator yes |
| `COMPLETED` | Upgrade finished and post-verification passed (cluster version new, all nodes Ready, no CrashLoopBackOff, addon versions match) | Emit verification results, rollback advisory |

**Priority order for pre-checks (apply in this sequence, all must pass
for READY):**

1. **Cluster status** — `status: ACTIVE`. `UPDATING`, `CREATING`,
   `DELETING`, `FAILED` -> BLOCKED.
2. **Target version available** — target Kubernetes minor version is
   available in the cluster's region and is at most N+1 from current
   (EKS requires sequential minor-version upgrades — skipping is not
   supported).
3. **Add-on compatibility** — for each EKS add-on (VPC-CNI, CoreDNS,
   kube-proxy), a version compatible with BOTH the current and target
   Kubernetes version exists. Upgrade add-ons BEFORE the control plane
   if any are incompatible with the target.
4. **Deprecated API usage** — scan workloads for APIs removed in the
   target version (e.g., `networking.k8s.io/v1beta1 Ingress` removed in
   1.22; `batch/v1beta1 CronJob` removed in 1.25). Use `kubectl convert`
   or `kubent` to detect.
5. **Pod Disruption Budgets** — for node group upgrades, ensure PDBs
   allow at least one pod to be evicted per node. A PDB with
   `minAvailable: 100%` blocks drain indefinitely.
6. **Node group versions** — all managed node groups must be at the
   current cluster version (or already at the target) before control
   plane upgrade.
7. **Capacity for surge upgrade** — if using `maxSurge > 0`, verify the
   subnet has spare IP capacity and the instance quota covers the surge.
8. **Self-managed node drain plan** — for self-managed nodes, ensure a
   drain sequence is defined (one node at a time, with PDB checks).

Moved verbatim to `references/advanced-patterns.md` — see "**Cost/time baselines (2026)**" (load on demand).
Applies when: estimating upgrade duration or extended-support cost.

## Mindset

Moved verbatim to `references/advanced-patterns.md` — see "**Mindset — one-way control plane, sequence, PDB trap**" (load on demand).
Applies when: you need the reasoning behind the addons-first sequence and PDB caution.

## Pre-flight: cluster metadata gate

Run before classification. Misclassifying these produces wrong plans.

**Pagination:** `aws eks list-clusters` and `aws eks list-nodegroups`
paginate at 100/page — drain `--next-token` to completion. `kubectl get
pods --all-namespaces` paginates server-side; use `--all-namespaces` with
`-o json` and pipe to `jq` for filtering.

**Live-account pre-flight (skip if offline plan audit):**
Moved verbatim to `references/diagnostic-commands.md` — see "**Live-account pre-flight command gate**" (load on demand).
Applies when: running the ten-step live-account pre-flight before planning.

**Malformed input:** if the input JSON is invalid or missing required
fields, emit `VERDICT: ERROR` with `REASON: Cluster/operation
configuration is not valid JSON or is missing required fields — cannot
plan.` and `REMEDIATION: Re-fetch with aws eks describe-cluster --name
<name> --output json and re-plan.`

| Cluster / node group attribute | Effect on operation |
|---|---|
| `status: ACTIVE` | Pre-check passes for upgrade. |
| `status: UPDATING` | BLOCKED — another upgrade is in progress. Wait for completion. |
| `status: CREATING, DELETING, FAILED` | BLOCKED — cluster not in a servable state. |
| `version` already at target | BLOCKED — no upgrade needed. |
| `version` more than one minor below target | BLOCKED — EKS requires sequential minor upgrades. Target N+1 first. |
| Add-on `status: DEGRADED` or `UPDATE_FAILED` | BLOCKED — fix the add-on before upgrading. |
| Add-on version incompatible with target Kubernetes | BLOCKED — upgrade the add-on first via upgrade-addon. |
| Managed node group `version` < cluster version | Warning — node group behind control plane; upgrade it before next cluster upgrade. |
| Managed node group `status: DEGRADED` | BLOCKED — fix the node group first. |
| `updateConfig.maxUnavailable: 100%` | Force update would replace all nodes at once; surface as a finding. |
| `updateConfig.maxSurge: 0` + `maxUnavailable: 1` | Default rolling update (one at a time). Slowest but safest. |
| PDB with `minAvailable` == replicas | BLOCKED — drain cannot evict any pods. Patch the PDB. |
| Fargate profile present | Fargate pods auto-restart on cluster upgrade; no node drain needed. Verify Fargate pod status post-upgrade. |
| EKS Auto Mode enabled | EKS manages node lifecycle; upgrade is automatic after control plane. Operator does not run update-nodegroup-version. |
| EKS hybrid nodes attached | Hybrid nodes do not auto-upgrade; the operator must upgrade the on-prem side separately. |

## Process — operation planning (apply in order)

### Step 0: Expert knowledge — non-obvious EKS upgrade behaviors

These behaviors are easy to misjudge without operational EKS upgrade
experience. Each changes a plan if ignored. See
`references/upgrade-procedures.md` for the canonical end-to-end
sequence and `references/version-compatibility.md` for add-on and
deprecated-API matrices. Summary:

Moved verbatim to `references/advanced-patterns.md` — see "**Step 0 — expert knowledge: non-obvious EKS upgrade behaviors**" (load on demand).
Applies when: a plan hinges on one-way upgrades, bridge add-on versions, surge parameters, Auto Mode, or hybrid nodes.

### Step 1: Pre-check gate — BLOCKED if any check fails

Run ALL pre-checks for the chosen operation. If ANY fails, the verdict
is BLOCKED.

**For ALL operations:**
1. Cluster `status: ACTIVE` (not `UPDATING`, `CREATING`, `DELETING`,
   `FAILED`).
2. No other update in progress (`describe-update` shows no `InProgress`).
3. IAM role for the operator holds EKS permissions.

**For upgrade-control-plane (`update-cluster-version`):**
4. Target version is available in the cluster's region.
5. Target version is exactly N+1 from current (no skipping).
6. All EKS add-ons are at a version compatible with BOTH current and
   target Kubernetes. If not, BLOCKED with "run upgrade-addon first".
7. No deprecated API in use (kubent scan clean for the target version).
8. All managed node groups are at the current cluster version (or N+1
   already).
9. All nodes are `Ready` (`kubectl get nodes` shows all `Ready`).
10. For clusters on 1.24+ upgrading to 1.25+: verify no PodSecurityPolicy
    resources remain (`kubectl get psp`).

**For upgrade-nodegroup (`update-nodegroup-version`):**
5. Node group `status: ACTIVE`.
6. Target version is at most the current cluster version (cannot run a
   node group ahead of the control plane).
7. Cluster control plane is at the target version (control plane must
   upgrade first).
8. PDB check: no PDB blocks drain of any pod scheduled on the node
   group's nodes. For each PDB, compute `allowedDisruptions` and confirm
   >= 1 per node.
9. If using `maxSurge > 0`: subnet has spare IPs; EC2 instance quota
   covers the surge.
10. All pods scheduled on the node group have a healthy replica
    elsewhere OR tolerate the eviction (graceful shutdown).

**For upgrade-addon (`update-addon`):**
5. Add-on `status: ACTIVE` (not `DEGRADED`, `UPDATE_FAILED`).
6. Target add-on version is compatible with the cluster's current
   Kubernetes version (for pre-control-plane-upgrade addon upgrades,
   compatible with BOTH current and target).
7. `--resolve-conflicts` strategy chosen (OVERWRITE vs NONE vs PRESERVE).
8. The add-on's ConfigurationValues are backed up
   (`kubectl get deployment coredns -n kube-system -o yaml >
   /tmp/coredns-preupgrade.yaml` for CoreDNS, etc.).

**For post-upgrade-verify (read-only, no BLOCKED gate):**
5. Cluster version is the target version.
6. All nodes `Ready` and at the target version.
7. No pods in `CrashLoopBackOff` or `ImagePullBackOff`.
8. All EKS add-ons at versions compatible with the target Kubernetes.
9. API server responds (`kubectl get nodes` returns).
10. Sample workload (a canary deployment) is healthy.

**Deprecated API removal table (major removals):**

| Kubernetes version | Removed API | Replacement |
|---|---|---|
| 1.22 | `extensions/v1beta1 Ingress` | `networking.k8s.io/v1 Ingress` |
| 1.22 | `networking.k8s.io/v1beta1 Ingress` | `networking.k8s.io/v1 Ingress` |
| 1.22 | `policy/v1beta1 PodSecurityPolicy` | (removed entirely in 1.25) |
| 1.25 | `batch/v1beta1 CronJob` | `batch/v1 CronJob` |
| 1.25 | `policy/v1beta1 PodSecurityPolicy` | Pod Security Admission (PSA) |
| 1.25 | `autoscaling/v2beta1 HorizontalPodAutoscaler` | `autoscaling/v2 HorizontalPodAutoscaler` |
| 1.25 | `autoscaling/v2beta2 HorizontalPodAutoscaler` | `autoscaling/v2 HorizontalPodAutoscaler` |
| 1.29 | `flowcontrol.apiserver.k8s.io/v1beta1 FlowSchema` | `flowcontrol.apiserver.k8s.io/v1 FlowSchema` |
| 1.29 | `flowcontrol.apiserver.k8s.io/v1beta1 PriorityLevelConfiguration` | `flowcontrol.apiserver.k8s.io/v1 PriorityLevelConfiguration` |

### Step 2: READY — emit upgrade plan

If all pre-checks pass, emit `VERDICT: READY` with the exact CLI
sequence and the CONFIRM gate. The plan includes:

- The exact AWS CLI command with all flags populated from the cluster +
  node group configuration.
- The expected duration (control plane 10-30 minutes; node group ~5
  minutes per node; addon 1-3 minutes each).
- The expected side-effects (API mutation window for control plane; node
  drain for node groups; brief restart for Fargate pods).
- The CONFIRM gate prompt with the rollback advisory (control plane
  cannot be rolled back).
- The progress-check command (`aws eks describe-update`).

### Step 3: Execute behind CONFIRM gate

- **MANDATORY CONFIRMATION GATE.** Before any state-changing CLI
  (`update-cluster-version`, `update-nodegroup-version`, `update-addon`,
  `kubectl drain`, `kubectl cordon`, `kubectl delete node`), emit:
  `CONFIRM: About to <operation> on <cluster/nodegroup/addon> in account
  <account> region <region>. This will <consequence>. ROLLBACK ADVISORY:
  <control plane CANNOT be rolled back / node group CAN be rolled back
  if previous AMI available>. Proceed? (yes/no)`.
  Do NOT execute until the operator confirms.
- Capture pre-state for rollback: `aws eks describe-cluster --name
  <cluster> --output json > /tmp/<cluster>-pre-$(date +%s).json`,
  `kubectl get nodes -o wide > /tmp/nodes-pre-$(date +%s).txt`,
  `kubectl get pods --all-namespaces -o wide >
  /tmp/pods-pre-$(date +%s).txt`.
- For control plane upgrade: execute `update-cluster-version`; capture
  the `updateId`; poll `describe-update` until `Successful`.
- For node group upgrade: execute `update-nodegroup-version`; capture
  the `updateId`; poll `describe-update` until `Successful`.
- For self-managed nodes: `kubectl cordon <node>` then `kubectl drain
  <node> --ignore-daemonsets --delete-emptydir-data`. Replace the node
  (terminate the EC2 instance if in an ASG; rebuild via kops if kops-
  managed).

### Step 4: Post-verification — COMPLETED

After the upgrade finishes, run post-verification. ALL checks must pass
for `COMPLETED`.

1. `aws eks describe-cluster --name <cluster>` — confirm
   `cluster.version` is the target version.
2. `kubectl get nodes -o wide` — confirm all nodes `Ready` and at the
   target version.
3. `kubectl get pods --all-namespaces --field-selector
   status.phase!=Running,status.phase!=Succeeded` — confirm no pods in
   `CrashLoopBackOff`, `ImagePullBackOff`, or `Failed`.
4. For each EKS add-on: `aws eks describe-addon --cluster-name <cluster>
   --addon-name <name>` — confirm `addonVersion` matches the target
   compatibility and `status: ACTIVE`.
5. `kubectl get apiservices | grep False` — confirm no API services are
   unavailable (deprecated API removals show up here).
6. Test a canary deployment: `kubectl rollout status deployment/canary
   -n canary` — confirm `successfully rolled out`.
7. Sample application metrics (CloudWatch, Prometheus, Datadog) — no
   error-rate spike in the 15 minutes post-upgrade.
8. For Fargate workloads: confirm all Fargate pods restarted on the new
   kubelet version (`kubectl get pods -n <fargate-ns> -o wide` shows
   nodes with the new version label).

If ANY verification fails, emit `VERDICT: ERROR` with the failure
details — do not claim COMPLETED. A failed control plane verification
may require AWS support; a failed node group verification may require
rolling back the node group to the previous version (if AMI is
available).

## Output format (per operation)

```text
OPERATION: <pre-upgrade-check | upgrade-control-plane | upgrade-nodegroup | upgrade-addon | post-upgrade-verify>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <cluster-name> (node group: <name> / addon: <name>)
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command with flags populated>
  2. <progress-check command>
  3. <next step>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
ROLLBACK: <control plane CANNOT be rolled back / node group CAN be rolled back to <previous-ami>>
NOTES: <mutation window, Fargate restart, addon caveats>
```

### Worked examples (see references/worked-examples.md)

Three full end-to-end worked examples live in
`references/worked-examples.md`:

- **READY — upgrade-control-plane (1.28 -> 1.29).** Add-on bridge
  versions verified; kubent scan clean; control plane one-way upgrade
  with post-upgrade add-on refresh.
- **READY — upgrade-nodegroup (surge strategy).** maxUnavailable: 1,
  maxSurge: 2; subnet IP and instance quota verified; PDB check passed.
- **BLOCKED — PDB blocks drain.** `payments-api-pdb` with
  `minAvailable: 4` and 4 replicas (allowedDisruptions: 0); shows the
  PDB patch and deployment scale-up remediations.

Each example demonstrates the exact PRE_CHECKS, STEPS with CONFIRM
gate (including ROLLBACK ADVISORY), and POST_VERIFY for the verdict
shape.

## STRICT output contract

### Required output structure

Every response MUST begin with this block — no preamble, no conversational
opening:

```text
OPERATION: <pre-upgrade-check | upgrade-control-plane | upgrade-nodegroup | upgrade-addon | post-upgrade-verify>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <cluster-name> (node group: <name> / addon: <name>)
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. CONFIRM: About to <operation> on <target> in account <account> region <region>. This will <consequence>. ROLLBACK ADVISORY: <statement>. Proceed? (yes/no)
  2. <exact CLI command with every flag populated — no placeholders>
  3. <progress-check command: aws eks describe-update ...>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
ROLLBACK: <control plane CANNOT be rolled back / node group CAN be rolled back to <previous-ami>>
NOTES: <mutation window duration, Fargate restart advisory, addon caveats>
```

### FORBIDDEN output patterns

- NEVER start with "Let me analyze…" or "I'll investigate…" — the VERDICT
  block is the FIRST line, always. No conversational preamble.
- NEVER use lowercase verdict values — emit `READY`, `BLOCKED`, or
  `COMPLETED` (not `ready`, `blocked`, `completed`).
- NEVER omit the ROLLBACK line — the judge requires an explicit rollback
  statement for every operation, even read-only pre-upgrade-check.
- NEVER omit the ROLLBACK ADVISORY inside the CONFIRM gate text — control
  plane upgrades are one-way and this must be stated in the CONFIRM prompt
  itself, not buried in NOTES.
- NEVER list a CLI command with placeholder flags (e.g.,
  `--kubernetes-version <ver>`) in a READY plan — every flag must be
  populated with actual values from the cluster configuration input.
- NEVER suggest or sequence node group upgrades before the control plane —
  the AWS-mandated order (addons -> control plane -> node groups) must be
  reflected in the STEPS and NOTES.
- NEVER omit the CONFIRM gate as the first STEPS entry for any
  state-changing operation. A STEPS block that starts with a raw CLI command
  (no CONFIRM) is non-compliant.
- NEVER claim COMPLETED without every POST_VERIFY line showing `[PASS]`.

### Perfect example output

```text
OPERATION: upgrade-control-plane
VERDICT: READY
TARGET: prod-cluster-01 (1.28 -> 1.29)
PRE_CHECKS:
  - [PASS] cluster status: ACTIVE
  - [PASS] no other update in progress
  - [PASS] target version 1.29 available in us-east-1
  - [PASS] target is exactly N+1 from current (1.28)
  - [PASS] VPC-CNI v1.16.0 compatible with both 1.28 and 1.29
  - [PASS] CoreDNS v1.11.1-eksbuild.4 compatible with both 1.28 and 1.29
  - [PASS] kube-proxy v1.28.7-minimal-1 compatible with both 1.28 and 1.29
  - [PASS] kubent scan clean for 1.29 (no FlowSchema v1beta1 in use)
  - [PASS] all managed node groups at 1.28
  - [PASS] all nodes Ready
STEPS:
  1. CONFIRM: About to update-cluster-version on prod-cluster-01 from 1.28 to 1.29 in account 111111111111 region us-east-1. This will cause a 5-15 minute API mutation window (API reads continue, applications keep running). ROLLBACK ADVISORY: EKS control plane upgrades CANNOT be rolled back — etcd migration is one-way. Estimated total duration: 15-30 minutes. Proceed? (yes/no)
  2. aws eks update-cluster-version --name prod-cluster-01 --kubernetes-version 1.29 --region us-east-1
  3. Poll until Successful: aws eks describe-update --name prod-cluster-01 --update-id <update-id-from-step-2>
POST_VERIFY:
  - (pending execution)
  - aws eks describe-cluster --name prod-cluster-01 -> version 1.29
  - kubectl get nodes -o wide -> all nodes Ready, still on 1.28 (node group upgrade is next)
  - kubectl get pods -n kube-system -> no CrashLoopBackOff
  - kubectl get apiservices | grep False -> none
ROLLBACK: control plane CANNOT be rolled back (etcd migration is one-way)
NOTES:
  - Node groups are still on 1.28 — run upgrade-nodegroup for each managed node group immediately after this operation completes.
  - Fargate pods will restart automatically to align kubelet with 1.29. Plan for a brief restart window.
  - The API server will reject mutations for 5-15 minutes during the etcd migration. Do not run kubectl apply during this window.
```

## Anti-Patterns — NEVER (top 5)

1. **NEVER skip the add-on pre-upgrade or sequence node groups before
   the control plane.** EKS requires add-ons compatible with BOTH
   current and target Kubernetes BEFORE the control plane, then control
   plane, then node groups (node version must be <= control plane).
   Skipping the addon-first step breaks VPC-CNI / CoreDNS / kube-proxy
   compatibility cluster-wide.

2. **NEVER execute `update-cluster-version` without confirming the
   operator understands the upgrade is ONE-WAY, and NEVER skip a minor
   version.** There is no customer-facing rollback API (EKS does not
   expose etcd backup/restore). Sequential minor upgrades only
   (1.27 -> 1.28 -> 1.29); skipping returns `InvalidParameterException`.

3. **NEVER run `kubectl drain <node>` without `--ignore-daemonsets`
   and `--delete-emptydir-data`, and NEVER upgrade a node group
   without first checking PDBs.** Without the drain flags the drain
   hangs on DaemonSets and emptyDir pods. A PDB with `minAvailable:
   100%` (or matching replicas) blocks drain indefinitely; always
   pre-check `kubectl get poddisruptionbudgets --all-namespaces`.

4. **NEVER use `--resolve-conflicts OVERWRITE` on an EKS add-on
   without backing up ConfigurationValues first, and NEVER use
   `maxUnavailable: 100%` in production.** OVERWRITE replaces
   customizations (CoreDNS replicas, Corefile, VPC-CNI env vars) with
   EKS defaults. `maxUnavailable: 100%` drains all nodes simultaneously,
   taking the entire workload offline.

5. **NEVER skip the deprecated API scan (`kubent` / `kubectl convert`)
   or the post-upgrade `kubectl get apiservices | grep False` check.**
   Workloads using removed APIs fail to apply after the upgrade; a
   removed APIService can leave objects in `False` availability,
   causing silent workload failures.

Additional NEVER rules (concurrent updates, Auto Mode operator action,
hybrid node upgrades, deploy during mutation window, AMI version
selection, stuck node deletion, `--force` drain bypass, Fargate
restart planning) appear in the FORBIDDEN output patterns section
above and in `references/upgrade-procedures.md`.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`update-cluster-version`, `update-nodegroup-version`, `update-addon`,
  `kubectl drain`, `kubectl cordon`, `kubectl delete node`, `kubectl
  patch pdb`), emit: `CONFIRM: About to <operation> on <target> in
  account <account> region <region>. This will <consequence>. ROLLBACK
  ADVISORY: <control plane CANNOT be rolled back / node group CAN be
  rolled back if previous AMI available / PDB patch is reversible>.
  Proceed? (yes/no)`. Do NOT execute until the operator confirms.
- **Capture pre-state for rollback.** `aws eks describe-cluster --name
  <cluster> --output json > /tmp/<cluster>-pre-$(date +%s).json`,
  `kubectl get nodes -o wide > /tmp/nodes-pre-$(date +%s).txt`,
  `kubectl get pods --all-namespaces -o wide >
  /tmp/pods-pre-$(date +%s).txt`, `kubectl get
  poddisruptionbudgets --all-namespaces -o yaml >
  /tmp/pdbs-pre-$(date +%s).yaml`. The PDB capture is critical — patch
  PDBs to unblock drain, then restore them after the upgrade.
- **Back up add-on ConfigurationValues before update-addon.**
  `kubectl get deployment coredns -n kube-system -o yaml >
  /tmp/coredns-preupgrade.yaml`, `kubectl get daemonset aws-node -n
  kube-system -o yaml > /tmp/vpc-cni-preupgrade.yaml`,
  `kubectl get daemonset kube-proxy -n kube-system -o yaml >
  /tmp/kube-proxy-preupgrade.yaml`.
- **Verify add-on compatibility with both versions.**
  `aws eks describe-addon-versions --kubernetes-version <target>
  --addon-name <name>`. The add-on version must be in the
  `compatibilities` list for the target Kubernetes.
- **Run kubent before the control plane upgrade.**
  `kubent --kubernetes-version <target>` or `kubectl convert
  --output-version <new-api-version> -f <manifest>`. Fix all flagged
  resources BEFORE the upgrade.
- **Verify subnet IP capacity for surge upgrade.** Use `aws ec2
  describe-subnets --subnet-ids <subnet-id> --query
  'Subnets[0].AvailableIpAddressCount'`. Reserve at least
  `maxSurge + maxUnavailable` IPs per subnet.
- **Verify PDBs allow disruption.** For each PDB:
  `kubectl get pdb <name> -n <ns> -o
  jsonpath='{.status.disruptionsAllowed}'`. If 0, drain will fail.
- **Fargate-only clusters:** no node drain needed; pods restart
  automatically. **EKS Auto Mode clusters:** do NOT run
  `update-nodegroup-version` — run only `update-cluster-version` and
  addon upgrades.

## Recent AWS features (2024-2026)

Moved verbatim to `references/advanced-patterns.md` — see "**Recent AWS features (2024-2026)**" (load on demand).
Applies when: the cluster uses Auto Mode, hybrid nodes, access entries, Pod Identity, surge updates, or Karpenter v1.

## References (load on demand)

- [references/upgrade-procedures.md](references/upgrade-procedures.md) — canonical end-to-end upgrade sequence and per-operation procedures.
- [references/version-compatibility.md](references/version-compatibility.md) — EKS/add-on compatibility matrices and deprecated-API removal tables.
- [references/worked-examples.md](references/worked-examples.md) — full end-to-end worked examples (READY control-plane, READY nodegroup surge, BLOCKED PDB).
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — live-account pre-flight command gate (moved verbatim from this file).
- [references/advanced-patterns.md](references/advanced-patterns.md) — cost/time baselines, mindset deep dive, Step 0 expert behaviors, and recent AWS features (moved verbatim from this file).

## Domain

AWS CloudOps / EKS Compute Upgrades & Lifecycle Management.

## AWS documentation

- **Amazon EKS User Guide** — https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html
- **Updating an EKS cluster** — https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html
- **EKS add-ons** — https://docs.aws.amazon.com/eks/latest/userguide/eks-add-ons.html
- **Managed node groups** — https://docs.aws.amazon.com/eks/latest/userguide/managed-node-groups.html
- **Updating a managed node group** — https://docs.aws.amazon.com/eks/latest/userguide/update-managed-node-group.html
- **EKS Auto Mode** — https://docs.aws.amazon.com/eks/latest/userguide/auto-mode.html
- **EKS Hybrid Nodes** — https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes.html
- **EKS API Reference** — https://docs.aws.amazon.com/eks/latest/APIReference/
- **EKS CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/eks/
- **Kubernetes deprecation guide** — https://kubernetes.io/docs/reference/using-api/deprecation-guide/
- **kubent (kubernetes-deprecation)** — https://github.com/doitintl/kube-deprecation
