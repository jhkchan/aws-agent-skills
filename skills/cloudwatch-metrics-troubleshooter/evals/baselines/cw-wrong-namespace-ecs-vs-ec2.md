# Baseline (no-skill) response: cw-wrong-namespace-ecs-vs-ec2

This file captures what a generic assistant produces WITHOUT the
cloudwatch-metrics-troubleshooter skill loaded — the contrast that
proves the skill adds structure (deterministic VERDICT, category-aware
walk, specific remediation).

---

Your CloudWatch query is returning empty because you're querying the
wrong namespace. AWS/EC2 CPUUtilization is for individual EC2
instances and uses `InstanceId` as the dimension, not ClusterName or
ServiceName.

For an ECS service, you should query the `AWS/ECS` namespace with
`ClusterName` and `ServiceName` dimensions. You'll also need Container
Insights enabled on the cluster to get service-level CPU metrics.

Try this query instead:
- Namespace: AWS/ECS
- MetricName: CPUUtilization
- Dimensions: ClusterName=prod-app, ServiceName=api
- Statistic: Average
