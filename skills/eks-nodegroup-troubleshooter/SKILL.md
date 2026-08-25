---
name: eks-nodegroup-troubleshooter
description: 'Diagnoses Amazon EKS managed node group issues through a node-state- driven diagnostic tree: nodes stuck NotReady (kubelet errors, container runtime crash, AMI version mismatch), taints blocking pod placement, ASG launch failures (InsufficientInstanceCapacity, launch template misconfig), VPC CNI IP exhaustion (warm ENI pool, prefix delegation, subnet CIDR too small), node group scaling failures, pod scheduling failures (insufficient CPU/memory), kubelet pressure (DiskPressure, MemoryPressure, PIDPressure), container runtime issues (containerd vs dockerd), node IAM role missing permissions (ECR pull, SSM, CloudWatch), security group misconfiguration, ECR image pull from worker nodes, and custom AMI bootstrap script errors. Combines AWS API (describe-nodegroup, describe-auto-scaling-groups) with kubectl (get nodes, describe node, get pods) to a verified root cause. Emits ROOT_CAUSE_IDENTIFIED or INSUFFICIENT_DATA.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline diagnosis works on supplied kubectl get/describe output and AWS CLI JSON. Live-cluster diagnosis uses aws eks describe-nodegroup, describe-cluster, aws autoscaling describe-auto-scaling-groups, aws ec2 describe-subnets / describe-security-groups, kubectl get nodes / describe node / get pods / describe pod / get events / top nodes (AWS CLI v2, kubectl v1.27+, SSO or key-based credentials, kubeconfig...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Compute
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
  when_to_use: Diagnosing why EKS managed node group nodes are NotReady, fail to join the cluster, cannot schedule pods due to taints or resource pressure, experience VPC CNI IP exhaustion, fail ASG launches, have AMI version mismatch with the control plane, have missing IAM permissions for ECR or SSM, encounter container runtime errors, or fail scaling operations (cluster autoscaler / Karpenter).
  when_not_to_use: Application-level pod crash debugging (use eks-pod-troubleshooter), EKS control plane / API server issues (use eks-cluster-auditor), EKS add-on installation or version issues (use eks-add-on-deployer), EKS upgrade orchestration (use eks-upgrade-operator), or steady-state node group cost optimization (use eks-cost-optimizer).
  activation_triggers: EKS nodes NotReady, EKS node group failed, EKS node not joining cluster, EKS VPC CNI IP exhaustion, EKS NoSchedule taint, EKS ASG launch failure, EKS InsufficientInstanceCapacity, EKS AMI version mismatch, EKS node IAM role, EKS ECR image pull, EKS security group, EKS kubelet error, EKS container runtime, EKS DiskPressure, EKS cluster autoscaler, EKS Karpenter, EKS custom AMI bootstrap, EKS node group scaling
  invocation_schema: 'Input: either (a) a symptom description (nodes NotReady, pods stuck Pending, scaling failures, error strings from kubectl or AWS Console) optionally paired with the cluster name, node group name, and kubectl output, OR (b) a cluster + node group name for live-cluster diagnosis. Output: a deterministic TARGET/VERDICT/REASON/ROOT_CAUSE/EVIDENCE/ REMEDIATION block where VERDICT is ROOT_CAUSE_IDENTIFIED or INSUFFICIENT_DATA, and ROOT_CAUSE names the specific failure category.'
  invocation_example: '# Minimal valid input (offline symptom classification): Symptom: "3 of 5 nodes in the EKS managed node group are NotReady after an AMI upgrade. Pods are stuck Pending with FailedScheduling." ClusterName: prod-cluster NodeGroupName: prod-ng-1 ClusterKubernetesVersion: "1.30" NodeGroupAmiVersion: "1.29.3-20240807" NodeStatus: 3 NotReady, 2 Ready'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: EKS, node group, managed node group, nodes NotReady, kubelet, container runtime, containerd, VPC CNI, IP exhaustion, warm IP pool, prefix delegation, taints, ASG launch failure, InsufficientInstanceCapacity, AMI version, node IAM role, ECR pull, security group, DiskPressure, cluster autoscaler, Karpenter, bootstrap script, custom AMI
  tags: eks, kubernetes, compute, troubleshoot, nodegroup, vpc-cni, asg, kubelet
---

# EKS NodeGroup Troubleshooter

## Quick start

- **Node `Ready` condition drives the first probe.** `kubectl get nodes`
  shows `Ready` vs `NotReady`. A `NotReady` node with conditions
  (`DiskPressure`, `MemoryPressure`, `PIDPressure`, `NetworkUnavailable`)
  narrows the cause immediately.
- **VPC CNI IP exhaustion is the #1 cause of pods stuck Pending.** The
  VPC CNI assigns secondary ENI IPs to pods. When the subnet runs out of
  free IPs, pods stay `Pending` with `FailedScheduling: insufficient IP
  addresses`. Check `kubectl describe node` for IP allocation and
  subnet `AvailableIpAddressCount`.
- **AMI K8s version MUST match the control plane version.** A node group
  running AMI `1.29` on a cluster at `1.30` produces kubelet errors and
  nodes that join but are immediately `NotReady`.
- **Node IAM role requires specific permissions.** The node role needs
  `AmazonEKSWorkerNodePolicy`, `AmazonEC2ContainerRegistryReadOnly` (for
  ECR pull), and `AmazonEKS_CNI_Policy` (for VPC CNI via IRSA). Missing
  ECR permissions produce `ImagePullBackOff` on every pod.
- **Custom AMI bootstrap failures are the most silent.** A custom AMI
  with a misconfigured `kubelet` or wrong `--apiserver-endpoint`
  produces instances that launch but never register with the API server.

## Quick reference — symptom-to-cause navigation table

| Symptom | Most likely ROOT_CAUSE | First probe |
|---|---|---|
| Nodes `NotReady`, no conditions | KUBELET_ERROR / CONTAINER_RUNTIME | `describe node`, kubelet logs |
| Nodes `NotReady`, `DiskPressure` / `MemoryPressure` | NODE_PRESSURE | `describe node` conditions, `top nodes` |
| Nodes `NotReady`, `NetworkUnavailable` | VPC_CNI_PLUGIN | `aws-node` DaemonSet, VPC CNI logs |
| Nodes never appear in `kubectl get nodes` | CUSTOM_AMI_BOOTSTRAP / ASG_LAUNCH_FAILURE | ASG activity, user-data, console output |
| Pods `Pending`, `insufficient IP` | VPC_CNI_IP_EXHAUSTION | `describe node` IP alloc, subnet IPs |
| Pods `Pending`, `insufficient cpu/memory` | SCHEDULING_INSUFFICIENT_RESOURCES | `top nodes`, pod requests vs allocatable |
| Pods `Pending`, `node(s) had taints` | TAINT_SCHEDULING | `describe node` taints, pod tolerations |
| Pods `ImagePullBackOff` | NODE_IAM_ROLE_ECR / ECR_ENDPOINT | Node IAM role policies, VPC endpoints |
| ASG `InsufficientInstanceCapacity` | INSTANCE_CAPACITY | ASG activity, different instance type/AZ |
| Node group `CREATE_FAILED` / `UPDATE_FAILED` | NODEGROUP_VERSION_MISMATCH / SG_MISCONFIG | `describe-nodegroup`, cluster SG, node SG |
| Scaling fails, no nodes added | SCALING_CONFIG | Autoscaler/Karpenter logs, ASG min/max |

## STRICT output contract

```text
TARGET: <cluster-name / nodegroup-name>
VERDICT: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
REASON: <1-2 sentences naming the observed state and ROOT_CAUSE>
ROOT_CAUSE: <VPC_CNI_IP_EXHAUSTION | VPC_CNI_PLUGIN |
  KUBELET_ERROR | CONTAINER_RUNTIME | NODE_PRESSURE |
  NODEGROUP_VERSION_MISMATCH | ASG_LAUNCH_FAILURE |
  INSTANCE_CAPACITY | TAINT_SCHEDULING |
  SCHEDULING_INSUFFICIENT_RESOURCES | NODE_IAM_ROLE_ECR |
  NODE_IAM_ROLE_MISSING | SG_MISCONFIG | ECR_ENDPOINT |
  CUSTOM_AMI_BOOTSTRAP | SCALING_CONFIG | UNKNOWN>
EVIDENCE:
  - Symptom: <observed node/pod state or error string>
  - Failing probe: <command and output that confirms the cause>
  - Passing probes: <categories ruled out>
REMEDIATION:
  1. <specific action with CLI command or kubectl>
  2. <verification command after the fix>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <nodegroup> in <cluster>.
  Proceed? (yes/no)"
```

## NEVER

- **NEVER** declare `ROOT_CAUSE_IDENTIFIED` without a failing probe that
  matches the symptom. A node in `NotReady` is a symptom, not a root
  cause; read the node conditions, kubelet logs, and ASG activity before
  naming the category.

- **NEVER** assume VPC CNI IP exhaustion is caused by the subnet CIDR
  alone. The VPC CNI's warm pool (`WARM_ENI_TARGET`, `WARM_IP_TARGET`,
  `WARM_PREFIX_TARGET`) controls how many IPs are pre-allocated per
  node. A subnet with available IPs can still show exhaustion if every
  node's warm pool consumes IPs faster than the scheduler places pods.

- **NEVER** confuse the node IAM role with the VPC CNI IRSA role. The
  **node IAM role** (`nodeRole`) is assumed by the EC2 instance and
  grants ECR pull, SSM, and CloudWatch permissions. The **VPC CNI role**
  (`AmazonEKS_CNI_Policy`) is used by the `aws-node` DaemonSet via IRSA
  for ENI/IP management. An `ImagePullBackOff` is the node role; a VPC
  CNI failure to allocate ENIs is the IRSA role.

- **NEVER** assume an AMI version mismatch produces an obvious error. A
  node group AMI behind the control plane version produces nodes that
  join but are immediately `NotReady`. Always verify `amiVersion` against
  `cluster.kubernetesVersion`.

- **NEVER** recommend changing the instance type without checking ASG
  activity for `InsufficientInstanceCapacity`. This AWS-side capacity
  issue is temporary and AZ-specific; the correct fix is to add
  secondary instance types or launch in a different AZ.

- **NEVER** assume a custom AMI node will register with the cluster
  automatically. The `bootstrap.sh` script must be correctly configured
  with `--apiserver-endpoint`, `--b64-cluster-ca`. A missing flag
  produces instances that launch but never appear in `kubectl get nodes`.

## Expert heuristic

> **VPC CNI warm IP pool determines pod IP allocation cadence.** Key
> `aws-node` env vars:
> - `WARM_ENI_TARGET` (default 1): pre-allocate IPs for one full ENI.
> - `WARM_IP_TARGET`: pre-allocate exactly N free IPs.
> - `WARM_PREFIX_TARGET`: pre-allocate a /28 prefix (16 IPs per
>   delegation; requires prefix delegation mode).
>
> **Node group AMI K8s version MUST align with the control plane.** EKS
> supports skew of at most one minor version (kubelet ≤ API server + 1).
> A node group AMI behind the control plane produces NotReady nodes.
>
> **ASG capacity is the scaling safety net.** For cluster autoscaler /
> Karpenter, the ASG must have headroom (`minSize < maxSize`). If
> `maxSize == desiredCapacity`, scaling fails silently — the autoscaler
> logs "no nodes can be added" but the node group appears healthy.

## Configuration dependency graph

```
                    EKS Cluster
                   (kubernetesVersion,
                    endpoint, CA cert,
                    vpcConfig)
                        │
         ┌──────────────┼──────────────────┐
         ▼              ▼                  ▼
    managed node    VPC CNI            cluster autoscaler /
    group           (aws-node          Karpenter
    (amiType,       DaemonSet,            (scales ASG or
     instanceTypes, manages ENIs          provisions nodes)
     subnets,       and pod IPs;              │
     nodeRole,      needs IRSA role           ▼
     scalingConfig, with CNI policy)      ASG
     SGs)                │               (launch template,
         │                ▼                minSize, maxSize,
         ▼          node subnets           desiredCapacity)
    launch template  (AvailableIpAddr         │
    (user-data,      Count → IP pool;         ▼
     bootstrap.sh)   ENI limits per       EC2 instances
         │            instance type)       (kubelet, containerd,
         ▼                                node IAM role)
    node IAM role                            │
    (ECR pull, SSM,                          ▼
     CloudWatch)                        ECR repository
                                        (node role needs
                                         ecr:BatchGetImage)
```

## Mindset

A failing EKS node group is usually an infrastructure-layer issue, not
a Kubernetes configuration bug. The broken thing is VPC CNI IP
allocation, AMI version alignment, the node IAM role permissions, the
ASG launch template / capacity, or the VPC networking. Treat the
Kubernetes manifests as innocent until the node infrastructure, IAM,
and networking layers are proven correct.

## Pre-flight: gather-info gate

```bash
# 1. Node group details (status, amiType, version, scalingConfig, health)
aws eks describe-nodegroup \
  --cluster-name <cluster> --nodegroup-name <ng> --output json

# 2. Cluster details (kubernetesVersion, vpcConfig)
aws eks describe-cluster --name <cluster> --output json

# 3. Node states and conditions
kubectl get nodes -o wide
kubectl describe node <node> | grep -A30 Conditions
kubectl describe node <node> | grep -A10 Allocatable

# 4. Pod states on affected nodes
kubectl get pods --all-namespaces --field-selector spec.nodeName=<node>

# 5. ASG activity (launch failures, capacity)
aws autoscaling describe-scaling-activities \
  --auto-scaling-group-name <asg-name> --max-records 5 --output json

# 6. Recent cluster events
kubectl get events --sort-by='.lastTimestamp' | tail -20
```

### Node-state short-circuit

| `kubectl get nodes` | Effect |
|---|---|
| All `Ready` | Nodes healthy; if pods fail, check pod-level (route to eks-pod-troubleshooter). |
| Some `NotReady` | Entry point. Read conditions. |
| Node count < `desiredCapacity` | Nodes not launching or not registering. Check ASG + user-data. |
| Node count = 0 | Node group failed to create. Check `describe-nodegroup` health. |

If input is malformed (missing cluster/nodegroup name), emit:

```text
TARGET: <cluster or unknown> / <nodegroup or unknown>
VERDICT: INSUFFICIENT_DATA
REASON: Input is missing required context.
ROOT_CAUSE: UNKNOWN
EVIDENCE:
  - Missing: <list specific missing fields>
REMEDIATION: Re-prompt for cluster name, node group name, symptom, region.
```

## Process — Diagnostic decision tree

### Step 1: Nodes NotReady — kubelet and container runtime

```bash
kubectl describe node <node> | grep -A30 Conditions
```

| Condition | ROOT_CAUSE |
|---|---|
| `Ready: False`, `KubeletNotReady` | KUBELET_ERROR |
| `Ready: Unknown` | KUBELET_ERROR — kubelet not reporting |
| `DiskPressure: True` | NODE_PRESSURE |
| `MemoryPressure: True` | NODE_PRESSURE |
| `PIDPressure: True` | NODE_PRESSURE |
| `NetworkUnavailable: True` | VPC_CNI_PLUGIN |

For `KUBELET_ERROR`, check kubelet logs via SSM:

```bash
aws ssm start-session --target <instance-id> \
  --document-name AWS-StartShell
sudo journalctl -u kubelet --no-pager | tail -50
```

| Kubelet log | ROOT_CAUSE |
|---|---|
| `Container runtime not ready` | CONTAINER_RUNTIME — containerd crashed |
| `failed to get node info: connection refused` | KUBELET_ERROR — API server unreachable |
| `curl: (7) Failed to connect ... port 443` | SG_MISCONFIG — node SG blocks API server |

### Step 2: VPC CNI IP exhaustion

Symptom: pods `Pending` with `FailedScheduling: insufficient IP`.

```bash
# Subnet available IPs
aws ec2 describe-subnets --subnet-ids <subnet-1> <subnet-2> --output json | \
  jq '.Subnets[] | {SubnetId, AvailableIpAddressCount, CidrBlock}'

# VPC CNI warm pool config
kubectl get ds aws-node -n kube-system -o jsonpath='{.spec.template.spec.containers[0].env[*]}' | jq -r '.[] | select(.name | startswith("WARM")) | "\(.name)=\(.value)"'
```

| Finding | ROOT_CAUSE |
|---|---|
| Subnet `AvailableIpAddressCount` < 10 | VPC_CNI_IP_EXHAUSTION — subnet too small |
| `WARM_ENI_TARGET` high (e.g., 3) | VPC_CNI_IP_EXHAUSTION — warm pool too aggressive |
| Nodes at max pods, subnet has IPs | VPC_CNI_IP_EXHAUSTION — per-node ENI limit |

**Remediation:** widen subnets (new ones), reduce `WARM_ENI_TARGET`, or
enable prefix delegation (`ENABLE_PREFIX_DELEGATION=true`).

### Step 3: VPC CNI plugin errors

Symptom: nodes `NotReady` with `NetworkUnavailable: True`.

```bash
kubectl get ds aws-node -n kube-system
kubectl get sa aws-node -n kube-system \
  -o jsonpath='{.metadata.annotations.eks\.amazonaws\.com/role-arn}'
```

Verify the IRSA role has `AmazonEKS_CNI_Policy`:

```bash
aws iam simulate-principal-policy \
  --policy-source-arn <cni-role-arn> \
  --action-names ec2:AssignPrivateIpAddresses ec2:AttachNetworkInterface ec2:CreateNetworkInterface \
  --output json --profile <p>
```

`implicitDeny` → **ROOT_CAUSE_IDENTIFIED**, `VPC_CNI_PLUGIN`.

### Step 4: AMI version mismatch

```bash
aws eks describe-cluster --name <cluster> --output json | jq '.cluster.version'
aws eks describe-nodegroup --cluster-name <cluster> --nodegroup-name <ng> \
  --output json | jq '.nodegroup.{amiType, version}'
```

The node AMI version MUST match the cluster K8s version (at most one
minor skew). If mismatched → **ROOT_CAUSE_IDENTIFIED**,
`NODEGROUP_VERSION_MISMATCH`. Fix: `update-nodegroup-version --version
<target>`.

### Step 5: ASG launch failures

```bash
aws autoscaling describe-scaling-activities \
  --auto-scaling-group-name <asg-name> --max-records 5 --output json | \
  jq '.Activities[0:3] | .[] | {StatusCode, StatusMessage, Cause}'
```

| `StatusCode` | ROOT_CAUSE |
|---|---|
| `Failed: InsufficientInstanceCapacity` | INSTANCE_CAPACITY — try different type/AZ |
| `Failed: Instance became unhealthy` | CUSTOM_AMI_BOOTSTRAP — check console output |
| `Failed: Launch configuration not found` | ASG_LAUNCH_FAILURE — launch template deleted |

### Step 6: Custom AMI bootstrap errors

Symptom: EC2 instances launch but never appear in `kubectl get nodes`.

```bash
# Check user-data
aws ec2 describe-instance-attribute --instance-id <i-id> \
  --attribute userData --output text --query 'UserData.Value' | base64 --decode

# Check console output
aws ec2 get-console-output --instance-id <i-id> --output text | tail -80
```

| Error | ROOT_CAUSE |
|---|---|
| `--apiserver-endpoint not set` | CUSTOM_AMI_BOOTSTRAP — wrong endpoint in user-data |
| `certificate signed by unknown authority` | CUSTOM_AMI_BOOTSTRAP — wrong `--b64-cluster-ca` |
| `/bootstrap.sh: command not found` | CUSTOM_AMI_BOOTSTRAP — AMI missing EKS bootstrap script |

### Step 7: Taints preventing scheduling

Symptom: pods `Pending` with `node(s) had taints that the pod didn't
tolerate`.

```bash
kubectl describe node <node> | grep -A5 Taints
kubectl describe pod <pod> -n <ns> | grep -A5 Tolerations
```

Intentional taints (`dedicated=gpu:NoSchedule`) → add toleration.
Condition-based taints (`not-ready:NoSchedule`, `disk-pressure`) → fix
the underlying node issue. **ROOT_CAUSE_IDENTIFIED**, `TAINT_SCHEDULING`.

### Step 8: Pod scheduling — insufficient CPU/memory

```bash
kubectl describe node <node> | grep -A10 "Allocated resources"
kubectl top nodes
```

If every node is at capacity → **ROOT_CAUSE_IDENTIFIED**,
`SCHEDULING_INSUFFICIENT_RESOURCES`. Fix: scale the node group or reduce
pod resource requests.

### Step 9: Node IAM role — ECR pull

Symptom: pods `ImagePullBackOff` or `ErrImagePull`.

```bash
aws eks describe-nodegroup --cluster-name <cluster> --nodegroup-name <ng> \
  --output json | jq '.nodegroup.nodeRole'
ROLE_NAME=$(echo <node-role-arn> | cut -d/ -f2)
aws iam list-attached-role-policies --role-name <role-name> --output json
```

Node role MUST include `AmazonEC2ContainerRegistryReadOnly`.

```bash
aws iam simulate-principal-policy \
  --policy-source-arn <node-role-arn> \
  --action-names ecr:BatchGetImage ecr:GetDownloadUrlForLayer \
  --output json --profile <p>
```

`implicitDeny` → **ROOT_CAUSE_IDENTIFIED**, `NODE_IAM_ROLE_ECR`.

If the role is entirely wrong (missing `AmazonEKSWorkerNodePolicy`):
**ROOT_CAUSE_IDENTIFIED**, `NODE_IAM_ROLE_MISSING`.

### Step 10: Security group misconfiguration

```bash
aws eks describe-cluster --name <cluster> --output json | \
  jq '.cluster.resourcesVpcConfig.securityGroupIds'
aws ec2 describe-security-groups --group-ids <node-sg> <cluster-sg> \
  --output json | jq '.SecurityGroups[] | {GroupId, IpPermissions, IpPermissionsEgress}'
```

Check: node SG egress to cluster SG on 443; cluster SG ingress from
node SG on 443; node SG ingress from node SG for pod traffic.

If node SG blocks API server → **ROOT_CAUSE_IDENTIFIED**, `SG_MISCONFIG`.

### Step 11: Node group scaling failures

```bash
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names <asg-name> --output json | \
  jq '.AutoScalingGroups[0] | {MinSize, MaxSize, DesiredCapacity}'

# Autoscaler logs
kubectl logs -l app=cluster-autoscaler -n kube-system --tail=20
# Karpenter logs
kubectl logs -l app.kubernetes.io/name=karpenter -n karpenter --tail=20
```

| Finding | ROOT_CAUSE |
|---|---|
| `MaxSize == DesiredCapacity` | SCALING_CONFIG — raise maxSize |
| CA: "node group not eligible" | SCALING_CONFIG — CA config mismatch |
| Karpenter: "no capacity" | INSTANCE_CAPACITY — no matching NodePool |

### Step 12: Container runtime issues

EKS AMIs migrated from `dockerd` to `containerd` (K8s 1.24+). A custom
AMI still using `dockerd` fails on newer K8s.

```bash
sudo systemctl status containerd
sudo crictl --runtime-endpoint unix:///run/containerd/containerd.sock info
```

If containerd is down → **ROOT_CAUSE_IDENTIFIED**, `CONTAINER_RUNTIME`.

### Step 13: INSUFFICIENT_DATA

Emit when input lacks cluster/nodegroup name, a probe requires operator
input, or the symptom matches no navigation table row. List missing
inputs and next probe.

## Worked examples

### Worked example — VPC CNI IP exhaustion

```text
TARGET: prod-cluster / prod-ng-1
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: Pods stuck Pending with "FailedScheduling: 0/5 nodes available:
  insufficient IP addresses." Subnets subnet-private-a (3 IPs) and
  subnet-private-b (1 IP) are nearly exhausted. WARM_ENI_TARGET is 1
  (default), pre-allocating a full ENI's worth of IPs per node (Step 2).
ROOT_CAUSE: VPC_CNI_IP_EXHAUSTION
EVIDENCE:
  - Symptom: 12 pods Pending; all nodes Ready.
  - Probe: aws ec2 describe-subnets returns AvailableIpAddressCount: 3
    and 1 for the two subnets.
  - Probe: kubectl describe node shows 5 nodes at max pods (110), all
    ENI secondary IPs allocated.
  - Passing: nodes have available CPU/memory; nodes are Ready.
REMEDIATION:
  1. Create wider subnets and add to node group:
     aws eks update-nodegroup-config --cluster-name prod-cluster \
       --nodegroup-name prod-ng-1 \
       --subnets <new-subnet-1> <new-subnet-2> --profile <p>
  2. Alternatively, enable prefix delegation:
     kubectl set env ds aws-node -n kube-system \
       ENABLE_PREFIX_DELEGATION=true
  3. Verify: kubectl get pods --watch (Pending → Running).
CONFIRM: Before updating, emit and await:
  "CONFIRM: About to add subnets / enable prefix delegation on
   prod-ng-1. Proceed? (yes/no)"
```

### Worked example — Node IAM role missing ECR

```text
TARGET: prod-cluster / prod-ng-1
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: All pods on the new node group show ImagePullBackOff. The node
  IAM role (arn:aws:iam::111111111111:role/eks-prod-ng-1) lacks
  AmazonEC2ContainerRegistryReadOnly — only AmazonEKSWorkerNodePolicy is
  attached (Step 9).
ROOT_CAUSE: NODE_IAM_ROLE_ECR
EVIDENCE:
  - Symptom: every pod is ImagePullBackOff.
  - Probe: kubectl describe pod shows "pull access denied" for ECR.
  - Probe: aws iam list-attached-role-policies returns
    AmazonEKSWorkerNodePolicy but NOT
    AmazonEC2ContainerRegistryReadOnly.
  - Passing: ECR repo allows same-account access; image exists.
REMEDIATION:
  1. Attach the managed policy:
     aws iam attach-role-policy --role-name eks-prod-ng-1 \
       --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly
  2. Delete ImagePullBackOff pods to force re-pull.
  3. Verify pods transition to Running.
CONFIRM: Before attaching, emit and await:
  "CONFIRM: About to attach AmazonEC2ContainerRegistryReadOnly to
   eks-prod-ng-1. Proceed? (yes/no)"
```

### Worked example — INSUFFICIENT_DATA

```text
TARGET: unknown / unknown
VERDICT: INSUFFICIENT_DATA
REASON: Input is "EKS nodes not ready in prod" with no cluster name,
  node group name, or kubectl output.
ROOT_CAUSE: UNKNOWN
EVIDENCE:
  - Missing: cluster name, node group name, kubectl output, region
REMEDIATION:
  1. Run aws eks list-clusters and share the cluster name.
  2. Run aws eks list-nodegroups --cluster-name <cluster>.
  3. Run kubectl get nodes -o wide.
```

## Pre-flight safety checks

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`update-nodegroup-version`, `update-nodegroup-config`, `attach-role-
  policy`, `set env ds aws-node`), emit and await operator approval.
- **Read-only first.** Every probe is read-only.
- **Updating a node group version** triggers rolling node replacement.
  Plan outside traffic peaks.
- **Changing the node IAM role** affects all running nodes immediately
  via EC2 metadata role refresh.
- **Modifying VPC CNI env vars** restarts `aws-node` on every node;
  existing pods keep IPs but new pods wait for CNI restart.
- **Bulk remediation:** batch groups of at most 5 node groups.

## Remediation guidance

| ROOT_CAUSE | Specific fix |
|---|---|
| `VPC_CNI_IP_EXHAUSTION` | Create wider subnets; reduce `WARM_ENI_TARGET`; enable prefix delegation. |
| `VPC_CNI_PLUGIN` | Verify `aws-node` DaemonSet; check IRSA role has `AmazonEKS_CNI_Policy`. |
| `KUBELET_ERROR` | Check kubelet logs; fix API server connectivity; restart kubelet. |
| `CONTAINER_RUNTIME` | Start containerd; rebuild custom AMI with containerd for K8s 1.24+. |
| `NODE_PRESSURE` | Resize EBS volume; clean images/containers; raise node `diskSize`. |
| `NODEGROUP_VERSION_MISMATCH` | `update-nodegroup-version --version <target>`. |
| `ASG_LAUNCH_FAILURE` | Fix launch template; verify AMI exists. |
| `INSTANCE_CAPACITY` | Add secondary instance types; use Karpenter; try different AZ. |
| `TAINT_SCHEDULING` | Add toleration to pod spec; remove taint if unintentional. |
| `SCHEDULING_INSUFFICIENT_RESOURCES` | Scale node group; reduce pod requests; add nodes. |
| `NODE_IAM_ROLE_ECR` | Attach `AmazonEC2ContainerRegistryReadOnly`. |
| `NODE_IAM_ROLE_MISSING` | Attach `AmazonEKSWorkerNodePolicy` + `AmazonEC2ContainerRegistryReadOnly` + CNI policy. |
| `SG_MISCONFIG` | Node SG egress to cluster SG on 443; node SG ingress from node SG. |
| `ECR_ENDPOINT` | Create ECR interface VPC endpoints + S3 gateway endpoint. |
| `CUSTOM_AMI_BOOTSTRAP` | Fix user-data `bootstrap.sh` args; ensure AMI includes EKS bootstrap. |
| `SCALING_CONFIG` | Raise ASG `maxSize`; verify autoscaler/Karpenter config. |

## Domain

AWS CloudOps / EKS Managed Node Groups, Kubernetes Node Lifecycle
Diagnostics, VPC CNI Networking, ASG Capacity Management, Node IAM
Roles, and Container Runtime Configuration.

## AWS documentation

- EKS managed node groups — https://docs.aws.amazon.com/eks/latest/userguide/managed-node-groups.html
- EKS node IAM role — https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html
- EKS AMI versions — https://docs.aws.amazon.com/eks/latest/userguide/eks-linux-ami-versions.html
- VPC CNI — https://docs.aws.amazon.com/eks/latest/userguide/managing-vpc-cni.html
- VPC CNI prefix delegation — https://github.com/aws/amazon-vpc-cni-k8s#prefix-delegation
- EKS security groups — https://docs.aws.amazon.com/eks/latest/userguide/sec-group-reqs.html
- Cluster autoscaler — https://docs.aws.amazon.com/eks/latest/userguide/cluster-autoscaler.html
- Karpenter — https://karpenter.sh/
- EKS troubleshooting — https://docs.aws.amazon.com/eks/latest/userguide/troubleshooting.html
