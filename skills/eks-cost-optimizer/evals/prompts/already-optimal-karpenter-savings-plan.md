# Eval prompt: already-optimal-karpenter-savings-plan

Evaluate this EKS cluster for any remaining cost optimization opportunities.
Walk the optimization framework and emit the standard optimization block.

Cluster: prod-cluster-already-optimal-karpenter-savings-plan
Region: us-east-1
Node provisioning: Karpenter v0.37
Consolidation: WhenEmptyOrUnderutilized
Capacity mix: 60% Spot (m7i.xlarge, m6i.xlarge, c7i.xlarge),
  40% On-Demand baseline
Autoscaler: Karpenter

Utilization (Container Insights, last 30 days):
  - node_cpu_utilization: avg=55%, max=68%
  - node_memory_utilization: avg=62%, max=75%
  - Spot interruption rate: 0.3% (low)

Bin-packing:
  - Requests/usage ratio: 1.3x (VPA-managed, tuned)
  - Pod density: 12 pods/node (healthy)

Pricing: 3-year Compute Savings Plan covering 100% of On-Demand baseline.
Fargate not in use (workloads need DaemonSets).
Workload: mixed stateful (PostgreSQL, Redis) and stateless services.
No Graviton path (x86 SIMD dependencies in some services).
