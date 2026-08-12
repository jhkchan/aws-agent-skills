# Eval prompt: ca-to-karpenter-migration

Design a migration from Cluster Autoscaler to Karpenter for the
following production cluster. Emit the standard AUTOSCALING block.
Include the migration sequence (uninstall CA first, then install
Karpenter) and flag the conflict risk of running both simultaneously.

Design reference: ca-to-karpenter-migration
Account: 111111111111
Region: us-east-1

Cluster: prod-cluster, EKS 1.30, 40 nodes
Current autoscaler: Cluster Autoscaler 9.34.0 (auto-discovery)
Desired: migrate to Karpenter 1.0.0 with consolidation
metrics-server: installed
Prometheus Adapter: installed
HPA: 3 deployments with HPA configured
Spot: 50% via ASG mixed instance policy (c5, m5)
Karpenter native interruption handling: desired (replace NTH)
