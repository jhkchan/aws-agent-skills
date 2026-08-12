# Eval: pod-identity-hybrid-workloads

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — pod identity agent must run on hybrid nodes (no IMDS), pod identity association configured in EKS API, differs from managed node groups

## Prompt

Configure pod identity for workloads running on EKS hybrid nodes
in cluster prod-cluster. Service account my-app-sa in namespace
production should map to IAM role
arn:aws:iam::123456789012:role/MyAppPodRole. Nodes are on-prem
hybrid nodes (no IMDS available). us-east-1.
