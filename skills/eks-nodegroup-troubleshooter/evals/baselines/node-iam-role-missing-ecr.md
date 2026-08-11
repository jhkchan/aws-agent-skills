# Baseline (no-skill) response: node-iam-role-missing-ecr

This file captures what a generic assistant produces WITHOUT the
eks-nodegroup-troubleshooter skill loaded.

---

Your pods are showing ImagePullBackOff which means they can't pull
the container image from ECR. This is usually a permissions issue.
Check that your EKS nodes have the right IAM permissions to access
ECR. You may need to add ECR permissions to the node role.

Also verify that the image exists in the repository and that the
repository policy allows access from your account. If the nodes are
in a VPC, check if there are VPC endpoints for ECR configured.
