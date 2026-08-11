# Eval: ebs-csi-irsa

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — aws-ebs-csi-driver with IRSA for ebs-csi-controller-sa, K8s 1.29 compatibility

## Prompt

I need to install the aws-ebs-csi-driver add-on on my EKS cluster
app-cluster (K8s 1.29) so I can use EBS PersistentVolumes. The
cluster has an OIDC provider. Set up IRSA for the EBS CSI
controller service account. Account ID: 123456789012.
