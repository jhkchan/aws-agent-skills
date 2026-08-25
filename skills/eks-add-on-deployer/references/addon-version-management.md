# Add-On Version Management — Detail Reference

Deep reference on EKS add-on version compatibility, the
EKS-managed vs self-managed conflict lifecycle, conflict resolution
strategies, and migration patterns. Loaded on demand by the skill —
kept out of the main SKILL.md body so the provisioning procedure stays
scannable.

## Version compatibility model

Each EKS add-on version is validated against specific Kubernetes minor
versions and EKS platform versions. The EKS API enforces this at
creation time via `describe-addon-versions`.

### Querying compatible versions

```bash
# List all versions of vpc-cni compatible with K8s 1.30
aws eks describe-addon-versions \
  --addon-name vpc-cni \
  --kubernetes-version 1.30 \
  --query 'addons[0].addonVersions[*].{
    Version:addonVersion,
    Default:compatibilities[0].defaultVersion,
    PlatformVersions:compatibilities[0].clusterVersions
  }' \
  --output table
```

### Version naming conventions

| Add-on | Version format | Example |
|---|---|---|
| `vpc-cni` | `v<major>.<minor>.<patch>-eksbuild.<n>` | `v1.18.1-eksbuild.3` |
| `coredns` | `v<major>.<minor>.<patch>-eksbuild.<n>` | `v1.11.1-eksbuild.4` |
| `kube-proxy` | `v<major>.<minor>.<patch>-eksbuild.<n>` | `v1.30.0-eksbuild.3` |
| `aws-ebs-csi-driver` | `v<major>.<minor>.<patch>-eksbuild.<n>` | `v1.26.0-eksbuild.1` |
| `metrics-server` | `v<major>.<minor>.<patch>-eksbuild.<n>` | `v0.7.0-eksbuild.2` |

The Kubernetes minor version in the add-on version (e.g., `1.30` in
`v1.30.0-eksbuild.3` for kube-proxy) must match the cluster's K8s version.

### Default version

`describe-addon-versions` marks one version as `defaultVersion: true`.
This is the AWS-recommended version for new installations. The default
is updated by AWS as new versions are validated.

```bash
# Get only the default version
aws eks describe-addon-versions \
  --addon-name vpc-cni \
  --kubernetes-version 1.30 \
  --query 'addons[0].addonVersions[?compatibilities[0].defaultVersion==`true`].addonVersion' \
  --output text
```

## Conflict resolution lifecycle

When a self-managed add-on exists (e.g., `aws-node` DaemonSet installed
via Helm), enabling the EKS-managed add-on creates a conflict. The
`--resolve-conflicts` flag determines the outcome.

### Conflict detection

EKS detects conflicts by comparing the self-managed resource's state
with the EKS-managed add-on's desired state. Common conflicts:

| Resource | Conflict scenario |
|---|---|
| DaemonSet (`aws-node`, `kube-proxy`) | Self-managed DaemonSet exists; EKS add-on wants to manage it |
| Deployment (`coredns`, `metrics-server`) | Self-managed Deployment exists; EKS add-on wants to manage it |
| ServiceAccount | IRSA annotation on self-managed SA conflicts with add-on config |
| ConfigMap | Self-managed ConfigMap (e.g., coredns Corefile) conflicts with add-on config |

### Conflict resolution strategies

| Strategy | When to use | Behavior |
|---|---|---|
| `OVERWRITE` (create) | Migrating from self-managed to EKS-managed | EKS takes full control; self-managed config is replaced |
| `RETAIN` (create) | Coexistence with custom config | EKS keeps self-managed config; add-on may report health issues |
| `NONE` (create) | Diagnostic only | Conflict reported; add-on in DEGRADED |
| `PRESERVE` (update) | Safe update with customizations | Existing fields kept; new defaults applied for unset fields |
| `OVERWRITE` (update) | Force full EKS control on update | All config replaced with EKS defaults + configuration-values |

### Migration: self-managed to EKS-managed

```text
1. EXPORT current self-managed config
   kubectl get ds aws-node -n kube-system -o yaml > aws-node-backup.yaml

2. CREATE the EKS add-on with OVERWRITE
   aws eks create-addon --cluster-name <cluster> --addon-name vpc-cni \
     --resolve-conflicts OVERWRITE --service-account-role-arn <arn>

3. RE-APPLY customizations via --configuration-values
   aws eks update-addon --cluster-name <cluster> --addon-name vpc-cni \
     --configuration-values '{"env":{"ENABLE_PREFIX_DELEGATION":"true"}}' \
     --resolve-conflicts PRESERVE

4. VERIFY add-on status is ACTIVE
   aws eks describe-addon --cluster-name <cluster> --addon-name vpc-cni \
     --query 'addon.status'
```

## Add-on health and status

| Status | Meaning | Action needed |
|---|---|---|
| `CREATING` | Add-on is being installed | Wait |
| `ACTIVE` | Add-on is healthy and running | None |
| `UPDATING` | Add-on is being updated | Wait |
| `DELETING` | Add-on is being removed | Wait |
| `DEGRADED` | Add-on has health issues | Check `healthIssues` field |
| `UPDATE_FAILED` | Update could not complete | Check `healthIssues`, rollback |

### Checking health issues

```bash
aws eks describe-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni \
  --query 'addon.healthIssues'
```

Health issues include resource conflicts, version incompatibility, and
pod scheduling failures. Each issue has a `code`, `message`, and
optional `resourceIds`.

## Update strategies

### In-place update (recommended for minor version bumps)

```bash
aws eks update-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni \
  --addon-version v1.18.2-eksbuild.1 \
  --resolve-conflicts PRESERVE
```

### Configuration-only update (no version change)

```bash
aws eks update-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni \
  --configuration-values '{"env":{"WARM_PREFIX_TARGET":"2"}}' \
  --resolve-conflicts PRESERVE
```

### Rollback

```bash
# Roll back to the previous version
aws eks update-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni \
  --addon-version v1.18.0-eksbuild.1 \
  --resolve-conflicts PRESERVE
```

## Common pitfalls

1. **Version mismatch with K8s.** Always validate with
   `describe-addon-versions --kubernetes-version <version>`.
2. **OVERWRITE destroying customizations.** Export config before
   migrating. Use `PRESERVE` for updates.
3. **Ignoring DEGRADED status.** Check `healthIssues` and resolve
   conflicts.
4. **Forgetting to update after K8s upgrade.** After upgrading the
   cluster, add-on versions may need updating to match the new K8s
   version.
5. **Multiple IRSA roles for the same add-on.** Each add-on should have
   exactly one IAM role. Multiple roles cause credential conflicts.

## Expert heuristic: add-on version compatibility matrix (moved from SKILL.md)

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
