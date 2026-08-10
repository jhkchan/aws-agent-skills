# Eval prompt: bin-packing-requests-limits-waste

Optimize this EKS node group for cost. Walk the optimization framework and
emit the standard optimization block. Pay special attention to the
requests-vs-usage analysis.

Cluster: prod-cluster-bin-packing-requests-limits-waste
Region: us-east-1
Node group: prod-services-ng
Instance type: m5.xlarge
Desired size: 6 nodes (min 4, max 12)
Capacity type: ON_DEMAND
Autoscaler: Cluster Autoscaler

Utilization (Container Insights, last 30 days):
  - node_cpu_utilization: avg=15%, max=25%
  - node_memory_utilization: avg=30%, max=40%

Bin-packing analysis (kubectl top + kubectl describe):
  - Pod CPU requests: 4000m per pod (8 pods per node)
  - Actual CPU usage: 500m avg per pod
  - Requests/usage ratio: 8.0x (severe waste)
  - Scheduler sees nodes as "full" (32 vCPU requested per node)
  - Memory requests: 8 GB per pod, actual usage: 2 GB

Pricing: On-Demand
Workload: Java 17 microservices, no Graviton images yet.
