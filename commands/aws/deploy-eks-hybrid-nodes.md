---
description: Provision Amazon EKS Hybrid Nodes with production-grade defaults: hybrid node IAM role, activation code/ID registration (not IAM access keys), nodeadm connector agent, pod identity for hybrid workloads, Direct Connect/VPN networking to EKS control plane, on-prem firewall rules (not VPC security groups), SSM Session Manager for access, CloudWatch agent for monitoring, upgrade strategy, and node draining. Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create eks hybrid nodes"
  - "deploy eks hybrid nodes"
  - "register on-prem node to eks"
  - "eks hybrid node activation code"
  - "eks hybrid pod identity"
  - "eks hybrid networking"
  - "eks hybrid direct connect"
  - "eks hybrid nodeadm"
  - "eks hybrid ssm session manager"
  - "eks hybrid cloudwatch"
  - "eks hybrid node drain"
  - "eks hybrid node upgrade"
  - "eks hybrid capacity"
routes_to: eks-hybrid-node-deployer
---

# /aws:deploy-eks-hybrid-nodes

Activate the `eks-hybrid-node-deployer` skill and register on-prem
servers as Amazon EKS Hybrid Nodes with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Hybrid node IAM role (identity for on-prem nodes)
2. Activation code/ID (bootstrap credential — NOT IAM access keys)
3. Connector agent (nodeadm — kubelet bootstrap on on-prem nodes)
4. Pod identity for hybrid workloads (no IMDS, agent required)
5. Networking (Direct Connect/VPN to EKS control plane API)
6. Security group mapping (on-prem firewall rules, NOT VPC SGs)
7. Node group (REMOTE — operator-managed, not AWS-managed)
8. Upgrade strategy (control plane first, then rolling node upgrades)
9. Health monitoring (CloudWatch agent — manually installed)
10. SSM Session Manager (keyless, audited remote access)
11. Capacity planning (CPU, RAM, storage requirements)
12. Node draining (PodDisruptionBudget, rolling maintenance)

## When to use

- You need to register on-prem servers as EKS hybrid nodes.
- You need to configure activation codes for on-prem registration.
- You need pod identity for workloads on hybrid nodes.
- You need Direct Connect or VPN networking for hybrid nodes.
- You need SSM Session Manager access to on-prem nodes.
- You need CloudWatch health monitoring for hybrid nodes.
- You need to plan hybrid node upgrades.
- You need to drain hybrid nodes for on-prem maintenance.

## When NOT to use

- **Standard EKS managed node groups (EC2)** — use managed node group
  skills.
- **EKS Fargate** — different serverless model, no node management.
- **EKS Anywhere** — self-managed control plane on-prem (not EKS
  hybrid).
- **ECS** — different container orchestration platform.
- **Auditing existing hybrid nodes** — use EKS audit skills.

## How to invoke

### Slash command

```
/aws:deploy-eks-hybrid-nodes
```

Then provide: EKS cluster name, on-prem node count and OS, hybrid node
IAM role name, activation code TTL, network path type (Direct Connect
or VPN), pod identity requirements, SSM activation, CloudWatch agent
install, capacity (CPU/RAM/storage), tags.

### Natural language

Any of these routes to the same skill:

- "register on-prem nodes to my eks cluster"
- "set up eks hybrid nodes with direct connect"
- "configure pod identity for hybrid workloads"
- "enable ssm session manager for eks hybrid nodes"
- "drain eks hybrid nodes for maintenance"

### CLI routing

```bash
node cli/bin/cli.js route "register on-prem nodes to eks"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to register on-prem
nodes as EKS hybrid nodes. The output checklist feeds into verification
pipelines and downstream audit skills.

## Example

```
You: /aws:deploy-eks-hybrid-nodes

     Register 3 on-prem Ubuntu servers as EKS hybrid nodes to
     prod-cluster. Hybrid node IAM role EKSHybridNodeRole. Direct
     Connect networking. Pod identity for my-app-sa → MyAppPodRole.
     SSM Session Manager for access. CloudWatch monitoring.

Skill:
  EKS_HYBRID: prod-cluster ← on-prem-node-01 (EKSHybridNodeRole)
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Activation code/ID: generated (type: HYBRID_LINUX)
    [✓] Connector agent (nodeadm): installed on 3 node(s)
    [✓] Network path: Direct Connect (latency: 12ms)
    [✓] Pod identity: agent running + 1 association(s)
    [✓] SSM Session Manager: enabled
    [✓] CloudWatch agent: installed on 3/3 node(s)
  VERIFICATION_COMMANDS:
    aws eks describe-cluster --name prod-cluster
    kubectl get nodes --show-labels
    aws ssm describe-instance-information
```

## References

- Skill definition: `skills/eks-hybrid-node-deployer/SKILL.md`
- Networking and registration guide: `skills/eks-hybrid-node-deployer/references/networking-and-registration.md`
- Pod identity and access guide: `skills/eks-hybrid-node-deployer/references/pod-identity-and-access.md`
- Eval suite: `skills/eks-hybrid-node-deployer/evals/evals.json`
