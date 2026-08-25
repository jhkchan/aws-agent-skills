---
name: eks-hybrid-node-deployer
description: 'Provisions Amazon EKS Hybrid Nodes with production defaults: hybrid node IAM role creation, activation code/ID for on-prem registration (NOT IAM access keys), connector agent (nodeadm or eksctl anywhere), pod identity for hybrid workloads, networking (direct VPN/Direct Connect or via Cloud Network), security group mapping, node group (remote vs managed), upgrade strategy for hybrid nodes, health monitoring via CloudWatch agent, SSM Session Manager for hybrid node access, capacity planning for on-prem k8s nodes, and node draining during on-prem maintenance. Emits a READY_TO_DEPLOY checklist with verification commands. Use when registering on-prem nodes to EKS, configuring hybrid node networking, setting up pod identity. Triggers: create eks hybrid nodes, register on-prem node to eks, eks hybrid node activation code, eks hybrid pod identity, eks hybrid networking direct connect, eks hybrid nodeadm, eks hybrid ssm session manager, eks hybrid node drain, eks hybrid cloudwatch monitoring, eks hybrid node upgrade.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with eks access, SSM, and IAM. Works with Terraform aws_eks_node_group / aws_eks_access_entry resources and eksctl anywhere / nodeadm for on-prem registration.'
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
  tags: aws, eks, hybrid-nodes, cloudops, deploy, compute, provisioning, on-prem, pod-identity, direct-connect, ssm
  dependencies: aws-orchestrator
  keywords: aws, eks, hybrid nodes, on-prem, activation code, pod identity, nodeadm, cloudops, deploy, provisioning, direct connect, ssm session manager, node drain, cloudwatch agent, upgrade strategy
  when_to_use: Invoke when the user wants to register on-premises servers as Amazon EKS hybrid nodes, configure hybrid node IAM roles, generate activation codes/IDs for on-prem registration, set up pod identity for hybrid workloads, configure networking (Direct Connect/VPN) for on-prem nodes to reach the EKS control plane, configure security group mapping, plan hybrid node upgrades, set up CloudWatch health monitoring, enable SSM Session Manager for hybrid node access, or plan node draining for on-prem maintenance. Do NOT invoke for standard EKS managed node groups (EC2-based), EKS Fargate, EKS Anywhere (self-managed control plane), or ECS.
---

# EKS Hybrid Node Deployer

An AWS CloudOps agent skill that provisions Amazon EKS Hybrid Nodes
with correct defaults. The skill walks the operator through hybrid
node IAM role creation, activation code/ID generation, connector agent
(nodeadm) deployment, pod identity for hybrid workloads, networking
(Direct Connect/VPN to EKS control plane), security group mapping,
upgrade strategy, health monitoring, SSM Session Manager access,
capacity planning, and node draining. It captures topology and
infrastructure decisions, explains why each default matters, and emits
a READY_TO_DEPLOY checklist with copy-pasteable verification commands.

## Activation keywords

create EKS hybrid nodes, register on-prem node to EKS, EKS hybrid node
activation code, EKS hybrid pod identity, EKS hybrid networking Direct
Connect, EKS hybrid nodeadm, EKS hybrid SSM Session Manager, EKS hybrid
node drain, EKS hybrid CloudWatch monitoring, EKS hybrid node upgrade.

## STRICT output contract

When this skill is invoked with an EKS hybrid node provisioning request
(register on-prem nodes, configure activation, set up pod identity,
configure networking, plan upgrades, enable monitoring, or a partial
configuration), the agent MUST respond with the READY_TO_DEPLOY
checklist defined in the "Output format" section using the literal
all-caps labels `EKS_HYBRID:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels
breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Hybrid node IAM role | Identity model |
| Step 2 — Activation code/ID (NOT access keys) | Registration model |
| Step 3 — Connector agent (nodeadm) | Node bootstrap |
| Step 4 — Pod identity for hybrid workloads | Workload auth |
| Step 5 — Networking (Direct Connect/VPN) | Control plane connectivity |
| Step 6 — Security group mapping | Network security |
| Step 7 — Node group (remote vs managed) | Node management |
| Step 8 — Upgrade strategy | Lifecycle |
| Step 9 — Health monitoring (CloudWatch agent) | Observability |
| Step 10 — SSM Session Manager access | Node access |
| Step 11 — Capacity planning | Resource sizing |
| Step 12 — Node draining (on-prem maintenance) | Maintenance |
| Step 13 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/networking-and-registration.md | Networking + registration detail |
| references/pod-identity-and-access.md | Pod identity + SSM detail |

## Mindset

**One-line takeaway:** EKS Hybrid Nodes let you register on-premises
servers as worker nodes in an EKS cluster. Hybrid nodes connect via an
ACTIVATION CODE (not IAM access keys). Pod identity works differently
for hybrid nodes than for managed node groups. On-prem nodes MUST have
a network path to the EKS control plane API.

Three misconceptions dominate EKS Hybrid Nodes misdesign at provisioning
time:

- **"Hybrid nodes authenticate with IAM access keys."** They do NOT.
  Hybrid nodes register to the EKS cluster using an ACTIVATION CODE and
  ACTIVATION ID generated by the EKS API. IAM access keys are NOT used
  for node-to-control-plane authentication. A baseline model may suggest
  creating access keys for the node role; this is incorrect — the
  activation code is the bootstrap credential.

- **"Pod identity works the same as managed node groups."** It does
  NOT. Pod identity (EKS Pod Identity) is available for hybrid nodes but
  the association and permission model differs. Hybrid nodes need the
  pod identity agent running on the node, and the node's IAM role must
  be configured differently. EC2 instance profiles do not apply to
  on-prem nodes.

- **"On-prem nodes just need internet access."** They do NOT. On-prem
  nodes MUST have a network path to the EKS control plane API endpoint.
  This requires Direct Connect, VPN, or VPC peering to reach the VPC
  hosting the EKS cluster. Without a proper network path, nodes cannot
  register or communicate with the control plane.

## Configuration dependency graph (novel heuristic)

EKS Hybrid Nodes configurations are NOT independent. The IAM role must
exist before the activation code. The activation code is the bootstrap
credential. The network path must exist before nodes can register. Pod
identity requires the pod identity agent. Use this graph to sequence
provisioning.

| Configuration | Hard dependencies | Silent failure | Enables downstream |
|---|---|---|---|
| Hybrid node IAM role | EKS cluster exists | role trust policy must allow EKS; differs from managed NG role | activation code generation |
| Activation code/ID | hybrid node IAM role exists | code expires after TTL; single-use per node or multi-use per group | node registration via nodeadm |
| Connector agent (nodeadm) | activation code/ID obtained; node OS supported | nodeadm configures kubelet; kubelet connects to control plane | kubelet running + node registered |
| Network path (DX/VPN) | EKS API endpoint reachable from on-prem | nodes CANNOT register without network path; latency affects heartbeats | node-to-control-plane communication |
| Pod identity agent | node registered; pod identity association configured | agent must run on hybrid nodes; NO IMDS on-prem | pod-to-AWS-permission mapping |
| Security group mapping | network path exists | hybrid nodes do NOT use VPC SGs; on-prem firewall rules apply | network security |
| CloudWatch agent | node registered; IAM role has CW perms | agent must be installed per node; metrics NOT automatic | health monitoring |
| SSM agent | node registered; IAM role has SSM perms | SSM enables Session Manager; hybrid nodes = managed instances | remote access without SSH |

**The activation-code-not-access-keys row is the one a baseline model
misses.** The activation code is THE bootstrap mechanism. Without it,
nodes cannot register. The network path is equally critical — without
it, the activation code is useless because the node cannot reach the
control plane.

**Cross-dependency gotchas:**
- The activation code is generated per-cluster and tied to a specific
  IAM role. It is NOT the same as IAM access keys.
- Pod identity on hybrid nodes requires the pod identity agent on the
  node AND the association configured in the EKS API. Missing either
  results in permission denied.
- The network path from on-prem to the EKS control plane must be
  stable. High latency or intermittent connectivity causes nodes to be
  marked NotReady.
- SSM Session Manager requires the SSM agent on the on-prem node and
  the node's IAM role having SSM permissions. This is the recommended
  remote access method — NOT SSH through a bastion.
- CloudWatch agent must be installed on each on-prem node individually.
  Hybrid nodes do NOT get CloudWatch metrics automatically.

## Expert heuristic: activation code is the bootstrap credential

A baseline model says "create an IAM access key for the node role."
The correct heuristic recognizes that hybrid nodes use an activation
code generated by the EKS API.

```text
EKS Cluster (control plane in AWS)
  │
  ├── Step 1: Create hybrid node IAM role
  │     └── Trust policy for EKS + permissions (ECR, SSM, CloudWatch)
  │
  ├── Step 2: Generate activation code/ID
  │     └── aws eks create-access-entry --type HYBRID_LINUX
  │     └── Returns: activationId + activationCode
  │
  ├── Step 3: On on-prem node, run nodeadm
  │     └── nodeadm uses activationId + activationCode to register
  │     └── kubelet connects to EKS control plane using the activation
  │     └── After registration, node gets client cert for ongoing auth
  │
  └── Step 4: Node appears in kubectl get nodes
        └── Status: Ready (if network path + kubelet healthy)
```

**Key implication:** never create IAM access keys for hybrid node
registration. The activation code is the only bootstrap mechanism. Once
registered, the node uses client certificates for ongoing authentication
(renewed automatically by kubelet).

## Expert heuristic: pod identity on hybrid nodes

A baseline model assumes pod identity works the same as managed node
groups. The correct heuristic recognizes the differences.

```text
Managed Node Group (EC2):
  ├── EKS Pod Identity association maps SA → IAM role
  ├── Pod identity agent uses IMDS from EC2
  └── EC2 instance profile provides baseline node permissions

Hybrid Node (on-prem):
  ├── EKS Pod Identity association maps SA → IAM role (SAME API)
  ├── Pod identity agent must run on-prem (NO IMDS available)
  │     └── Agent obtains credentials via activation-based auth
  ├── NO EC2 instance profile (on-prem is not EC2)
  └── Node IAM role is referenced by activation code registration
```

**Key implication:** the pod identity agent must be explicitly installed
and configured on hybrid nodes. The node's IAM role (created in Step 1)
is what the agent uses to obtain credentials.

## Expert heuristic: network path is non-negotiable

A baseline model says "nodes just need internet." The correct heuristic
recognizes that nodes MUST reach the EKS control plane API.

```text
On-prem Node (10.0.1.5)
  │
  ├── Must reach: EKS API endpoint (TCP 443)
  │
  ├── Network path options:
  │     ├── Direct Connect (private VIF → VPC)     ← RECOMMENDED
  │     ├── Site-to-Site VPN (IPsec → VPC)          ← Acceptable
  │     └── Public internet (EKS public endpoint)   ← NOT recommended
  │
  └── Latency requirement:
        ├── kubelet heartbeat: every 10s (default)
        └── If latency > grace period (40s) → node → NotReady
```

**Key implication:** verify the network path BEFORE registering nodes.
A node that registers then loses connectivity will be marked NotReady
within 40 seconds (default kubelet grace period).

## Prerequisites (verify before provisioning)

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| EKS cluster exists (running) | Hybrid nodes register to an existing cluster | `aws eks describe-cluster --name <name>` |
| Hybrid node IAM role | Activation code references this role | `aws iam get-role --role-name <role>` |
| Network path to control plane | Nodes MUST reach the EKS API endpoint | Test: `curl -k https://<eks-endpoint>/healthz` from on-prem |
| On-prem node OS supported | nodeadm supports Amazon Linux, Ubuntu, RedHat | Check OS on on-prem node |
| Container runtime installed | kubelet needs containerd | `systemctl status containerd` on on-prem |
| Direct Connect / VPN configured | Private network path to VPC | `aws directconnect describe-connections` |
| SSM agent (for Session Manager) | Enables remote access without SSH | Check SSM agent on on-prem node |
| Capacity (CPU/RAM/Storage) | On-prem nodes must meet k8s minimum | Verify on-prem node specs |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Hybrid node IAM role

The hybrid node IAM role is the identity assumed by on-prem nodes when
communicating with the EKS control plane and AWS services. This role is
referenced by the activation code.

```bash
# Create the hybrid node IAM role
aws iam create-role \
  --role-name EKSHybridNodeRole \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ec2.amazonaws.com"},"Action":"sts:AssumeRole"}]}'

# Attach required policies
aws iam attach-role-policy --role-name EKSHybridNodeRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly
aws iam attach-role-policy --role-name EKSHybridNodeRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
aws iam attach-role-policy --role-name EKSHybridNodeRole \
  --policy-arn arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy
```

**Critical:** this role is NOT the same as a managed node group role.
Hybrid nodes do NOT use an EC2 instance profile (they are not EC2
instances). The role is referenced by the activation code.

## Step 2 — Activation code/ID (NOT access keys)

The activation code is the bootstrap credential for hybrid node
registration. Generated by the EKS API, tied to the hybrid node IAM
role.

```bash
# Create an access entry for the hybrid node role
aws eks create-access-entry \
  --cluster-name my-cluster \
  --principal-arn arn:aws:iam::123456789012:role/EKSHybridNodeRole \
  --type HYBRID_LINUX
```

**The activation code is:** generated per-cluster, tied to a specific
IAM role; used by nodeadm to bootstrap kubelet; single-use per node or
multi-use per group; expires after configurable TTL (default 7 days).

**NEVER use IAM access keys** for hybrid node registration.

## Step 3 — Connector agent (nodeadm)

The connector agent (nodeadm) is installed on each on-prem node. It
uses the activation code to register with the EKS cluster.

```bash
# On the on-prem node (NOT an AWS CLI command):
# Download and install nodeadm
curl -O https://s3.us-east-1.amazonaws.com/amazon-eks/hybrid-node-tools/nodeadm
chmod +x nodeadm

# Configure and start
./nodeadm init \
  --cluster-name my-cluster \
  --cluster-endpoint https://XXXX.gr7.us-east-1.eks.amazonaws.com \
  --cluster-ca <base64-ca> \
  --activation-id <activation-id> \
  --activation-code <activation-code> \
  --node-role arn:aws:iam::123456789012:role/EKSHybridNodeRole

./nodeadm up

# Verify registration (from a machine with kubectl)
kubectl get nodes --show-labels | grep hybrid
# Expected: node appears with Ready status
```

**Common failure:** node shows NotReady. Check: (1) network path to
control plane, (2) activation code not expired, (3) kubelet running
(`systemctl status kubelet`), (4) container runtime running.

## Step 4 — Pod identity for hybrid workloads

Pod identity maps Kubernetes service accounts to IAM roles. On hybrid
nodes, the pod identity agent must run on the node.

**Step 1: Install the pod identity agent on the on-prem node:**

```bash
./nodeadm enable-pod-identity \
  --role arn:aws:iam::123456789012:role/EKSHybridNodeRole
```

**Step 2: Create a pod identity association in the EKS cluster:**

```bash
aws eks create-pod-identity-association \
  --cluster-name my-cluster \
  --namespace production \
  --service-account my-app-sa \
  --role-arn arn:aws:iam::123456789012:role/MyAppPodRole
```

**Step 3: Deploy workload using the service account** with
`serviceAccountName: my-app-sa` and `nodeSelector:
eks.amazonaws.com/node-group: hybrid` to schedule on hybrid nodes.

**Key implication:** pod identity on hybrid nodes requires the agent
running on the node AND the association in the EKS API. Missing either
results in permission denied.

## Step 5 — Networking (Direct Connect/VPN to control plane)

On-prem nodes MUST have a network path to the EKS control plane API.

```bash
# Verify Direct Connect
aws directconnect describe-connections \
  --query 'connections[*].{Name:connectionName,State:connectionState}' \
  --output table

# Or verify Site-to-Site VPN
aws ec2 describe-vpn-connections \
  --query 'VpnConnections[*].{ID:VpnConnectionId,State:State}' \
  --output table

# Test connectivity from the on-prem node:
curl -k https://<eks-endpoint>/healthz   # Expected: ok (HTTP 200)
```

**Latency requirement:** kubelet heartbeats every 10s. If latency
exceeds the grace period (default 40s), nodes are marked NotReady. For
production, maintain latency under 100ms.

## Step 6 — Security group mapping

Hybrid nodes do NOT use VPC security groups (they are not in the VPC).
On-prem firewall rules apply.

| Traffic | Source → Destination | Port | Rule |
|---|---|---|---|
| Kubernetes API | On-prem node → EKS control plane | 443 | Allow |
| Image pulls | On-prem node → ECR | 443 | Allow |
| SSM | On-prem node → SSM endpoints | 443 | Allow |
| CloudWatch | On-prem node → CW endpoints | 443 | Allow |
| Inter-node | On-prem node ↔ On-prem node | varies | CNI handles |

## Step 7 — Node group (remote vs managed)

EKS Hybrid Nodes use a REMOTE node group (not a managed node group).

| Feature | Managed Node Group | Remote (Hybrid) |
|---|---|---|
| Provisioning | AWS auto-provisions EC2 | Operator manages on-prem servers |
| Scaling | Auto Scaling Group | Manual or on-prem autoscaler |
| Upgrades | AWS manages via EKS API | Operator runs nodeadm upgrade |
| Security groups | VPC SG on EC2 | On-prem firewall rules |
| Monitoring | CloudWatch (automatic) | CloudWatch agent (manual install) |
| IAM | EC2 instance profile | Activation code + IAM role |

Hybrid node groups are managed outside of AWS. The operator manages
capacity, OS patching, and hardware maintenance.

## Step 8 — Upgrade strategy

Upgrading hybrid nodes follows a different process than managed node
groups.

```text
1. Upgrade EKS control plane (aws eks update-cluster-version)
2. Upgrade nodeadm on each on-prem node (rolling, one at a time)
3. For each node:
   kubectl drain <node> --ignore-daemonsets --delete-emptydir-data
   → Upgrade nodeadm → kubectl uncordon <node>
   → Verify node returns to Ready
4. Repeat for all nodes
```

**Key implication:** hybrid node upgrades are a manual, rolling process.
There is no AWS-managed auto-upgrade. Always upgrade the control plane
before upgrading nodes.

## Step 9 — Health monitoring (CloudWatch agent)

CloudWatch agent must be installed on each on-prem node for health
monitoring. Without it, zero visibility into node health.

```bash
# On the on-prem node:
wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
rpm -U amazon-cloudwatch-agent.rpm

# Configure (JSON config at /opt/aws/amazon-cloudwatch-agent/etc/)
# Collect: CPU, mem, disk metrics + kubelet.log + system logs
# Log groups: /eks/hybrid/kubelet, /eks/hybrid/system

systemctl start amazon-cloudwatch-agent
systemctl enable amazon-cloudwatch-agent
```

**Key metrics to monitor:** kubelet health, CPU/memory, disk usage,
network connectivity to control plane, pod restart counts.

## Step 10 — SSM Session Manager access

SSM Session Manager is the recommended remote access method for hybrid
nodes (NOT SSH through a bastion).

**Prerequisites:** SSM agent installed on on-prem node; IAM role has
`AmazonSSMManagedInstanceCore`; node has network path to SSM endpoints.

```bash
# Create a managed-instance activation (registers on-prem as SSM managed)
aws ssm create-activation \
  --iam-role EKSHybridSSMRole \
  --registration-limit 10 \
  --expiration-date $(date -u -v+30d +"%Y-%m-%dT%H:%M:%SZ")

# On the on-prem node: register with SSM using returned code+id
# sudo amazon-ssm-agent -register -code <code> -id <id> -region us-east-1

# Start a session
aws ssm start-session --target mi-xxxxxxxxxxxxxxxxx
```

**Key implication:** SSM Session Manager provides audited, keyless
access to on-prem nodes. No SSH keys, no bastion hosts, no open
firewall ports. All access is logged to CloudTrail.

## Step 11 — Capacity planning

On-prem nodes must meet Kubernetes minimum requirements.

| Resource | Minimum | Recommended (production) |
|---|---|---|
| CPU | 2 cores | 4+ cores |
| RAM | 4 GB | 16+ GB |
| Storage | 20 GB | 100+ GB (SSD) |
| Network | 1 Gbps | 10+ Gbps |

**Planning:** max 110 pods per node (kubelet default); sum of pod CPU/
memory requests must fit in allocatable; leave storage headroom for
images, logs, and ephemeral containers.

## Step 12 — Node draining (on-prem maintenance)

Drain hybrid nodes before on-prem maintenance (hardware, OS patching,
reboots).

```bash
# Cordon (no new pods scheduled)
kubectl cordon <node-name>

# Drain (evict running pods)
kubectl drain <node-name> \
  --ignore-daemonsets --delete-emptydir-data --grace-period=300

# After maintenance, uncordon
kubectl uncordon <node-name>
kubectl get node <node-name>   # Verify Ready
```

**Best practices:** drain one node at a time (rolling); use
PodDisruptionBudgets to ensure enough replicas; wait for pods to
reschedule before powering off.

## Step 13 — Recent features

- **EKS Hybrid Nodes GA (2024-2025):** On-prem servers join EKS clusters
  as worker nodes using activation-based registration.
- **nodeadm automation (2024-2025):** Automates kubelet configuration,
  certificate management, and node registration. Supports Amazon Linux,
  Ubuntu, RedHat.
- **Pod Identity for hybrid nodes (2024-2025):** EKS Pod Identity
  extended to hybrid nodes with on-prem pod identity agent. Replaces
  IRSA for hybrid workloads.
- **SSM Session Manager for hybrid (2024-2025):** Managed instance
  activation enables audited, keyless access to on-prem nodes.
- **CloudWatch agent for hybrid (2024-2025):** Enhanced agent with
  pre-built dashboards for kubelet health, pod metrics, connectivity.
- **Hybrid node upgrade tooling (2025-2026):** Automated rolling upgrade
  support via nodeadm.
- **Direct Connect optimization (2025-2026):** Performance improvements
  reducing latency for hybrid node-to-control-plane communication.

## NEVER do these things

1. **NEVER use IAM access keys for hybrid node registration.** Hybrid
   nodes register using an ACTIVATION CODE generated by the EKS API.
   IAM access keys are NOT the bootstrap mechanism.

2. **NEVER assume pod identity works the same as managed node groups.**
   Hybrid nodes need the pod identity agent explicitly installed. No
   EC2 instance profile, no IMDS — the agent uses activation-based auth.

3. **NEVER register hybrid nodes without verifying the network path.**
   Nodes MUST reach the EKS control plane API. Without Direct Connect,
   VPN, or another network path, nodes cannot register or maintain
   heartbeats.

4. **NEVER use SSH through a bastion for hybrid node access.** Use SSM
   Session Manager instead — audited, keyless, no open firewall ports.

5. **NEVER upgrade hybrid nodes before the control plane.** Always
   upgrade the EKS control plane first, then roll node upgrades.

6. **NEVER power off a hybrid node without draining.** Use
   `kubectl drain` to evict pods gracefully. Hard shutdowns cause pod
   disruption and data loss for stateful workloads.

7. **NEVER assume CloudWatch metrics are automatic for hybrid nodes.**
   The agent must be manually installed on each on-prem node.

8. **NEVER skip the activation code TTL check.** Activation codes
   expire. If expired, re-generate before attempting registration.

9. **NEVER apply VPC security groups to hybrid nodes.** Hybrid nodes
   are NOT in the VPC. Use on-prem firewall rules.

10. **NEVER assume hybrid nodes auto-scale.** Hybrid node groups are
    managed outside of AWS. Capacity and lifecycle are the operator's
    responsibility.

## Output format

```text
EKS_HYBRID: <cluster-name> ← <on-prem-node> (<node-role-arn>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] EKS cluster: <cluster-name> — ACTIVE
  [✓|✗] Hybrid node IAM role: <role-arn>
  [✓|✗] Activation code/ID: generated (type: HYBRID_LINUX, TTL: <n> days)
  [✓|✗] Connector agent (nodeadm): installed on <n> node(s)
  [✓|✗] Pod identity: agent running + <n> association(s) configured
  [✓|✗] Network path: Direct Connect | VPN | Public (latency: <n>ms)
  [✓|✗] Security group mapping: on-prem firewall rules (no VPC SG)
  [✓|✗] Node group: REMOTE (operator-managed, <n> node(s) registered)
  [✓|✗] Upgrade strategy: rolling (control plane first, then nodes)
  [✓|✗] CloudWatch agent: installed on <n>/<n> node(s)
  [✓|✗] SSM Session Manager: enabled (keyless, audited access)
  [✓|✗] Capacity: CPU <n> cores, RAM <n> GB, Storage <n> GB per node
  [✓|✗] Node draining: configured (PodDisruptionBudget, rolling maintenance)
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws eks describe-cluster --name <cluster-name>
  kubectl get nodes --show-labels
  kubectl get pods -A --field-selector spec.nodeName=<node-name>
  aws ssm describe-instance-information --query 'InstanceInformationList[*].{ID:InstanceId,Ping:PingStatus}'
  aws cloudwatch describe-alarms --alarm-name-prefix eks-hybrid
```

### Worked example — hybrid node registration with Direct Connect

```text
EKS_HYBRID: prod-cluster ← on-prem-node-01 (arn:aws:iam::123456789012:role/EKSHybridNodeRole)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] EKS cluster: prod-cluster — ACTIVE (v1.30)
  [✓] Hybrid node IAM role: arn:aws:iam::123456789012:role/EKSHybridNodeRole
  [✓] Activation code/ID: generated (type: HYBRID_LINUX, TTL: 7 days)
  [✓] Connector agent (nodeadm): installed on 3 node(s)
  [✓] Pod identity: agent running + 2 association(s) configured
  [✓] Network path: Direct Connect (latency: 12ms, private VIF)
  [✓] Security group mapping: on-prem firewall rules (no VPC SG)
  [✓] Node group: REMOTE (operator-managed, 3 node(s) registered)
  [✓] Upgrade strategy: rolling (control plane first, then nodes)
  [✓] CloudWatch agent: installed on 3/3 node(s)
  [✓] SSM Session Manager: enabled (keyless, audited access)
  [✓] Capacity: CPU 8 cores, RAM 32 GB, Storage 200 GB per node
  [✓] Node draining: configured (PodDisruptionBudget, rolling maintenance)
  [✓] Tags: Environment=production, Topology=hybrid
VERIFICATION_COMMANDS:
  aws eks describe-cluster --name prod-cluster
  kubectl get nodes --show-labels
  kubectl get pods -A --field-selector spec.nodeName=on-prem-node-01
  aws ssm describe-instance-information --query 'InstanceInformationList[*].{ID:InstanceId,Ping:PingStatus}'
```

## Error handling

### Node stuck in NotReady
- Check network path to control plane (latency, packet loss). Verify
  kubelet running (`systemctl status kubelet`). Check activation code
  not expired. Review kubelet logs for connection errors.

### Pod identity permission denied
- Verify pod identity agent running on the node. Check the association
  exists in the EKS API. Ensure service account name matches. Check the
  node's IAM role can assume the pod-level role.

### Node cannot pull images from ECR
- Verify network path to ECR (443/TCP). Check IAM role has
  `AmazonEC2ContainerRegistryReadOnly`. Verify on-prem firewall allows
  outbound 443 to ECR.

### SSM Session Manager cannot connect
- Verify SSM agent running on the node. Check node is registered as SSM
  managed instance. Verify network path to SSM endpoints (443/TCP).
  Check IAM role has `AmazonSSMManagedInstanceCore`.

### Activation code expired
- Re-generate via the EKS API. Update nodeadm config. Restart kubelet.

## Domain

AWS CloudOps / Amazon EKS Hybrid Nodes Provisioning & On-Premises
Kubernetes Node Management.

## AWS documentation

- **EKS Hybrid Nodes Guide** — https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes.html
- **Hybrid node IAM role** — https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-iam-role.html
- **Activation code and registration** — https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-activation.html
- **nodeadm connector agent** — https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-nodeadm.html
- **Pod Identity** — https://docs.aws.amazon.com/eks/latest/userguide/pod-id.html
- **SSM Session Manager** — https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager.html
- **Direct Connect** — https://docs.aws.amazon.com/directconnect/latest/UserGuide/Welcome.html
- **EKS Hybrid Nodes pricing** — https://aws.amazon.com/eks/pricing/
