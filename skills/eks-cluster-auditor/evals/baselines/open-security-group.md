# Baseline (no-skill) response: open-security-group

This file captures what a generic assistant produces WITHOUT the
eks-cluster-auditor skill loaded.

---

The cluster looks mostly well-configured — private endpoint, logging
enabled, and the IAM role mappings are standard. However, the node
security group has an inbound rule allowing 0.0.0.0/0 on port 10250,
which is the kubelet API port.

This exposes the kubelet directly to the internet. While the kubelet
requires authentication, you should still restrict this to your VPC
CIDR or the control plane security group. Remove the 0.0.0.0/0 rule
and replace it with a more specific CIDR.
