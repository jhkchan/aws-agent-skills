# Eval prompt: missing-metrics-server

Design an EKS autoscaling system for the following staging cluster.
Emit the standard AUTOSCALING block.

Design reference: missing-metrics-server
Account: 111111111111
Region: us-east-1

Cluster: staging-cluster, EKS 1.28, 8 nodes (managed node group, c5.large)
metrics-server: NOT installed
Prometheus: not installed
Current autoscaler: none
HPA: none configured
KEDA: not installed
PDB: none
Overprovisioning: none
Spot: 0% (on-demand only)
