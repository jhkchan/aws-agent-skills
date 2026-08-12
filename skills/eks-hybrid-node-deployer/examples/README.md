# End-to-End Example: EKS Hybrid Node Deployment

A walkthrough showing how to use the `eks-hybrid-node-deployer` skill
from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are registering 3 on-prem Ubuntu servers as EKS Hybrid Nodes to an
existing EKS cluster, with Direct Connect networking, pod identity for
workloads, SSM Session Manager for access, and CloudWatch monitoring.
The deployment needs:

- EKS cluster: prod-cluster (v1.30, us-east-1)
- On-prem nodes: 3x Ubuntu servers (8 cores, 32 GB RAM each)
- Hybrid node IAM role: EKSHybridNodeRole
- Networking: Direct Connect (private VIF, 12ms latency)
- Pod identity: my-app-sa → MyAppPodRole (production namespace)
- SSM Session Manager: keyless, audited access
- CloudWatch agent: health monitoring on all 3 nodes

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-eks-hybrid-nodes
```

Then paste the requirements.

### Option B: Natural language

```
You: "Register 3 on-prem Ubuntu servers as EKS hybrid nodes to
      prod-cluster. Direct Connect networking. Pod identity for
      production workloads. SSM for access. CloudWatch monitoring."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "register on-prem nodes to eks"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
EKS_HYBRID: prod-cluster ← on-prem-node-01 (arn:aws:iam::123456789012:role/EKSHybridNodeRole)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] EKS cluster: prod-cluster — ACTIVE (v1.30)
  [✓] Hybrid node IAM role: arn:aws:iam::123456789012:role/EKSHybridNodeRole
  [✓] Activation code/ID: generated (type: HYBRID_LINUX, TTL: 7 days)
  [✓] Connector agent (nodeadm): installed on 3 node(s)
  [✓] Pod identity: agent running + 1 association(s) configured
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
  aws ssm describe-instance-information
```

---

## Step 3 — Provisioning commands

```bash
# 1. Create hybrid node IAM role
aws iam create-role --role-name EKSHybridNodeRole \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ec2.amazonaws.com"},"Action":"sts:AssumeRole"}]}'

aws iam attach-role-policy --role-name EKSHybridNodeRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly
aws iam attach-role-policy --role-name EKSHybridNodeRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
aws iam attach-role-policy --role-name EKSHybridNodeRole \
  --policy-arn arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy

# 2. Create EKS access entry (activation for hybrid nodes)
aws eks create-access-entry \
  --cluster-name prod-cluster \
  --principal-arn arn:aws:iam::123456789012:role/EKSHybridNodeRole \
  --type HYBRID_LINUX

# 3. Create pod identity association
aws eks create-pod-identity-association \
  --cluster-name prod-cluster \
  --namespace production \
  --service-account my-app-sa \
  --role-arn arn:aws:iam::123456789012:role/MyAppPodRole

# 4. On each on-prem node (run locally on the node):
#    nodeadm init --cluster-name prod-cluster \
#      --cluster-endpoint https://XXXX.gr7.us-east-1.eks.amazonaws.com \
#      --cluster-ca <base64-ca> \
#      --activation-id <id> --activation-code <code> \
#      --node-role arn:aws:iam::123456789012:role/EKSHybridNodeRole
#    nodeadm enable-pod-identity --role arn:aws:iam::123456789012:role/EKSHybridNodeRole
#    nodeadm up

# 5. Install CloudWatch agent on each node (locally)
#    rpm -U amazon-cloudwatch-agent.rpm
#    systemctl start amazon-cloudwatch-agent && systemctl enable amazon-cloudwatch-agent

# 6. Register nodes with SSM for Session Manager
aws ssm create-activation \
  --iam-role EKSHybridSSMRole \
  --registration-limit 10 \
  --expiration-date $(date -u -v+30d +"%Y-%m-%dT%H:%M:%SZ")
```

---

## Step 4 — Post-deployment verification

```bash
# Verify cluster
aws eks describe-cluster --name prod-cluster --query 'cluster.status'

# Verify nodes registered
kubectl get nodes --show-labels | grep hybrid
# Expected: 3 nodes with Ready status

# Verify pod identity
aws eks list-pod-identity-associations \
  --cluster-name prod-cluster \
  --query 'associations[*].{NS:namespace,SA:serviceAccount,Role:roleArn}' \
  --output table

# Verify SSM managed instances
aws ssm describe-instance-information \
  --query 'InstanceInformationList[*].{ID:InstanceId,Ping:PingStatus}' \
  --output table

# Verify network latency (from on-prem node)
ping -c 10 <eks-endpoint-host>
# Expected: avg latency < 100ms for Direct Connect
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Node registration | IAM access keys | Activation code (NOT access keys) | Hybrid nodes use activation-based bootstrap |
| Pod identity | Assumes same as managed NG | Agent must run on-prem (no IMDS) | No EC2 instance profile on hybrid nodes |
| Network path | Assumes internet is enough | Direct Connect/VPN required | Nodes MUST reach EKS API for heartbeats |
| Security | Applies VPC security groups | On-prem firewall rules (no VPC SG) | Hybrid nodes are NOT in the VPC |
| Remote access | SSH via bastion | SSM Session Manager | Keyless, audited, no open ports |
| Monitoring | Assumes automatic CW | Agent must be manually installed | No EC2 integration for on-prem nodes |
| Upgrades | Assumes auto-upgrade | Manual rolling via nodeadm | No AWS-managed upgrade for hybrid nodes |

---

## Related artifacts

- **Skill definition:** `skills/eks-hybrid-node-deployer/SKILL.md`
- **Networking and registration guide:** `skills/eks-hybrid-node-deployer/references/networking-and-registration.md`
- **Pod identity and access guide:** `skills/eks-hybrid-node-deployer/references/pod-identity-and-access.md`
- **Slash command:** `commands/aws/deploy-eks-hybrid-nodes.md`
- **Eval suite:** `skills/eks-hybrid-node-deployer/evals/evals.json`
- **Legacy test cases:** `skills/eks-hybrid-node-deployer/eval/test-cases.yaml`
