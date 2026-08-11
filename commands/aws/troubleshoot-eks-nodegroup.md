---
description: Diagnose Amazon EKS managed node group issues — nodes NotReady, VPC CNI IP exhaustion, AMI version mismatch, ASG launch failures, node IAM role permissions, taints, custom AMI bootstrap errors, and scaling failures. Emits ROOT_CAUSE_IDENTIFIED or INSUFFICIENT_DATA.
nl_triggers:
  - "EKS nodes NotReady"
  - "EKS node group failed"
  - "EKS node not joining cluster"
  - "EKS VPC CNI IP exhaustion"
  - "EKS NoSchedule taint"
  - "EKS ASG launch failure"
  - "EKS InsufficientInstanceCapacity"
  - "EKS AMI version mismatch"
  - "EKS node IAM role"
  - "EKS ECR image pull"
  - "EKS security group"
  - "EKS kubelet error"
  - "EKS container runtime"
  - "EKS DiskPressure"
  - "EKS cluster autoscaler"
  - "EKS Karpenter"
  - "EKS custom AMI bootstrap"
  - "EKS node group scaling"
  - "troubleshoot EKS nodegroup"
  - "diagnose EKS node failure"
  - "EKS pods Pending insufficient IP"
routes_to: eks-nodegroup-troubleshooter
---

# /aws:troubleshoot-eks-nodegroup

Activate the `eks-nodegroup-troubleshooter` skill and diagnose an
Amazon EKS managed node group issue through the node-state-driven
diagnostic tree.

## What it does

Reads a symptom description (nodes NotReady, pods stuck Pending, ASG
launch failures, scaling issues) plus the cluster and node group
configuration, then walks the node-state-driven diagnostic tree to a
root cause with positive evidence:

1. **Pre-flight** — node group config (`describe-nodegroup`), cluster
   details (`describe-cluster`), node states (`kubectl get nodes` /
   `describe node`), ASG activity, recent events.
2. **Symptom entry** — map the observed state to a diagnostic branch.
3. **Branch-specific probes** —
   - Nodes NotReady: kubelet logs, container runtime, conditions.
   - VPC CNI: subnet `AvailableIpAddressCount`, `aws-node` warm pool,
     IRSA role permissions.
   - AMI version: `nodegroup.version` vs `cluster.kubernetesVersion`.
   - ASG: `describe-scaling-activities`, `InsufficientInstanceCapacity`,
     launch template.
   - Custom AMI: user-data, console output, `bootstrap.sh` args.
   - Taints: `describe node` taints vs pod tolerations.
   - Scheduling: `top nodes`, pod requests vs node allocatable.
   - Node IAM: role policies for ECR, SSM, CNI.
   - Security groups: node SG egress to cluster SG on 443.
   - Scaling: ASG min/max, cluster autoscaler / Karpenter logs.
4. **Verdict** — ROOT_CAUSE_IDENTIFIED (with failing probe) or
   INSUFFICIENT_DATA (missing context).

Emits a deterministic diagnostic block per target:

```text
TARGET: <cluster-name / nodegroup-name>
VERDICT: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
REASON: <1-2 sentences naming the observed state and ROOT_CAUSE>
ROOT_CAUSE: <VPC_CNI_IP_EXHAUSTION | NODE_IAM_ROLE_ECR | ...>
EVIDENCE:
  - <observed node/pod state or error string>
  - <failing probe — command and output that confirms the cause>
  - <passing probes — categories ruled out>
REMEDIATION:
  1. <specific action with CLI command or kubectl>
  2. <verification command after the fix>
```

## When to invoke

Paste a symptom description and ask any of:

- "EKS nodes are NotReady after upgrade"
- "EKS pods stuck Pending with insufficient IP"
- "EKS ImagePullBackOff on new node group"
- "EKS ASG can't launch instances"
- "EKS custom AMI nodes not joining cluster"
- "EKS cluster autoscaler not scaling"
- "EKS nodes DiskPressure"

A bare cluster name + node issue also routes here via the orchestrator.

## Inputs

- Symptom description: node states, pod states, error strings, ASG
  failures, scaling issues.
- Cluster and node group: names, K8s version, AMI type/version,
  instance types, subnets, scaling config.
- For live-cluster diagnosis: the skill uses `describe-nodegroup`,
  `describe-cluster`, `describe-auto-scaling-groups`,
  `describe-scaling-activities`, `describe-subnets` /
  `describe-security-groups`, `kubectl get nodes` / `describe node` /
  `get pods` / `describe pod` / `get events` / `top nodes`.

## Outputs

- One diagnostic block per target cluster/node group.
- ROOT_CAUSE value from the enumerated set.
- Evidence section with the failing probe AND passing probes.
- Specific remediation: VPC CNI config, node group version update, IAM
  policy attach, security group rule, ASG scaling config, user-data fix.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 2 Troubleshoot specialist for EKS node group issues).
- `/aws:troubleshoot-eks-pod` for application-level pod crash debugging
  (CrashLoopBackOff, OOMKilled, probe failures).
- `/aws:audit-eks-cluster` for configuration posture audits on the
  same cluster (control plane access, logging, encryption).
