# Eval prompt: spot-node-group-missing-pdb

Evaluate whether this cluster should add a Spot node group for cost savings.
Walk the optimization framework and emit the standard optimization block.

Cluster: prod-cluster-spot-node-group-missing-pdb
Region: us-east-1
Node group: prod-on-demand-ng
Instance type: m5.2xlarge
Desired size: 4 nodes (min 3, max 8)
Capacity type: ON_DEMAND

Utilization (Container Insights, last 30 days):
  - node_cpu_utilization: avg=40%, max=55%
  - node_memory_utilization: avg=50%, max=65%

Bin-packing: requests/usage ratio 1.5x (healthy)
Pod density: 15 pods/node (good)

Request: evaluate Spot node group for this workload to reduce cost.

Safety check results:
  - PodDisruptionBudget: NONE FOUND (kubectl get pdb returns empty)
  - AWS Node Termination Handler: NOT INSTALLED
  - terminationGracePeriodSeconds: 30s (default)
  - Multi-AZ: yes (3 AZs)
  - Stateful workloads: 2 Deployments use emptyDir for temp data

Pricing: On-Demand (no Savings Plan)
