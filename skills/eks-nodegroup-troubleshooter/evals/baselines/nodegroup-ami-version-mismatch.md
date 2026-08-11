# Baseline (no-skill) response: nodegroup-ami-version-mismatch

This file captures what a generic assistant produces WITHOUT the
eks-nodegroup-troubleshooter skill loaded.

---

After upgrading your EKS cluster to 1.30, some nodes are showing
NotReady. This could be because the node AMI version doesn't match
the new cluster version. The nodes are running kubelet 1.28 which
might be too old for the 1.30 control plane.

You should try updating the node group to a newer AMI version that
matches the cluster version. Also check the kubelet logs on the
NotReady nodes to see what errors are being reported. You might
need to drain and replace the old nodes.
