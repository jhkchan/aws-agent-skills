
<!-- Moved verbatim from SKILL.md (eks-upgrade-operator) — progressive-disclosure restructure, lines 88-100 -->

## Cost/time baselines (2026)

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

<!-- Moved verbatim from SKILL.md (eks-upgrade-operator) — progressive-disclosure restructure, lines 104-126 -->

## Mindset — one-way control plane, sequence, PDB trap

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

<!-- Moved verbatim from SKILL.md (eks-upgrade-operator) — progressive-disclosure restructure, lines 199-248 -->

## Step 0 — expert knowledge: non-obvious EKS upgrade behaviors

- **EKS requires sequential minor-version upgrades** — cannot skip from
  1.27 to 1.29; each minor bump is a separate `update-cluster-version`.
- **The control plane upgrade is one-way** — no customer-facing rollback
  API; AWS support may recover a failed upgrade. Pre-checks are the
  safety gate. A failed upgrade leaves the cluster in `UPDATING` or
  `FAILED`; monitor via `aws eks describe-update`.
- **API server has 5-15 min mutation unavailability** during etcd
  migration — API reads continue, applications keep running. Do not
  deploy during the window.
- **Add-ons must be compatible with BOTH current and target Kubernetes.**
  Upgrade to a "bridge" version BEFORE the control plane, then to the
  latest AFTER. The pre-upgrade add-on upgrade is the step most
  operators miss.
- **VPC-CNI upgrade is critical** — an incompatible VPC-CNI prevents
  new pods from getting IPs (`ContainerCreating` /
  `FailedCreateNetworkContainer`). Always upgrade VPC-CNI before node
  groups.
- **CoreDNS and kube-proxy need care.** `--resolve-conflicts OVERWRITE`
  resets CoreDNS replicas and Corefile to defaults; preserve with
  `--configuration-values`. kube-proxy mismatch causes subtle
  service-routing bugs.
- **Managed node group rolling update respects PDBs** — a PDB blocking
  eviction halts the update with nodes stuck in `NotReady`.
- **Surge parameters (`maxUnavailable`, `maxSurge`)** — `maxSurge > 0`
  creates new nodes before draining; faster but needs spare IPs and
  quota. Default is `maxUnavailable: 1, maxSurge: 0`.
- **Fargate pods restart on control plane upgrade** — kubelet version
  must align; plan for a brief restart window.
- **EKS Auto Mode manages node lifecycle** — operator runs only control
  plane + addon upgrades; Auto Mode aligns nodes after control plane.
- **EKS hybrid nodes are operator-upgraded** — `remoteNetworkConfig`
  nodes do NOT auto-upgrade; upgrade on-prem kubelet and runtime
  separately.
- **`kubent` scans for removed APIs** — examples: 1.22 removed
  `networking.k8s.io/v1beta1 Ingress`, `extensions/v1beta1 Ingress`,
  `policy/v1beta1 PodSecurityPolicy`; 1.25 removed `batch/v1beta1
  CronJob`, `autoscaling/v2beta1 HorizontalPodAutoscaler`; 1.29 removed
  `flowcontrol.apiserver.k8s.io/v1beta1 FlowSchema`. Full table in
  Step 1 below.
- **Addon upgrades can fail with `Conflicting` errors** — use
  `--resolve-conflicts OVERWRITE` (EKS wins) or `NONE` (preserve local
  edits, upgrade may fail) or `PRESERVE`.
- **PodSecurityPolicy removed in 1.25** — migrate to Pod Security
  Admission (PSA) before upgrading to 1.25+.
- **EKS extended support** — standard support ~14 months; extended adds
  $0.10/cluster-hour; after that, AWS force-upgrades (no operator
  control).
- **Enable control plane logging before upgrading** — all five log
  types; `audit`, `api`, and `authenticator` are critical during
  upgrade.

<!-- Moved verbatim from SKILL.md (eks-upgrade-operator) — progressive-disclosure restructure, lines 595-641 -->

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

