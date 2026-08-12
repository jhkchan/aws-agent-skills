# Eval: hybrid-node-basic-registration

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — activation code/ID as bootstrap credential (not IAM access keys), hybrid node IAM role, nodeadm connector agent, kubelet connects to control plane

## Prompt

Register 3 on-prem Ubuntu servers as EKS hybrid nodes to cluster
prod-cluster in us-east-1. Hybrid node IAM role EKSHybridNodeRole.
Kubernetes v1.30. Container runtime containerd already installed.
Create the activation entry and nodeadm bootstrap commands.
Tags: Environment=production.
