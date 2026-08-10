# End-to-end usage scenario: cloudwatch-metrics-troubleshooter

A walkthrough showing the skill diagnosing a CloudWatch metric query
that returns empty because of a namespace mismatch. This exercises
Step 0 (signal capture), Step 1 (symptom categorisation), Step 2
(METRIC_NOT_APPEARING walk), the root-cause catalog, and the
remediation workflow.

## Input (user prompt)

> Our operator is looking for CPU utilization for the ECS service
> `api` on cluster `prod-app` in `us-east-1`. The dashboard cell is
> empty. They queried `AWS/EC2` `CPUUtilization` with dimensions
> `ClusterName=prod-app, ServiceName=api`. `list-metrics` on `AWS/EC2`
> for `CPUUtilization` returns only `InstanceId` dimensions. The same
> call on `AWS/ECS` returns the metric with `ClusterName=prod-app`
> and `ServiceName=api`. Container Insights is enabled and
> `runningCount: 12`.

## Skill output

```text
INCIDENT: AWS/EC2 / CPUUtilization / ClusterName=prod-app, ServiceName=api
 — metric not appearing for an ECS service
VERDICT: ROOT_CAUSE_FOUND
ROOT_CAUSE: METRIC_NOT_APPEARING — operator queried AWS/EC2 CPUUtilization
for an ECS service; the metric lives under AWS/ECS with dimensions
ClusterName + ServiceName. AWS/EC2 CPUUtilization is per-EC2-instance
(InstanceId dimension only) and has no concept of ECS service-level CPU.
EVIDENCE:
  - list-metrics --namespace AWS/EC2 --metric-name CPUUtilization:
    returns dimension InstanceId only (no ClusterName, no ServiceName)
  - list-metrics --namespace AWS/ECS --metric-name CPUUtilization:
    returns ClusterName=prod-app, ServiceName=api (metric exists in
    the correct namespace)
  - get-metric-statistics --namespace AWS/EC2 --dimensions
    ClusterName=prod-app, ServiceName=api: Datapoints [] (empty —
    these dimensions are not valid in AWS/EC2)
  - describe-cluster prod-app settings:
    [{"name":"containerInsights","value":"enabled"}]
  - describe-services prod-app/api: runningCount 12, desiredCount 12
ROOT_CAUSE_CATALOG: #1 (wrong namespace)
REMEDIATION:
  1. Update the dashboard / alarm query to use:
     Namespace: AWS/ECS
     MetricName: CPUUtilization
     Dimensions: ClusterName=prod-app, ServiceName=api
     Statistic: Average
     Period: 60
  2. Verify with:
     aws cloudwatch get-metric-statistics \
       --namespace AWS/ECS --metric-name CPUUtilization \
       --dimensions Name=ClusterName,Value=prod-app Name=ServiceName,Value=api \
       --start-time $(date -u -v-5M +%Y-%m-%dT%H:%M:%SZ) \
       --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
       --period 60 --statistics Average \
       --query 'Datapoints[*].{ts:Timestamp,avg:Average}'
     Expect: non-empty Datapoints with values in the expected range.
  3. If the AWS/ECS query is also empty, verify Container Insights is
     still enabled on the cluster (it can be disabled inadvertently)
     and that runningCount > 0. Container Insights emits per-minute,
     so allow 3-5 minutes for fresh data.
```

## What the skill caught that a generic assistant misses

1. **The `list-metrics`-before-`get-metric-statistics` discipline.**
   A generic assistant often stops at "the metric is missing." The
   skill runs `list-metrics` first to distinguish "metric does not
   exist" from "metric exists but the query is wrong" — and here the
   metric exists in a different namespace.

2. **The `AWS/EC2` vs `AWS/ECS` distinction for CPU metrics.** A
   generic assistant may suggest "the metric is broken, enable
   Container Insights" without verifying that Container Insights is
   already enabled and the issue is purely a namespace query error.

3. **The Container-Insights-fallback verification step.** The skill
   notes that if the corrected `AWS/ECS` query ALSO returns empty,
   the next probe is the cluster's Container Insights setting — a
   layered diagnosis, not a single-shot fix.

4. **The "per-EC2-instance vs per-ECS-service" semantic explanation.**
   A generic assistant often just gives the corrected query without
   explaining why. The skill documents that `AWS/EC2 CPUUtilization`
   measures the underlying host (or Fargate tenant) and has no
   visibility into per-service CPU — so the operator does not make
   the same mistake again on a different dashboard.

## Slash-command invocation

```
/aws:troubleshoot-cloudwatch-metrics
```

Or via the orchestrator:

```
/aws:pipeline
You: "ECS service api CPU dashboard is empty, operator queried AWS/EC2"
```

The orchestrator emits `[Phase: Troubleshoot | Skills routed:
cloudwatch-metrics-troubleshooter]` and hands off to this skill for
the VERDICT.

## Live-account diagnostic flow (requires AWS CLI)

When the operator has credentials for the account:

```bash
# Discover what dimensions actually exist for the metric:
aws cloudwatch list-metrics --namespace AWS/EC2 --metric-name CPUUtilization \
  --query 'Metrics[*].Dimensions' --output json

# Compare against the ECS namespace:
aws cloudwatch list-metrics --namespace AWS/ECS --metric-name CPUUtilization \
  --query 'Metrics[*].Dimensions' --output json

# Verify Container Insights is enabled:
aws ecs describe-cluster --cluster prod-app \
  --query 'clusters[0].settings[?name==`containerInsights`].value'

# Verify the cluster is active:
aws ecs describe-services --cluster prod-app --services api \
  --query 'services[0].{running:runningCount,desired:desiredCount}'

# Run the corrected query:
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS --metric-name CPUUtilization \
  --dimensions Name=ClusterName,Value=prod-app Name=ServiceName,Value=api \
  --start-time $(date -u -v-5M +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 --statistics Average \
  --query 'Datapoints[*].{ts:Timestamp,avg:Average}'
```

If the `list-metrics --namespace AWS/ECS` call returns the metric
with `ClusterName=prod-app, ServiceName=api` and the corrected
`get-metric-statistics` call returns non-empty Datapoints, the
diagnosis is confirmed without needing to read CloudTrail or any
emitter logs.
