# Eval prompt: cw-wrong-namespace-ecs-vs-ec2

Diagnose the following CloudWatch metric query failure. Walk the
METRIC_NOT_APPEARING decision tree and emit the standard VERDICT block
(INCIDENT, VERDICT, ROOT_CAUSE, EVIDENCE, ROOT_CAUSE_CATALOG,
REMEDIATION).

## Scenario

An operator is looking for CPU utilization for an ECS service named
`api` running on cluster `prod-app` in `us-east-1`.

## Known facts

- The operator's `get-metric-statistics` query:
  - Namespace: `AWS/EC2`
  - MetricName: `CPUUtilization`
  - Dimensions: `ClusterName=prod-app`, `ServiceName=api`
  - Period: 60
  - Statistic: Average
  - Window: last 15 minutes
  - Result: `Datapoints: []` (empty)
- `aws cloudwatch list-metrics --namespace AWS/EC2 --metric-name CPUUtilization`
  returns metrics with dimension `InstanceId` ONLY — no `ClusterName`
  and no `ServiceName` are returned.
- `aws cloudwatch list-metrics --namespace AWS/ECS --metric-name CPUUtilization`
  returns metrics with dimensions `ClusterName=prod-app` and
  `ServiceName=api` (among others).
- `aws ecs describe-cluster --cluster prod-app` shows
  `settings: [{name: containerInsights, value: enabled}]`.
- `aws ecs describe-services --cluster prod-app --services api` shows
  `runningCount: 12`, `desiredCount: 12`.

## Symptom

The dashboard cell for "ECS service api CPU" is empty. The operator
expects a non-empty time series.
