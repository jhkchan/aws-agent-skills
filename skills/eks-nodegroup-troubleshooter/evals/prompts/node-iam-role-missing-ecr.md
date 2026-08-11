# Eval prompt: node-iam-role-missing-ecr

Diagnose the EKS node group issue for the following cluster. Walk the
node-state-driven diagnostic tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, ROOT_CAUSE, EVIDENCE, REMEDIATION).

Symptom: every pod on the newly created node group `prod-ng-2` shows
ImagePullBackOff. The pods are trying to pull images from ECR. The
image exists and the repo policy allows same-account access.

```text
ClusterName: prod-cluster
NodeGroupName: prod-ng-2
KubernetesVersion: "1.30"
NodeRole: arn:aws:iam::111111111111:role/eks-prod-ng-2
NodeRoleAttachedPolicies:
  - AmazonEKSWorkerNodePolicy
AmazonEC2ContainerRegistryReadOnly: NOT ATTACHED

kubectl get pods -A (sample):
  app-pod-1   ImagePullBackOff   0/1   0   8m
  app-pod-2   ImagePullBackOff   0/1   0   8m
  app-pod-3   ImagePullBackOff   0/1   0   8m

kubectl describe pod app-pod-1:
  Warning  Failed   kubelet  Failed to pull image
    "111111111111.dkr.ecr.us-east-1.amazonaws.com/app:v1":
    rpc error: code = Unknown desc = Error response from daemon:
    pull access denied for
    111111111111.dkr.ecr.us-east-1.amazonaws.com/app:v1

ECR context:
  Repository: 111111111111.dkr.ecr.us-east-1.amazonaws.com/app
  Image tag v1 exists, 450 MB
  Repository policy: allows same-account Lambda and EC2 access
  Build is not VPC-attached with endpoint issues
```

The image exists in ECR and the repo policy allows same-account access.
The nodes are Ready. Focus on the node IAM role permissions for ECR.
