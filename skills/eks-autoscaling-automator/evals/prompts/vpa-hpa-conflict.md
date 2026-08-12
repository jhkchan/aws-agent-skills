# Eval prompt: vpa-hpa-conflict

Design pod autoscaling for the following workload. The user wants to
run HPA on CPU and VPA on CPU simultaneously. Emit the standard
AUTOSCALING block and explain the conflict and recommended resolution.

Design reference: vpa-hpa-conflict
Account: 111111111111
Region: us-east-1

Cluster: prod-cluster, EKS 1.30
Workload: data-processor (Deployment, 5 replicas)
Desired HPA: CPU utilization 70%, min=3, max=20
Desired VPA: Auto mode, controls CPU and memory
metrics-server: installed
