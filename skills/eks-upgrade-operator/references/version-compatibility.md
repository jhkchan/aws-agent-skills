# EKS Version Compatibility Matrix Reference

Load this reference when checking add-on compatibility, deprecated API
removals, or version-specific upgrade notes. The matrices below cover
EKS add-ons, Kubernetes API removals, and EKS lifecycle dates.

## EKS Kubernetes version lifecycle (2026)

| Kubernetes version | EKS release | Standard support end | Extended support end |
|---|---|---|---|
| 1.27 | 2023-04 | 2024-06 | 2024-09 |
| 1.28 | 2023-08 | 2024-10 | 2025-01 |
| 1.29 | 2023-12 | 2025-02 | 2025-05 |
| 1.30 | 2024-04 | 2025-06 | 2025-09 |
| 1.31 | 2024-08 | 2025-10 | 2026-01 |
| 1.32 | 2024-12 | 2026-02 | 2026-05 |
| 1.33 | 2025-04 | 2026-06 | 2026-09 |
| 1.34 | 2025-08 | 2026-10 | 2027-01 |

Standard support is ~14 months per version. Extended support adds
$0.10/cluster-hour. After extended support, AWS force-upgrades the
cluster to N+1.

## Outdated thresholds

| Cluster version (latest = 1.33) | Status | Action |
|---|---|---|
| 1.30 (N-3) | Approaching end-of-standard-support | Plan upgrade now |
| 1.29 (N-4) | In extended support | Paying surcharge; upgrade ASAP |
| 1.28 (N-5) | Past extended support; force-upgrade incoming | Upgrade immediately |
| Older | Force-upgraded by AWS | Recovery only via AWS support |

## EKS add-on compatibility matrix

### VPC-CNI (amazon-vpc-cni)

| VPC-CNI version | Kubernetes 1.27 | 1.28 | 1.29 | 1.30 | 1.31 | 1.32 | 1.33 |
|---|---|---|---|---|---|---|---|
| v1.15.x | Yes | Yes | No | No | No | No | No |
| v1.16.x | Yes | Yes | Yes | Yes | No | No | No |
| v1.17.x | No | Yes | Yes | Yes | Yes | No | No |
| v1.18.x | No | No | Yes | Yes | Yes | Yes | No |
| v1.19.x | No | No | No | Yes | Yes | Yes | Yes |
| v1.20.x | No | No | No | No | Yes | Yes | Yes |

Always check `describe-addon-versions --kubernetes-version <target>
--addon-name vpc-cni` for the canonical list. The EKS team ships bridge
versions for each Kubernetes minor.

### CoreDNS

| CoreDNS version | Kubernetes 1.27 | 1.28 | 1.29 | 1.30 | 1.31 | 1.32 | 1.33 |
|---|---|---|---|---|---|---|---|
| v1.10.x | Yes | Yes | Yes | No | No | No | No |
| v1.11.x | Yes | Yes | Yes | Yes | Yes | No | No |
| v1.11.1-eksbuild.4 | Yes | Yes | Yes | Yes | Yes | No | No |
| v1.11.3-eksbuild.x | No | Yes | Yes | Yes | Yes | Yes | No |
| v1.12.x | No | No | No | Yes | Yes | Yes | Yes |

### kube-proxy

kube-proxy versions track Kubernetes minor versions directly. The
correct kube-proxy for Kubernetes 1.29 is `v1.29.x-minimal-1` (where x
is the latest patch).

| Kubernetes version | kube-proxy version |
|---|---|
| 1.27 | v1.27.x-minimal-1 (or v1.27.x-eksbuild.1) |
| 1.28 | v1.28.x-minimal-1 |
| 1.29 | v1.29.x-minimal-1 |
| 1.30 | v1.30.x-minimal-1 |
| 1.31 | v1.31.x-minimal-1 |
| 1.32 | v1.32.x-minimal-1 |
| 1.33 | v1.33.x-minimal-1 |

Always match kube-proxy to the cluster's Kubernetes minor version.

## Deprecated Kubernetes API removals

### Removed in Kubernetes 1.22 (EKS 1.22)

| Removed API | Replacement |
|---|---|
| `extensions/v1beta1 Ingress` | `networking.k8s.io/v1 Ingress` |
| `networking.k8s.io/v1beta1 Ingress` | `networking.k8s.io/v1 Ingress` |
| `extensions/v1beta1 NetworkPolicy` | `networking.k8s.io/v1 NetworkPolicy` |
| `apiextensions.k8s.io/v1beta1 CustomResourceDefinition` | `apiextensions.k8s.io/v1 CustomResourceDefinition` |
| `admissionregistration.k8s.io/v1beta1 MutatingWebhookConfiguration` | `admissionregistration.k8s.io/v1 MutatingWebhookConfiguration` |
| `admissionregistration.k8s.io/v1beta1 ValidatingWebhookConfiguration` | `admissionregistration.k8s.io/v1 ValidatingWebhookConfiguration` |
| `rbac.authorization.k8s.io/v1beta1 Role/RoleBinding/ClusterRole/ClusterRoleBinding` | `rbac.authorization.k8s.io/v1` equivalents |
| `scheduling.k8s.io/v1beta1 PriorityClass` | `scheduling.k8s.io/v1 PriorityClass` |
| `storage.k8s.io/v1beta1 CSIDriver, CSINode, StorageClass, VolumeAttachment` | `storage.k8s.io/v1` equivalents |

### Removed in Kubernetes 1.25 (EKS 1.25)

| Removed API | Replacement |
|---|---|
| `batch/v1beta1 CronJob` | `batch/v1 CronJob` (no schema change) |
| `policy/v1beta1 PodSecurityPolicy` | Pod Security Admission (PSA) — namespace labels |
| `autoscaling/v2beta1 HorizontalPodAutoscaler` | `autoscaling/v2 HorizontalPodAutoscaler` (schema change for metrics) |
| `autoscaling/v2beta2 HorizontalPodAutoscaler` | `autoscaling/v2 HorizontalPodAutoscaler` (same as above) |
| `storage.k8s.io/v1beta1 CSIStorageCapacity` | `storage.k8s.io/v1 CSIStorageCapacity` |
| `storage.k8s.io/v1beta1 VolumeAttachment` | `storage.k8s.io/v1 VolumeAttachment` (deprecated since 1.22) |
| `node.k8s.io/v1beta1 RuntimeClass` | `node.k8s.io/v1 RuntimeClass` |

### Removed in Kubernetes 1.29 (EKS 1.29)

| Removed API | Replacement |
|---|---|
| `flowcontrol.apiserver.k8s.io/v1beta1 FlowSchema` | `flowcontrol.apiserver.k8s.io/v1 FlowSchema` |
| `flowcontrol.apiserver.k8s.io/v1beta1 PriorityLevelConfiguration` | `flowcontrol.apiserver.k8s.io/v1 PriorityLevelConfiguration` |

### Removed in Kubernetes 1.32 (EKS 1.32)

| Removed API | Replacement |
|---|---|
| `storage.k8s.io/v1beta1 CSIStorageCapacity` (already gone in 1.27) | `storage.k8s.io/v1 CSIStorageCapacity` |
| Various beta feature gates (not API removals) | Stable features only |

## Detecting deprecated APIs

### kubent (kubernetes-deprecation)

```bash
# Install: see https://github.com/doitintl/kube-deprecation

# Run against the cluster (uses kubeconfig context)
kubent

# Filter by target version
kubent --target-version 1.29

# Output as JSON for CI integration
kubent --output json
```

### kubectl convert

```bash
# Convert a manifest to the new API version
kubectl convert --output-version networking.k8s.io/v1 -f ingress-old.yaml | kubectl apply -f -

# kubectl convert is a plugin — install via:
kubectl krew install convert
```

### Manual scan via kubectl

```bash
# Find Ingresses on deprecated APIs
kubectl get ingresses --all-namespaces -o json | \
  jq -r '.items[] | select(.apiVersion | test("extensions/v1beta1|networking.k8s.io/v1beta1")) | "\(.metadata.namespace)/\(.metadata.name) \(.apiVersion)"'

# Find CronJobs on deprecated API
kubectl get cronjobs --all-namespaces -o json | \
  jq -r '.items[] | select(.apiVersion == "batch/v1beta1") | "\(.metadata.namespace)/\(.metadata.name)"'

# Find PodSecurityPolicies
kubectl get psp --all-namespaces

# Find HorizontalPodAutoscalers on deprecated APIs
kubectl get hpa --all-namespaces -o json | \
  jq -r '.items[] | select(.apiVersion | test("autoscaling/v2beta1|autoscaling/v2beta2")) | "\(.metadata.namespace)/\(.metadata.name) \(.apiVersion)"'
```

## Bridge-version selection strategy

When upgrading the cluster from N to N+1, choose add-on versions that
support BOTH N and N+1. The bridge version is the highest version
appearing in BOTH the N and N+1 compatibility lists.

**Example for VPC-CNI on cluster 1.28 -> 1.29:**

```bash
# Versions compatible with 1.28
aws eks describe-addon-versions --kubernetes-version 1.28 --addon-name vpc-cni \
  --query 'addons[].addonVersions[].addonVersion' --output text | tr '\t' '\n'

# Versions compatible with 1.29
aws eks describe-addon-versions --kubernetes-version 1.29 --addon-name vpc-cni \
  --query 'addons[].addonVersions[].addonVersion' --output text | tr '\t' '\n'

# The bridge version is in BOTH lists. Choose the highest.
# Then upgrade BEFORE the control plane upgrade:
aws eks update-addon --cluster-name <cluster> --addon-name vpc-cni \
  --addon-version <bridge-version> --resolve-conflicts PRESERVE
```

After the control plane reaches N+1, upgrade again to the LATEST N+1
version (which may not be N-compatible).

## Upgrade ordering matrix

For each upgrade scenario, follow this ordering:

| Cluster state | Order |
|---|---|
| Standard managed node group cluster | 1. Add-ons (bridge) -> 2. Scan APIs -> 3. Control plane -> 4. Add-ons (latest) -> 5. Node groups -> 6. Verify |
| Fargate-only cluster | 1. Add-ons (bridge) -> 2. Scan APIs -> 3. Control plane -> 4. Add-ons (latest) -> 5. Verify (Fargate auto-restarts) |
| EKS Auto Mode cluster | 1. Add-ons (bridge) -> 2. Scan APIs -> 3. Control plane -> 4. Add-ons (latest) -> 5. Verify (Auto Mode handles nodes) |
| Self-managed nodes | 1. Add-ons (bridge) -> 2. Scan APIs -> 3. Control plane -> 4. Add-ons (latest) -> 5. Drain and replace nodes one at a time -> 6. Verify |
| Hybrid nodes attached | 1. Add-ons (bridge) -> 2. Scan APIs -> 3. Control plane -> 4. Add-ons (latest) -> 5. Upgrade hybrid node kubelets on-prem -> 6. Verify |
