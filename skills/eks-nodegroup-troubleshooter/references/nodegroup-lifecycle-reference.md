# EKS Managed Node Group Lifecycle Reference Guide

Supplementary reference for the EKS NodeGroup Troubleshooter skill.
Loaded on-demand when a diagnostic needs VPC CNI semantics, AMI version
matrices, ENI/IP limits, ASG health check behavior, or kubelet condition
details.

## VPC CNI IP allocation model

The VPC CNI (`amazon-vpc-cni-k8s`) assigns pod IPs from the node's
elastic network interfaces (ENIs). Each ENI has a primary IP and a set
of secondary IPs. The CNI attaches ENIs to the node and allocates
secondary IPs to pods.

### Per-instance-type ENI and IP limits

| Instance type | Max ENIs | IPs per ENI (incl. primary) | Max pods |
|---|---|---|---|
| t3.micro | 2 | 2 | 4 |
| t3.small | 3 | 4 | 11 |
| t3.medium | 3 | 6 | 17 |
| m5.large | 3 | 10 | 29 |
| m5.xlarge | 4 | 15 | 58 |
| m5.2xlarge | 4 | 15 | 58 |
| m5.4xlarge | 8 | 30 | 234 |
| c5.large | 3 | 10 | 29 |
| c5.xlarge | 4 | 15 | 58 |
| r5.large | 3 | 10 | 29 |
| r5.4xlarge | 8 | 30 | 234 |

Formula: `maxPods = (eni_count * (ips_per_eni - 1)) + 2`

### Warm pool env vars

| Env var | Default | Effect |
|---|---|---|
| `WARM_ENI_TARGET` | 1 | Pre-allocate IPs for N full ENIs per node |
| `WARM_IP_TARGET` | (unset) | Pre-allocate exactly N free IPs (overrides WARM_ENI_TARGET if set) |
| `WARM_PREFIX_TARGET` | (unset) | Pre-allocate N /28 prefixes (16 IPs each; requires ENABLE_PREFIX_DELEGATION) |
| `ENABLE_PREFIX_DELEGATION` | false | Use /28 prefix delegation instead of individual secondary IPs |

### Prefix delegation

When `ENABLE_PREFIX_DELEGATION=true`, the CNI attaches /28 prefixes
(16 IPs each) to each ENI secondary slot. This multiplies the pod
capacity per node significantly:

- m5.large: 3 ENIs * 1 primary + 9 secondary slots * 16 IPs = ~144 pods
- m5.xlarge: 4 ENIs * 1 primary + 14 secondary slots * 16 IPs = ~224 pods

Requirements:
- The subnet must have available prefixes (Amazon VPC CNI manages
  allocation; the subnet CIDR must be large enough).
- The VPC CNI version must be >= 1.9.0.
- Node maximum pods annotation (`eks.amazonaws.com/max-pods`) must be
  raised to match the higher limit.

## AMI version support matrix

EKS managed AMIs track Kubernetes minor versions. Always verify
`nodegroup.version` against `cluster.version`.

| Cluster K8s | Supported node AMI versions | Notes |
|---|---|---|
| 1.30 | 1.30.x, 1.29.x | One minor skew allowed |
| 1.29 | 1.29.x, 1.28.x | One minor skew allowed |
| 1.28 | 1.28.x, 1.27.x | One minor skew allowed |
| 1.27 | 1.27.x, 1.26.x | One minor skew allowed |

Running a node AMI two minor versions behind the control plane is NOT
supported and produces unpredictable kubelet errors.

### AMI types

| `amiType` | Description |
|---|---|
| `AL2_x86_64` | Amazon Linux 2, x86_64 |
| `AL2_x86_64_GPU` | Amazon Linux 2 with NVIDIA drivers |
| `AL2_ARM_64` | Amazon Linux 2, ARM64 (Graviton) |
| `CUSTOM_TEMPLATE` | User-provided launch template (custom AMI) |

## Node IAM role required policies

| Policy | Purpose |
|---|---|
| `AmazonEKSWorkerNodePolicy` | Base EKS worker permissions |
| `AmazonEC2ContainerRegistryReadOnly` | ECR image pull (`ecr:BatchGetImage`, `ecr:GetDownloadUrlForLayer`) |
| `AmazonEKS_CNI_Policy` | VPC CNI ENI management (attach to IRSA role, not node role — common confusion) |
| `AmazonSSMManagedInstanceCore` | SSM Session Manager access (for debugging) |
| `CloudWatchAgentServerPolicy` | CloudWatch agent for container insights |

**Critical distinction:** `AmazonEKS_CNI_Policy` should be attached to
the **IRSA role** (Kubernetes Service Account `aws-node`), NOT the node
IAM role. Attaching it to the node role works but is less secure (all
pods on the node inherit the ENI management permissions).

## Kubelet condition reference

| Condition | True means | Cause |
|---|---|---|
| `Ready` | Node is healthy and accepting pods | `False`/`Unknown` = problem |
| `DiskPressure` | Kubelet disk is low | Log accumulation, image storage, volume leaks |
| `MemoryPressure` | Node memory is low | Pod memory leak, too many pods, memory overcommit |
| `PIDPressure` | Too many processes | Process leak in a container, kernel thread leak |
| `NetworkUnavailable` | CNI not configured | VPC CNI not installed, crashed, or misconfigured |

### Eviction thresholds

Kubelet evicts pods when conditions persist:
- `memory.available < 100Mi` → evict best-effort, then burstable pods
- `nodefs.available < 10%` → evict pods to reclaim disk
- `nodefs.inodesFree < 5%` → evict pods to reclaim inodes
- `imagefs.available < 15%` → garbage-collect unused images

## ASG health check and replacement behavior

| Health check type | Grace period | Effect |
|---|---|---|
| EC2 (default) | 300 seconds | EC2 status checks fail → instance replaced |
| ELB | Configurable | Target group health fails → instance replaced |
| Custom | Configurable | CloudWatch alarm triggers replacement |

When an ASG replaces an instance:
1. New instance launched from launch template.
2. User-data `bootstrap.sh` runs (or `/etc/eks/bootstrap.sh` for managed AMIs).
3. Kubelet starts, connects to API server, registers the node.
4. If step 3 fails within the grace period → instance marked unhealthy → replaced.

This creates a launch-replace cycle for bootstrap errors.

## Security group requirements for EKS

| Traffic | Source → Destination | Port | Purpose |
|---|---|---|---|
| API server communication | Node SG → Cluster SG (or endpoint SG) | 443 | Kubelet to API server |
| API server to node | Cluster SG → Node SG | 10250 | API server to kubelet |
| Pod-to-pod (same node) | Node SG → Node SG | All | CNI inter-pod traffic |
| Node-to-node | Node SG → Node SG | All | Kube-proxy, metrics, health |
| ECR pull (if using VPC endpoint) | Node SG → ECR endpoint SG | 443 | Container image pull |
| Internet egress (if using NAT) | Node SG → 0.0.0.0/0 | 443 | Package install, external APIs |

The cluster security group is managed by EKS; the node security group
is created with the node group (or specified in the launch template).

## Cluster autoscaler vs Karpenter comparison

| Feature | Cluster Autoscaler | Karpenter |
|---|---|---|
| Scaling target | ASG (node groups) | Directly provisions EC2 |
| Instance selection | Fixed per node group | Dynamic via `instanceRequirements` |
| Consolidation | No (only scale-up/down) | Yes (consolidates underutilized nodes) |
| Spot support | Via ASG mixed instances | First-class (spot-to-on-demand fallback) |
| Config | `--nodes=<min>:<max>:<asg>` flag | `NodePool` / `NodeClaim` CRD |
| Logs | `kube-system/cluster-autoscaler` | `karpenter/karpenter` |
| When it fails silently | maxSize == desiredSize | No matching NodePool |

## Container runtime timeline (EKS)

| K8s version | Default runtime | Notes |
|---|---|---|
| 1.23 and below | dockerd | Docker container runtime |
| 1.24 | containerd | dockerd removed; containerd default |
| 1.25+ | containerd | Only containerd supported on managed AMIs |

Custom AMIs still using `dockerd` on K8s 1.24+ must migrate to
`containerd` or the kubelet reports `Container runtime not ready`.
