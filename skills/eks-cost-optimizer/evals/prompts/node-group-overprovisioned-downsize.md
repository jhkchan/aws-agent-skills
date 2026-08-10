# Eval prompt: node-group-overprovisioned-downsize

Optimize this EKS node group for cost. Walk the optimization framework and
emit the standard optimization block (TARGET, VERDICT, REASON,
RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

Cluster: prod-cluster-node-group-overprovisioned-downsize
Region: us-east-1
Node group: prod-general-purpose
Instance type: m5.2xlarge
Desired size: 4 nodes (min 3, max 10)
Capacity type: ON_DEMAND
Autoscaler: Cluster Autoscaler

Utilization (Container Insights, last 30 days):
  - node_cpu_utilization: avg=12%, max=20%
  - node_memory_utilization: avg=25%, max=35%
  - Average pods per node: 8 (allocatable capacity ~28 pods)

Bin-packing analysis (kubectl top):
  - Pod requests/usage ratio: 1.4x (healthy)
  - CPU requests per pod: 1000m, actual usage: 700m avg

Pricing: On-Demand (no Savings Plan)
Workload: mixed microservices (Java 17, Python, Go), multi-arch
Docker images available (arm64 manifest entries present).
