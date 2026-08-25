
<!-- Moved verbatim from SKILL.md (eks-nodegroup-troubleshooter) — progressive-disclosure restructure, lines 491-515 -->

## Worked example — Node IAM role missing ECR

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

<!-- Moved verbatim from SKILL.md (eks-nodegroup-troubleshooter) — progressive-disclosure restructure, lines 519-531 -->

## Worked example — INSUFFICIENT_DATA

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

