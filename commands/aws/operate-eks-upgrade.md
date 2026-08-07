---
description: Operate EKS cluster and node group upgrade workflows — control plane upgrade, node group rolling/surge upgrade, add-on bridge versions, PDB pre-checks, deprecated API scan via kubent, self-managed node drain, EKS Auto Mode and hybrid nodes — with deterministic pre-checks, CONFIRM gate, and post-verification.
nl_triggers:
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
  - "rollback EKS node group"
routes_to: eks-upgrade-operator
---

# /aws:operate-eks-upgrade

Activate the `eks-upgrade-operator` skill and plan/execute an EKS
cluster or node group upgrade with deterministic pre-checks, CONFIRM
gate, and post-verification.

## What it does

Reads a cluster configuration plus the intended operation and applies
the priority-ordered pre-check sequence:

1. Pre-flight cluster metadata gate — short-circuit non-ACTIVE states,
  in-progress updates, EKS Auto Mode / hybrid node detection.
2. Pre-check gate — BLOCKED if any check fails (target version not
   available, sequential minor required, add-ons incompatible,
   deprecated APIs in use, PDB blocks drain, capacity insufficient).
3. READY — emit the exact CLI sequence with all flags populated, the
   expected side-effects (API mutation window, node drain sequence,
   Fargate restart), and the CONFIRM gate prompt with the rollback
   advisory (control plane CANNOT be rolled back).
4. Execute behind CONFIRM gate — capture pre-state, execute the CLI,
   poll `describe-update` until Successful.
5. Post-verification — cluster version target, all nodes Ready and at
   target version, no CrashLoopBackOff, addon versions match,
   apiservices healthy, canary deployment healthy. COMPLETED only if
   ALL post-verification checks pass.

Emits a deterministic VERDICT per upgrade:

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
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
ROLLBACK: <control plane CANNOT be rolled back / node group CAN be rolled back>
NOTES: <mutation window, Fargate restart, addon caveats>
```

## When to invoke

Paste a cluster configuration plus the intended operation, or just
describe the scenario and ask any of:

- "upgrade this cluster to the next Kubernetes version"
- "upgrade the managed node group to match the control plane"
- "pre-upgrade VPC-CNI to a bridge version"
- "the node group upgrade is stuck on a PDB"
- "verify the cluster after the 1.29 upgrade"
- "scan for deprecated APIs before upgrading"

A bare cluster-name + any upgrade verb ("upgrade the cluster", "refresh
the node groups") also routes here via the orchestrator.

## Inputs

- Cluster configuration (`describe-cluster` JSON): `status`, `version`,
  `logging`, `accessConfig.authenticationMode`, `computeConfig` (Auto
  Mode), `remoteNetworkConfig` (hybrid nodes).
- EKS add-ons (`list-addons` + `describe-addon` per add-on): `addonVersion`,
  `status`, `configurationValues`.
- Managed node groups (`list-nodegroups` + `describe-nodegroup`): `version`,
  `status`, `instanceTypes`, `subnets`, `scalingConfig`, `updateConfig`.
- Add-on compatibility (`describe-addon-versions
  --kubernetes-version <target>`): compatible versions for the target.
- PDB list (`kubectl get poddisruptionbudgets --all-namespaces`):
  `minAvailable`, `allowedDisruptions`.
- Node versions (`kubectl get nodes -o wide`): `STATUS`, `VERSION`.
- kubent scan output (deprecated API report for the target version).

## Outputs

- One VERDICT block per upgrade.
- PRE_CHECKS list with `[PASS]` / `[FAIL]` per check and reason for
  failure.
- For READY: the exact CLI sequence, expected duration, expected side-
  effects, the CONFIRM gate prompt, and the rollback advisory.
- For COMPLETED: POST_VERIFY list with `[PASS]` per check, the new
  cluster/node version, addon versions match confirmation, monitoring
  recommendations.
- For BLOCKED: the specific failure reason and the remediation step
  (e.g., `update-addon --addon-version <bridge>` for incompatible
  add-ons, `kubectl patch pdb` for blocked drains, target N+1 instead
  of N+2 for skip-version attempts).

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 4 Operate specialist for EKS upgrades).
- `/aws:audit-eks-cluster` for the audit-side counterpart — auditing
  cluster security posture and version-lifecycle status without changing
  state.
- `/aws:deploy-eks-cluster` for the deploy-side counterpart — provisioning
  new clusters with the latest Kubernetes version and add-ons.
