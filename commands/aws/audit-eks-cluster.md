---
description: Audit an EKS cluster for public API endpoint exposure, disabled control-plane logging, IAM auth mapRoles misconfiguration, security group ingress exposure, and outdated Kubernetes version.
nl_triggers:
  - "audit this EKS cluster"
  - "check EKS API endpoint"
  - "is my EKS cluster public"
  - "EKS control plane logging"
  - "audit aws-auth ConfigMap"
  - "system:masters mapping"
  - "check EKS security groups"
  - "EKS version outdated"
  - "Kubernetes version lifecycle"
  - "harden EKS cluster"
  - "EKS cluster security posture"
  - "eks endpoint public access"
  - "kubelet port exposed"
  - "node IAM role cluster admin"
routes_to: eks-cluster-auditor
---

# /aws:audit-eks-cluster

Activate the `eks-cluster-auditor` skill and audit one or more EKS
cluster configurations for security exposure.

## What it does

Reads an EKS cluster configuration (describe-cluster output), optionally
paired with the aws-auth ConfigMap and node security groups, and applies
priority-ordered classification:

1. Public API endpoint — endpointPublicAccess: true with
   publicAccessCidrs 0.0.0.0/0 or empty → PUBLIC_ENDPOINT.
2. Control-plane logging — all log types disabled → LOGGING_DISABLED.
3. Config gap — system:masters to node role / wildcard username / broad
   ARN, OR security group 0.0.0.0/0 on ports 10250/443/22 → CONFIG_GAP.
4. Outdated version — cluster N-3 or older from latest → OUTDATED.
5. All clean → OK.

Emits a deterministic VERDICT per cluster:

```text
CLUSTER: <name>
VERDICT: PUBLIC_ENDPOINT | LOGGING_DISABLED | CONFIG_GAP | OUTDATED | OK
REASON: <1-2 sentences citing the worst finding and step number>
FINDINGS:
  - [PUBLIC_ENDPOINT] <finding description (Step 1)>
  - [CONFIG_GAP] <finding description (Step 3a/3b)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste an EKS cluster configuration and ask any of:

- "audit this EKS cluster"
- "is my API server public?"
- "check control-plane logging"
- "audit the aws-auth ConfigMap"
- "are my security groups open?"
- "is my Kubernetes version outdated?"

A bare cluster name + any audit verb ("audit this cluster", "check EKS
security") also routes here via the orchestrator.

## Inputs

- An EKS cluster configuration (JSON from `aws eks describe-cluster`),
  pasted inline or referenced by file path.
- aws-auth ConfigMap mapRoles (optional but recommended for full audit).
- Node security group rules (optional but recommended).
- Latest available EKS version (for version lifecycle evaluation).

## Outputs

- One VERDICT block per cluster (multiple findings listed but verdict is
  the highest-priority match).
- Enumerated FINDINGS list with per-finding category and step citation.
- Specific remediation: disable public endpoint, enable logging, fix
  mapRoles, restrict security groups, upgrade version.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for EKS compute security).
- `/aws:audit-ec2-security-groups` for standalone EC2 security group
  auditing (this skill checks node SGs in the EKS context).
- `/aws:audit-iam-least-privilege` for IAM policy analysis of the EKS
  node and service roles.
