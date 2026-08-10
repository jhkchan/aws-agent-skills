# Baseline (no-skill) response: imagepullbackoff-node-role-no-ecr

This file captures what a generic assistant produces WITHOUT the
eks-pod-troubleshooter skill loaded.

---

Your pod can't pull the image. ImagePullBackOff usually means there's
a permission issue or the image doesn't exist. Since you confirmed the
image exists in ECR, the problem is likely IAM permissions.

Check that your EKS cluster has permission to pull from ECR. You may
need to attach the AmazonEC2ContainerRegistryReadOnly policy. Also
check that the image name and tag are spelled correctly, and consider
using imagePullPolicy: Always to make sure kubectl pulls a fresh copy.

If you're using IRSA, make sure the service account annotation points
to a role with ECR permissions.
