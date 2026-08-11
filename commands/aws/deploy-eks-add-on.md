---
description: Provision Amazon EKS add-ons (vpc-cni, coredns, kube-proxy, aws-ebs-csi-driver, metrics-server, adot, guardduty-agent) with production-grade defaults (version compatibility, EKS-managed vs self-managed conflict resolution, IRSA and Pod Identity, configuration values, EKS Auto Mode, EKS Hybrid Nodes). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create eks add-on"
  - "eks add-on"
  - "eks addon"
  - "vpc-cni eks add-on"
  - "coredns eks add-on"
  - "kube-proxy eks add-on"
  - "aws-ebs-csi-driver eks"
  - "metrics-server eks"
  - "adot eks add-on"
  - "guardduty-agent eks"
  - "eks pod identity add-on"
  - "eks auto mode add-on"
  - "eks hybrid nodes add-on"
  - "irsa eks add-on"
  - "eks add-on configuration values"
routes_to: eks-add-on-deployer
---

# /aws:deploy-eks-add-on

Activate the `eks-add-on-deployer` skill and provision Amazon EKS
add-ons with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Add-on types (vpc-cni, coredns, kube-proxy, etc.)
2. Version management (EKS-managed vs self-managed)
3. Configuration values (override existing config)
4. IAM roles for add-ons (IRSA)
5. EKS Pod Identity (latest credential method)
6. EKS Auto Mode add-ons (auto-managed lifecycle)
7. EKS Hybrid Nodes add-ons
8. Recent features

## When to use

- You need to create or update EKS add-ons on a cluster.
- You are migrating from self-managed to EKS-managed add-ons.
- You need to configure IRSA or Pod Identity for an add-on.
- You need to set add-on configuration values.
- You are enabling EKS Auto Mode add-ons.
- You are deploying add-ons for EKS Hybrid Nodes.

## When NOT to use

- **Creating the EKS cluster itself** — use eks-cluster-deployer if
  available, or the EKS API directly.
- **Installing Helm charts that are not EKS add-ons** — use Helm
  directly.
- **Self-managed Kubernetes controllers** outside the EKS add-on
  framework — not this skill.
- **Auditing EKS add-on versions** — use `eks-cluster-auditor`.

## How to invoke

### Slash command

```
/aws:deploy-eks-add-on
```

Then provide: cluster name, Kubernetes version, add-on name(s), add-on
version (or "default"), IRSA or Pod Identity preference, configuration
values JSON, conflict resolution strategy.

### Natural language

Any of these routes to the same skill:

- "install vpc-cni on my EKS cluster"
- "set up the EBS CSI driver with IRSA"
- "use Pod Identity for the ADOT collector"
- "migrate self-managed vpc-cni to EKS-managed"
- "install metrics-server as an EKS add-on"

### CLI routing

```bash
node cli/bin/cli.js route "create eks add-on"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create or update
EKS add-ons. The output checklist feeds into verification pipelines
and downstream audit skills.

## Example

```
You: /aws:deploy-eks-add-on

     Set up vpc-cni, coredns, and kube-proxy on production-cluster
     (K8s 1.30). Use IRSA for vpc-cni with ENABLE_PREFIX_DELEGATION.
     Account: 123456789012.

Skill:
  EKS_ADDON: vpc-cni (v1.18.1-eksbuild.3) on production-cluster
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Cluster: production-cluster — ACTIVE, K8s 1.30
    [✓] Add-on type: vpc-cni
    [✓] Version: v1.18.1-eksbuild.3 (compatible with 1.30)
    [✓] Management mode: EKS-managed
    [✓] Conflict resolution: OVERWRITE
    [✓] Config: {"env":{"ENABLE_PREFIX_DELEGATION":"true"}}
    [✓] IAM: IRSA (role AmazonEKSVPCCNIRole)
    [✓] OIDC provider: present
    [✓] Health: ACTIVE
  VERIFICATION_COMMANDS:
    aws eks describe-addon --cluster-name production-cluster --addon-name vpc-cni
    kubectl get pods -n kube-system -l k8s-app=aws-node
```

## References

- Skill definition: `skills/eks-add-on-deployer/SKILL.md`
- Version management detail: `skills/eks-add-on-deployer/references/addon-version-management.md`
- Provisioning CLI commands: `skills/eks-add-on-deployer/references/provisioning-cli-commands.md`
- Eval suite: `skills/eks-add-on-deployer/evals/evals.json`
