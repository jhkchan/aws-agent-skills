# Eval: version-conflict-resolution

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — self-managed to EKS-managed migration, OVERWRITE conflict resolution, configuration-values migration

## Prompt

My cluster migration-cluster (K8s 1.30) has a self-managed
vpc-cni installed via Helm (the aws-node DaemonSet). I have
custom env vars: AWS_VPC_K8S_CNI_LOGLEVEL=DEBUG and
ENABLE_PREFIX_DELEGATION=true. I want to migrate to the
EKS-managed vpc-cni add-on without losing my customizations.
OIDC provider exists. Account ID: 123456789012.
