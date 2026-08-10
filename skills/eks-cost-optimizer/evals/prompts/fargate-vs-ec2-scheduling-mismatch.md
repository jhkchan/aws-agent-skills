# Eval prompt: fargate-vs-ec2-scheduling-mismatch

Optimize this EKS dev cluster for cost. Walk the optimization framework and
emit the standard optimization block.

Cluster: dev-cluster-fargate-vs-ec2-scheduling-mismatch
Region: us-east-1
Node group: dev-nodegroup
Instance type: m5.large
Desired size: 3 nodes (min 1, max 5)
Capacity type: ON_DEMAND

Utilization (Container Insights, last 30 days):
  - node_cpu_utilization: avg=5%, max=10%
  - node_memory_utilization: avg=8%, max=15%
  - Pods per node: 2 (very low density)

Pod details:
  - 6 pods total, each requesting 0.5 vCPU + 1 GB
  - No DaemonSets in use
  - No privileged pods
  - Sporadic usage (dev environment, idle nights/weekends)

Pricing: On-Demand
Workload: dev/test microservices, Python and Node.js, no ARM dependencies.
