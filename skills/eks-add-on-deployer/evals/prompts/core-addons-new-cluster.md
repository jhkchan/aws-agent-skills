# Eval: core-addons-new-cluster

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — core networking add-ons, K8s 1.30 version compatibility, IRSA for vpc-cni, ENABLE_PREFIX_DELEGATION config

## Prompt

I have a new EKS cluster named production-cluster running
Kubernetes 1.30. I need to set up the core add-ons: vpc-cni,
coredns, and kube-proxy. The cluster has an OIDC provider. For
vpc-cni I want to use IRSA with the AmazonEKS_CNI_Policy. I want
ENABLE_PREFIX_DELEGATION set to true. Account ID: 123456789012.
Tags: Environment=production.
