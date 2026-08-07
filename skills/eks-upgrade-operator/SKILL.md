---
name: eks-upgrade-operator
description: >-
  Operates EKS cluster and node group upgrade workflows safely — pre-
  upgrade checks (current Kubernetes version, addon compatibility
  matrices, node group version drift, pod disruption budgets, deprecated
  API usage via kubent), control plane upgrade sequence (update-cluster-
  version first, wait, then node groups), managed node group upgrade
  strategies (rolling update default, force update with maxUnavailable
  and maxSurge surge parameters), self-managed node drain and cordon,
  EKS add-on upgrades (VPC-CNI, CoreDNS, kube-proxy) BEFORE nodes, and
  full post-upgrade verification (all nodes Ready, no CrashLoopBackOff,
  addon versions match new Kubernetes). Emits READY with pre-checks,
  BLOCKED with specific blocker, or COMPLETED with verification. Use
  when upgrading an EKS cluster, refreshing managed node groups, aligning
  add-ons to a new Kubernetes version, or recovering from a failed
  upgrade.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). No AWS CLI required for offline plan classification.
  Live-account operations use aws eks describe-cluster, update-cluster-
  version, describe-addon, describe-addon-versions, update-addon,
  describe-nodegroup, update-nodegroup-version, describe-update, aws ec2
  describe-instances, kubectl get nodes / drain / cordon / uncordon,
  kubectl get poddisruptionbudgets, and kubent (kubernetes deprecation
  checker) (AWS CLI v2, SSO or key-based credentials, kubectl 1.28+).
keywords:
  - EKS
  - Kubernetes
  - cluster upgrade
  - version upgrade
  - update-cluster-version
  - update-nodegroup-version
  - managed node group
  - self-managed nodes
  - kops
  - fargate
  - VPC-CNI
  - CoreDNS
  - kube-proxy
  - EKS add-ons
  - pod disruption budget
  - PDB
  - deprecated API
  - kubent
  - kubectl drain
  - kubectl cordon
  - maxUnavailable
  - maxSurge
  - force update
  - rolling update
  - EKS Auto Mode
  - EKS hybrid nodes
tags: [eks, kubernetes, compute, upgrade, node-group, addons, pdb, kubent, operate]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 4
  supports_pipeline: true
  entry_point: false
  family: Compute
  task_type: operate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY | BLOCKED | COMPLETED"
  when_to_use: >-
    Upgrading an EKS cluster to a new Kubernetes version, refreshing
    managed node groups, aligning EKS add-ons (VPC-CNI, CoreDNS, kube-
    proxy) to a new Kubernetes version, draining self-managed nodes for
    upgrade, diagnosing a stuck node group upgrade, recovering from a
    failed upgrade, or validating post-upgrade cluster health.
  activation_triggers:
    - "upgrade EKS cluster"
    - "upgrade Kubernetes version"
    - "update-cluster-version"
    - "upgrade node group"
    - "update-nodegroup-version"
    - "upgrade EKS addons"
    - "VPC-CNI upgrade"
    - "CoreDNS upgrade"
    - "kube-proxy upgrade"
    - "pod disruption budget blocking"
    - "PDB blocking drain"
    - "deprecated API check"
    - "kubent"
    - "kubectl drain nodes"
    - "EKS Auto Mode upgrade"
    - "EKS hybrid nodes upgrade"
  invocation_schema: >-
    Input: either (a) an EKS cluster configuration (describe-cluster
    output) plus the intended operation (pre-upgrade-check, upgrade-
    control-plane, upgrade-nodegroup, upgrade-addon, post-upgrade-
    verify), OR (b) a cluster-name + operation for live-account
    execution. Output: deterministic OPERATION / VERDICT / PRE_CHECKS /
    STEPS / POST_VERIFY / NOTES block per upgrade, where VERDICT is one
    of READY, BLOCKED, COMPLETED.
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

**Cost/time baselines (2026):**

- Control plane upgrade: 10-30 minutes (cluster is briefly unavailable
  for API mutations during etcd migration, but API reads continue).
- Managed node group rolling update: ~5 minutes per node (drain, replace,
  wait for Ready).
- Managed node group force update with surge: faster wall-clock, but
  requires spare capacity.
- Add-on upgrade: 1-3 minutes per add-on.
- Self-managed node drain: 2-10 minutes per node (depends on graceful
  shutdown).
- EKS extended support surcharge (after standard support ends): $0.10
  per cluster-hour.

## Mindset

**One-line takeaway:** EKS upgrades are a one-way operation — the
control plane CANNOT be rolled back. Add-ons first, control plane
second, node groups third, verify after each step. Driven by three EKS
realities:

- **Control plane upgrades are irreversible.** `update-cluster-version`
  migrates etcd to the new Kubernetes schema. There is no AWS API to
  roll back. If the upgrade fails partway, AWS support may be able to
  recover the cluster, but the operator cannot. Always pre-check add-ons
  and deprecated APIs BEFORE issuing `update-cluster-version`.

- **The sequence matters.** AWS requires that add-ons be compatible with
  the target Kubernetes version BEFORE the control plane upgrade. Then
  the control plane upgrades. Then node groups upgrade to match. Skipping
  the addon-first step leaves VPC-CNI / CoreDNS / kube-proxy running
  versions incompatible with the new control plane — pod networking and
  DNS can break.

- **PDBs and drain ordering cause most upgrade stalls.** A pod
  disruption budget with `minAvailable: 100%` (or matching the replica
  count) blocks `kubectl drain` indefinitely. Managed node group rolling
  updates also respect PDBs — a misconfigured PDB halts the upgrade
  with nodes stuck in `NotReady` until the PDB is patched.

## Pre-flight: cluster metadata gate

Run before classification. Misclassifying these produces wrong plans.

**Pagination:** `aws eks list-clusters` and `aws eks list-nodegroups`
paginate at 100/page — drain `--next-token` to completion. `kubectl get
pods --all-namespaces` paginates server-side; use `--all-namespaces` with
`-o json` and pipe to `jq` for filtering.

**Live-account pre-flight (skip if offline plan audit):**
1. `aws eks describe-cluster --name <cluster>` — confirm `status:
   ACTIVE`; capture `version`, `platformVersion`, `addonsConfig`,
   `accessConfig.authenticationMode`, `computeConfig` (Auto Mode),
   `remoteNetworkConfig` (hybrid nodes).
2. `aws eks list-addons --cluster-name <cluster>` — list installed EKS
   add-ons.
3. `aws eks describe-addon --cluster-name <cluster> --addon-name
   <name>` per add-on — capture `addonVersion`, `status`,
   `configurationValues`.
4. `aws eks describe-addon-versions --kubernetes-version <target>` —
   list compatible add-on versions for the target Kubernetes.
5. `aws eks list-nodegroups --cluster-name <cluster>` — list all
   managed node groups.
6. `aws eks describe-nodegroup --cluster-name <cluster> --nodegroup-name
   <name>` per node group — capture `version`, `status`,
   `instanceTypes`, `subnets`, `scalingConfig`, `amiType`, `updateConfig`
   (maxUnavailable, maxSurge).
7. `kubectl get nodes -o wide` — verify all nodes are `Ready` and on the
   expected version.
8. `kubectl get poddisruptionbudgets --all-namespaces` — find PDBs that
   might block drain.
9. `kubectl get pods --all-namespaces --field-selector
   status.phase=Running` — sample workload; pair with `kubent` for
   deprecated API detection.
10. `kubectl get apiversions` — list all API groups/versions in use
    (for deprecated API scan).

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
experience. Each changes a plan if ignored:

- **EKS requires sequential minor-version upgrades.** You cannot skip
  from 1.27 to 1.29 — you must upgrade to 1.28 first, then 1.29. Each
  upgrade is a separate `update-cluster-version` call. Patch version
  bumps (e.g., 1.28.2 -> 1.28.3) happen automatically; minor version
  bumps are always operator-driven.

- **The control plane upgrade is one-way.** Once `update-cluster-version`
  starts, you cannot cancel it. AWS support may be able to recover a
  failed upgrade, but there is no customer-facing rollback API. The
  pre-checks are the safety gate.

- **API server has brief unavailability during the upgrade.** Expect
  5-15 minutes where API mutations (create/update/delete) are rejected.
  API reads continue. Applications continue to run. Plan for the
  mutation window; do not deploy during a control plane upgrade.

- **Add-ons must be compatible with BOTH current and target Kubernetes.**
  Upgrade add-ons to a "bridge" version that supports both Kubernetes
  versions BEFORE the control plane upgrade. Then upgrade add-ons again
  to the latest version AFTER the control plane reaches the target. The
  pre-upgrade add-on upgrade is the one most operators miss.

- **VPC-CNI upgrade requires care — pod networking depends on it.** The
  VPC-CNI daemonset runs on every node. An incompatible VPC-CNI on a new
  Kubernetes version can prevent new pods from getting IP addresses
  (pod stuck in `ContainerCreating` with `FailedCreateNetworkContainer`).
  Always upgrade VPC-CNI before node groups.

- **CoreDNS deployment replicas and config may need adjustment.** EKS
  manages CoreDNS via the EKS add-on, but the `coredns` Deployment
  replicas and the `Corefile` ConfigMap are user-editable. An upgrade
  resets these to defaults if `--resolve-conflicts OVERWRITE` is used;
  preserve customizations with `--configuration-values`.

- **kube-proxy upgrade is invisible but critical.** kube-proxy programs
  iptables/ipvs rules on each node. A version mismatch with the kubelet
  causes subtle service-routing bugs. Always upgrade kube-proxy to match
  the new Kubernetes version.

- **Managed node group rolling update respects PDBs.** If a PDB blocks
  eviction of a pod on the node being drained, the rolling update halts.
  The node stays in `NotReady` until the PDB allows eviction or the
  operator force-deletes the pod.

- **Force update with surge parameters (`maxUnavailable`, `maxSurge`).**
  `updateConfig.maxSurge: 1` means the autoscaler creates one new node
  BEFORE draining the old one. This is faster but requires spare IP
  capacity in the subnet and spare instance quota. `maxUnavailable: 2`
  means drain two nodes at a time. The default is `maxUnavailable: 1`
  (one at a time, no surge).

- **Fargate pods restart on control plane upgrade.** When the control
  plane Kubernetes version changes, Fargate drains and restarts all
  Fargate pods to align the kubelet version. Plan for a brief restart
  window for Fargate workloads.

- **EKS Auto Mode manages node lifecycle.** When `computeConfig.enabled:
  true`, EKS automatically provisions and upgrades nodes. The operator
  does not run `update-nodegroup-version` — Auto Mode handles it after
  the control plane upgrade. The operator still runs addon upgrades.

- **EKS hybrid nodes are operator-upgraded.** When `remoteNetworkConfig`
  is present, hybrid nodes attached to the cluster do NOT auto-upgrade
  with `update-nodegroup-version`. The operator must upgrade the on-prem
  node components (kubelet, container runtime) separately and re-attach.

- **`kubent` (kubernetes-deprecation) scans for removed APIs.** Run
  `kubent` against the cluster (or `kubectl convert --output-version`)
  to detect workloads using APIs removed in the target version. Examples:
  - 1.22 removed: `networking.k8s.io/v1beta1 Ingress`, `extensions/v1beta1
    Ingress`, `policy/v1beta1 PodSecurityPolicy`.
  - 1.25 removed: `batch/v1beta1 CronJob`, `policy/v1beta1
    PodSecurityPolicy` (already gone), `autoscaling/v2beta1
    HorizontalPodAutoscaler`.
  - 1.29 removed: `flowcontrol.apiserver.k8s.io/v1beta1
    FlowSchema/PriorityLevelConfiguration`.

- **A failed `update-cluster-version` leaves the cluster in `UPDATING`
  or `FAILED`.** AWS auto-retries transient failures. Persistent
  failures require AWS support intervention. Monitor via
  `aws eks describe-update`.

- **`describe-update` is the progress API.** Track upgrade progress via
  `aws eks describe-update --name <cluster> --update-id <id>`. Statuses:
  `InProgress`, `Successful`, `Failed`, `Cancelled`.

- **Addon upgrades can fail with `Conflicting` errors.** If you (or a
  GitOps controller) edited the add-on's ConfigurationValues via kubectl,
  an EKS add-on upgrade may conflict. Use `--resolve-conflicts OVERWRITE`
  to let EKS win, or `--resolve-conflicts NONE` to preserve local edits
  (upgrade may fail).

- **Pod security standards changed in 1.25.** PodSecurityPolicy was
  removed; Pod Security Admission (PSA) replaced it. Workloads relying
  on PSP must be migrated to PSA before upgrading to 1.25+.

- **EKS extended support starts after standard support ends.** Standard
  support is ~14 months. Extended support adds $0.10/cluster-hour. After
  extended support, AWS force-upgrades the cluster (typically to N+1).
  Skipping upgrades triggers forced upgrades with no operator control.

- **Control plane logging is essential during upgrade.** Enable all five
  log types before upgrading. The `audit` log captures Kubernetes API
  calls during the upgrade; `api` captures the mutation-window errors;
  `authenticator` captures IAM-to-RBAC decisions if access entries
  change.

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

### Worked example — upgrade-control-plane (1.28 -> 1.29)

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
    (will upgrade to v1.29.x after control plane)
  - [PASS] kubent scan clean for 1.29 (no FlowSchema v1beta1 in use)
  - [PASS] all managed node groups at 1.28 (will upgrade after control plane)
  - [PASS] all nodes Ready
STEPS:
  1. CONFIRM: About to update-cluster-version on prod-cluster-01
     from 1.28 to 1.29 in account 111111111111 region us-east-1.
     This will cause a 5-15 minute API mutation window (API reads
     continue, applications keep running). ROLLBACK ADVISORY: EKS
     control plane upgrades CANNOT be rolled back. Estimated total
     duration: 15-30 minutes. Proceed? (yes/no)
  2. aws eks update-cluster-version \
       --name prod-cluster-01 \
       --kubernetes-version 1.29 \
       --region us-east-1
  3. Poll until Successful:
     aws eks describe-update --name prod-cluster-01 \
       --update-id <update-id-from-step-2>
  4. After control plane is 1.29, upgrade add-ons to 1.29-compatible:
     aws eks update-addon --cluster-name prod-cluster-01 \
       --addon-name kube-proxy --addon-version v1.29.3-minimal-1 \
       --resolve-conflicts OVERWRITE
     aws eks update-addon --cluster-name prod-cluster-01 \
       --addon-name coredns --addon-version v1.11.1-eksbuild.6 \
       --resolve-conflicts OVERWRITE
POST_VERIFY:
  - (pending execution)
  - aws eks describe-cluster --name prod-cluster-01 → version 1.29
  - kubectl get nodes -o wide → all nodes Ready, still on 1.28
    (node group upgrade is the next operation)
  - kubectl get pods -n kube-system → no CrashLoopBackOff
  - kubectl get apiservices | grep False → none
ROLLBACK: control plane CANNOT be rolled back (etcd migration is one-way)
NOTES:
  - Node groups are still on 1.28 — they are incompatible with the new
    control plane. Run upgrade-nodegroup for each managed node group
    immediately after this operation completes.
  - Fargate pods will restart automatically to align kubelet with 1.29.
    Plan for a brief restart window for Fargate workloads.
  - The API server will reject mutations for 5-15 minutes during the
    etcd migration. Do not run kubectl apply during this window.
  - If the upgrade fails partway, AWS auto-retries transient failures.
    Persistent failures require AWS support — the cluster may be in
    UPDATING or FAILED state.
```

### Worked example — upgrade-nodegroup (rolling update)

```text
OPERATION: upgrade-nodegroup
VERDICT: READY
TARGET: prod-cluster-01 / nodegroup: prod-ng-1 (1.28 -> 1.29)
PRE_CHECKS:
  - [PASS] node group status: ACTIVE
  - [PASS] cluster control plane at 1.29 (target matches)
  - [PASS] target node version 1.29 <= cluster version 1.29
  - [PASS] PDB check: 2 PDBs found, both allow >= 1 disruption
  - [PASS] subnet spare IPs: 47 available (>= maxSurge+1)
  - [PASS] EC2 instance quota: 20 m5.large in use, 30 quota
    (10 spare, covers maxSurge: 2)
  - [PASS] updateConfig: maxUnavailable: 1, maxSurge: 2
STEPS:
  1. CONFIRM: About to update-nodegroup-version on prod-cluster-01 /
     prod-ng-1 from 1.28 to 1.29 in account 111111111111 region
     us-east-1. Strategy: surge (maxUnavailable: 1, maxSurge: 2). EKS
     will create 2 new nodes on 1.29, then drain 1.28 nodes one at a
     time. PDBs will be respected. Estimated duration: 20-30 minutes
     (5 nodes, ~5 minutes per drain). ROLLBACK ADVISORY: node group
     CAN be rolled back to 1.28 if the previous AMI is available.
     Proceed? (yes/no)
  2. aws eks update-nodegroup-version \
       --cluster-name prod-cluster-01 \
       --nodegroup-name prod-ng-1 \
       --kubernetes-version 1.29 \
       --release-version 1.29.3-20240807 \
       --region us-east-1
  3. Poll until Successful:
     aws eks describe-update --name prod-cluster-01 \
       --update-id <update-id>
  4. Watch node replacement:
     kubectl get nodes -w
POST_VERIFY:
  - (pending execution)
  - aws eks describe-nodegroup --cluster-name prod-cluster-01 \
      --nodegroup-name prod-ng-1 → version 1.29, status ACTIVE
  - kubectl get nodes -l eks.amazonaws.com/nodegroup=prod-ng-1 → all
    Ready, all at 1.29
  - kubectl get pods --all-namespaces --field-selector \
      spec.nodeName=<any-upgraded-node> → no CrashLoopBackOff
ROLLBACK: node group CAN be rolled back to 1.28 if the 1.28 AMI is
          still in the EKS AMI repository
NOTES:
  - The surge strategy (maxSurge: 2) creates 2 new nodes before draining,
    so workload capacity is never below the original count. This requires
    spare subnet IPs and instance quota.
  - If a PDB blocks drain on a node, the upgrade halts on that node.
    Patch the PDB to allow at least 1 disruption, then resume.
  - DaemonSets (VPC-CNI, kube-proxy, node-exporter) are not evicted
    during drain (--ignore-daemonsets). They will restart on the new
    nodes automatically.
```

### Worked example — BLOCKED (PDB blocks drain)

```text
OPERATION: upgrade-nodegroup
VERDICT: BLOCKED
TARGET: prod-cluster-01 / nodegroup: prod-ng-1 (1.28 -> 1.29)
PRE_CHECKS:
  - [PASS] node group status: ACTIVE
  - [PASS] cluster control plane at 1.29
  - [PASS] target node version 1.29 <= cluster version 1.29
  - [FAIL] PDB "payments-api-pdb" in namespace payments has
    minAvailable: 4 and only 4 replicas exist. allowedDisruptions: 0.
    Drain cannot evict any pod. The upgrade would halt on every node
    running a payments-api pod.
  - [PASS] subnet spare IPs: 47 available
STEPS: (none — pre-checks failed)
POST_VERIFY: (none)
ROLLBACK: (none)
NOTES:
  - Patch the PDB to allow at least 1 disruption before retrying:
    kubectl patch pdb payments-api-pdb -n payments --type=json \
      -p='[{"op":"replace","path":"/spec/minAvailable","value":3}]'
    Then verify: kubectl get pdb payments-api-pdb -n payments \
      -o jsonpath='{.status.disruptionsAllowed}'
    DisruptionsAllowed should be >= 1.
  - Alternatively, scale the deployment to 5 replicas so minAvailable: 4
    still allows 1 disruption:
    kubectl scale deployment payments-api -n payments --replicas=5
  - After the upgrade, restore the PDB to its original value.
```

## Anti-Patterns — NEVER

- NEVER skip the add-on pre-upgrade. EKS requires add-ons to be
  compatible with BOTH the current and target Kubernetes versions
  BEFORE the control plane upgrade. Skipping this leaves VPC-CNI /
  CoreDNS / kube-proxy running versions incompatible with the new
  control plane — pod networking and DNS can break cluster-wide.

- NEVER execute `update-cluster-version` without confirming the operator
  understands the upgrade is ONE-WAY. There is no customer-facing
  rollback API. The pre-checks are the safety gate.

- NEVER skip a minor version. EKS requires sequential minor-version
  upgrades (1.27 -> 1.28 -> 1.29). Attempting 1.27 -> 1.29 directly
  returns `InvalidParameterException` or silently upgrades only to 1.28.

- NEVER upgrade node groups BEFORE the control plane. Node group
  versions must be <= the control plane version. A node group on 1.29
  with a control plane on 1.28 produces kubelet-vs-apiserver schema
  mismatches.

- NEVER issue `update-cluster-version` while another update is in
  progress. EKS rejects concurrent updates with `InvalidParameterException`.
  Always check `describe-update` first.

- NEVER run `kubectl drain <node>` without `--ignore-daemonsets` and
  `--delete-emptydir-data`. DaemonSets (VPC-CNI, kube-proxy) cannot be
  evicted; without `--ignore-daemonsets` the drain hangs forever. Pods
  using `emptyDir` for scratch storage need `--delete-emptydir-data`
  (or `--force` to skip confirmation) to be evicted.

- NEVER upgrade a node group without first checking PDBs. A PDB with
  `minAvailable: 100%` (or matching replicas) blocks drain indefinitely.
  The node group upgrade halts on the affected node until the PDB is
  patched. Always pre-check `kubectl get poddisruptionbudgets
  --all-namespaces` and compute `disruptionsAllowed` per node.

- NEVER use `maxUnavailable: 100%` in a managed node group updateConfig
  for a production cluster. It drains all nodes simultaneously, taking
  the entire workload offline. Reserve `maxUnavailable: 100%` for
  development clusters with redundancy elsewhere.

- NEVER use `--resolve-conflicts OVERWRITE` on an EKS add-on without
  backing up the current ConfigurationValues first. OVERWRITE replaces
  your customizations with EKS defaults. For CoreDNS, this means
  replicas and the Corefile ConfigMap reset to defaults — losing
  custom stub-domains or forward configurations.

- NEVER assume EKS Auto Mode requires no operator action. Auto Mode
  manages node lifecycle, but the operator still runs addon upgrades
  and the control plane upgrade. Auto Mode nodes align to the new
  Kubernetes version AFTER the control plane reaches the target.

- NEVER assume EKS hybrid nodes upgrade automatically. Hybrid nodes
  attached via `remoteNetworkConfig` do NOT participate in
  `update-nodegroup-version`. The operator must upgrade the on-prem
  kubelet and container runtime separately and re-attach.

- NEVER deploy workloads during the control plane upgrade's API mutation
  window. API writes (create/update/delete) are rejected for 5-15
  minutes. Reads continue. Applications continue to run, but CI/CD
  pipelines will fail.

- NEVER skip the deprecated API scan (`kubent` / `kubectl convert`).
  Workloads using removed APIs will fail to apply after the upgrade —
  the API server rejects them. Detect BEFORE the upgrade; convert the
  manifest to the new API version; deploy; THEN upgrade the cluster.

- NEVER assume the latest EKS AMI is automatically the right one for
  your cluster. The AMI must match the cluster's Kubernetes minor
  version. Specify `--release-version` explicitly when calling
  `update-nodegroup-version` to avoid surprises.

- NEVER delete a stuck node from a managed node group with `kubectl
  delete node` while the upgrade is in progress. The EKS-managed
  autoscaler will recreate the node, but the upgrade updateId may lose
  track of it. Use `aws eks describe-update` and AWS support for stuck
  managed node group upgrades.

- NEVER use `kubectl drain --force` to bypass PDBs without operator
  confirmation. `--force` deletes pods that don't tolerate the eviction
  — including single-replica stateful workloads. Data loss is possible.

- NEVER forget Fargate pods restart on control plane upgrade. The
  kubelet version must align with the new control plane. Plan for a
  brief restart window; Fargate pods may take 30-60 seconds to
  reschedule.

- NEVER skip post-upgrade verification of `kubectl get apiservices |
  grep False`. A deprecated API removal can leave an APIService object
  in `False` availability — workloads depending on it fail silently.

- NEVER attempt to roll back a control plane upgrade by restoring an
  etcd backup taken before the upgrade. EKS does not expose etcd backup
  / restore to customers. The only recovery path for a failed control
  plane upgrade is AWS support.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`update-cluster-version`, `update-nodegroup-version`, `update-addon`,
  `kubectl drain`, `kubectl cordon`, `kubectl delete node`, `kubectl
  patch pdb`), emit: `CONFIRM: About to <operation> on <target> in
  account <account> region <region>. This will <consequence>. ROLLBACK
  ADVISORY: <control plane CANNOT be rolled back / node group CAN be
  rolled back if previous AMI available / PDB patch is reversible>.
  Proceed? (yes/no)`. Do NOT execute until the operator confirms.

- **Capture pre-state for rollback.** Before any upgrade:
  `aws eks describe-cluster --name <cluster> --output json >
  /tmp/<cluster>-pre-$(date +%s).json`, `kubectl get nodes -o wide >
  /tmp/nodes-pre-$(date +%s).txt`, `kubectl get pods --all-namespaces
  -o wide > /tmp/pods-pre-$(date +%s).txt`, `kubectl get
  poddisruptionbudgets --all-namespaces -o yaml >
  /tmp/pdbs-pre-$(date +%s).yaml`. The PDB capture is critical — patch
  PDBs to unblock drain, then restore them after the upgrade.

- **Back up add-on ConfigurationValues before update-addon.**
  `kubectl get deployment coredns -n kube-system -o yaml >
  /tmp/coredns-preupgrade.yaml`, `kubectl get daemonset aws-node -n
  kube-system -o yaml > /tmp/vpc-cni-preupgrade.yaml`,
  `kubectl get daemonset kube-proxy -n kube-system -o yaml >
  /tmp/kube-proxy-preupgrade.yaml`. These captures preserve
  customizations that `--resolve-conflicts OVERWRITE` would discard.

- **Verify add-on compatibility with both versions.**
  `aws eks describe-addon-versions --kubernetes-version <target>
  --addon-name <name>`. The add-on version must be in the
  `compatibilities` list for the target Kubernetes.

- **Run kubent before the control plane upgrade.**
  `kubent --kubernetes-version <target>` or `kubectl convert
  --output-version <new-api-version> -f <manifest>`. Fix all flagged
  resources BEFORE the upgrade — the API server will reject removed APIs
  post-upgrade.

- **Verify subnet IP capacity for surge upgrade.** Each new node in the
  surge consumes one IP from its subnet. Use `aws ec2
  describe-subnets --subnet-ids <subnet-id> --query
  'Subnets[0].AvailableIpAddressCount'`. Reserve at least
  `maxSurge + maxUnavailable` IPs per subnet.

- **Verify PDBs allow disruption.** For each PDB:
  `kubectl get pdb <name> -n <ns> -o jsonpath='{.status.disruptionsAllowed}'`.
  If the value is 0, drain will fail on any node running the PDB's pods.

- **For Fargate-only clusters:** no node drain is needed. Fargate pods
  restart automatically. Verify Fargate profile scheduling after the
  upgrade.

- **For EKS Auto Mode clusters:** do NOT run `update-nodegroup-version`
  — Auto Mode manages nodes. Run only `update-cluster-version` and
  addon upgrades; Auto Mode handles the rest.

## Recent AWS features (2024-2026)

- **EKS Auto Mode (2024-2025):** EKS Auto Mode manages node provisioning,
  scaling, and lifecycle automatically. When `computeConfig.enabled:
  true`, the operator runs only the control plane upgrade and addon
  upgrades — Auto Mode aligns node versions to the new Kubernetes
  version after the control plane reaches the target. The operator does
  not call `update-nodegroup-version`.

- **EKS Hybrid Nodes (2025):** EKS supports on-premises nodes attached
  to EKS clusters via `remoteNetworkConfig`. Hybrid nodes do NOT
  auto-upgrade with `update-nodegroup-version`. The operator must
  upgrade the on-prem kubelet and container runtime separately and
  re-attach the node. Verify the hybrid node's kubelet version matches
  the cluster's control plane.

- **EKS Access Entries (2024-2025):** EKS Access Entries replace the
  `aws-auth` ConfigMap. Before upgrading, verify the cluster's
  `authenticationMode` (`API`, `CONFIG_MAP`, `API_AND_CONFIG_MAP`).
  Clusters in `API` mode use access entries exclusively; ConfigMap
  edits have no effect. The upgrade does not change authenticationMode.

- **EKS Pod Identity (2024):** EKS Pod Identity provides IAM credentials
  to pods without OIDC trust policies. The EKS Pod Identity Agent addon
  must be at a version compatible with the target Kubernetes. Verify
  before upgrade.

- **Force update with surge parameters GA (2024):**
  `update-nodegroup-version` supports `updateConfig.maxUnavailable` and
  `updateConfig.maxSurge` for faster node group upgrades. The default is
  `maxUnavailable: 1, maxSurge: 0` (one at a time, no surge). Higher
  values speed up the upgrade but require spare capacity.

- **EKS Add-on ConfigurationValues (2024-2025):** Add-ons support
  structured ConfigurationValues via JSON patches. Use
  `--configuration-values` to apply structured changes (e.g., CoreDNS
  replicas, VPC-CNI environment variables). Use `--resolve-conflicts
  PRESERVE` to keep local edits on upgrade.

- **Extended support pricing (2024-2025):** EKS extended support costs
  $0.10/cluster-hour after standard support ends (~14 months). Plan
  upgrades to land before standard support ends to avoid the surcharge.
  After extended support, AWS force-upgrades the cluster.

- **Karpenter v1 (2025):** Karpenter v1 supports EKS cluster upgrades
  by drift-based node replacement. When the cluster Kubernetes version
  changes, Karpenter detects drift and replaces nodes. Verify the
  Karpenter `EC2NodePool` and `NodeClaim` resources allow the new
  Kubernetes version.

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
