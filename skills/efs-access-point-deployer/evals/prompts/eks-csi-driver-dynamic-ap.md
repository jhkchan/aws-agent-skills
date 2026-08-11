# Eval: eks-csi-driver-dynamic-ap

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — CSI driver StorageClass with provisioningMode efs-ap + IRSA role including ClientRootAccess

## Prompt

Set up EKS cluster "prod-cluster" to consume an existing EFS
file system fs-ccccdddddddd (account 123456789012, region
us-east-1) via the EFS CSI driver. I want dynamic access-point
provisioning per PVC with directoryPerms 700 and gidRange
1000-2000. The CSI driver IRSA role is
arn:aws:iam::123456789012:role/efs-csi-driver-role. Verify the
IRSA role includes ClientRootAccess. Mount targets exist in
all three AZs.
