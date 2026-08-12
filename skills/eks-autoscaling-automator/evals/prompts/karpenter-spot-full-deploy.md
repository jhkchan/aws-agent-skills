# Eval prompt: karpenter-spot-full-deploy

Design a complete EKS autoscaling system for the following production
cluster. Emit the standard AUTOSCALING block (TOOLING, PROVISIONING,
POD_SCALING, SPOT, SAFETY, VERDICT, TEMPLATE).

Design reference: karpenter-spot-full-deploy
Account: 111111111111
Region: us-east-1

Cluster: my-prod-cluster, EKS 1.30, 25 nodes
Current autoscaler: none (greenfield Karpenter)
metrics-server: installed and healthy
Prometheus Adapter: installed, custom metrics available
Workloads:
  - api-server (Deployment, 5 replicas, CPU + http_requests_per_second)
  - sqs-consumer (Deployment, 3 replicas, scales on SQS queue depth)
Spot ratio target: 70% spot, 30% on-demand
Instance diversification: c5, m5, c6i, m6i (4 families)
Disruption budget: 20% max, freeze during business hours
Overprovisioning: 10 pause-pods x 1 CPU/1Gi headroom
PDB: api-server minAvailable=2
Descheduler: enabled (LowNodeUtilization, max 3 evictions/node)
