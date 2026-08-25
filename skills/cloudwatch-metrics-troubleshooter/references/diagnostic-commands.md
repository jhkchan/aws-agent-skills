# Diagnostic Commands (load on demand) — CloudWatch Metrics Troubleshooter

Per-step diagnostic walks and fix-verification probes moved verbatim from SKILL.md. The sub-symptom tables, fix patterns, and verdict rules remain in SKILL.md.


---

## Step 2 — METRIC_NOT_APPEARING diagnostic walk (moved from SKILL.md)

**Diagnostic walk:**

1. **Run `list-metrics` for the namespace + metric name:**
   ```bash
   aws cloudwatch list-metrics --namespace <ns> --metric-name <m>
   ```
   If empty, broaden: drop `--namespace`, then drop `--metric-name`,
   to discover the actual namespace or name.
2. **Compare the returned dimensions** against the operator's query.
   A common mismatch: `list-metrics` returns `ClusterName + ServiceName`
   for `ECS/ContainerInsights` CPUUtilization, but the operator queried
   with only `ClusterName`.
3. **Verify the resource exists and is in a state that emits.** A
   stopped EC2 instance emits no `CPUUtilization`. An ECS service with
   `desiredCount: 0` emits no service-level metrics.
4. **For storage resolution:** high-resolution metrics
   (`StorageResolution: 1`) are queryable at Period 1; standard metrics
   are queryable at Period 60 or higher. A Period-1 query on a standard
   metric returns empty.

---

## Step 3 — METRIC_VALUE_UNEXPECTED diagnostic walk (moved from SKILL.md)

**Diagnostic walk:**

1. **Try every statistic** on the same (Namespace, MetricName,
   Dimensions, Period):
   ```bash
   for stat in Sum Average Maximum Minimum SampleCount; do
     aws cloudwatch get-metric-statistics --namespace <ns> \
       --metric-name <m> --dimensions <dims> \
       --start-time <iso> --end-time <iso> --period <p> \
       --statistics $stat --query 'Datapoints[*].{ts:Timestamp,value:'$stat'}'
   done
   ```
2. **Inspect the metric math definition** (if used). Each `Id` in the
   `metrics` array must return data; an empty input produces null.
3. **Verify the expected value's source.** A common mismatch: the
   operator expects the "request rate" but is looking at `RequestCount`
   (a count) without dividing by the Period in seconds.

---

## Step 4 — INSUFFICIENT_DATA_ALARM diagnostic walk (moved from SKILL.md)

**Diagnostic walk:**

1. **Read `describe-alarms` for the alarm config:**
   ```bash
   aws cloudwatch describe-alarms --alarm-names <alarm> \
     --query 'MetricAlarms[0].{Namespace:Namespace,MetricName:MetricName,Dimensions:Dimensions,Period:Period,EvaluationPeriods:EvaluationPeriods,Statistic:Statistic,ComparisonOperator:ComparisonOperator,Threshold:Threshold,TreatMissingData:TreatMissingData}'
   ```
2. **Re-run `get-metric-statistics` with the alarm's exact
   (Namespace, MetricName, Dimensions, Period, Statistics) over the
   last 3 × EvaluationPeriods windows.**
3. **Compare data point count against EvaluationPeriods.** If the
  count is below EvaluationPeriods in any window, the alarm correctly
  reports INSUFFICIENT_DATA — the fix is alarm config, not the metric.
4. **For sparse metrics (error rates, rare events):** set
   `TreatMissingData: notBreaching` (or `breaching`, depending on
   semantics) so the alarm treats absent data as "not breaching"
   instead of INSUFFICIENT_DATA.

---

## Step 5 — CUSTOM_METRIC_NOT_ARRIVING diagnostic walk (PutMetricData / agent / EMF) (moved from SKILL.md)

**Diagnostic walk:**

1. **Identify the emission path** (PutMetricData / agent / EMF).
2. **For PutMetricData:**
   ```bash
   aws cloudtrail lookup-events --lookup-attributes AttributeKey=EventName,AttributeValue=PutMetricData \
     --start-time <iso> --end-time <iso>
   ```
   Look for `errorCode: "AccessDenied"` or validate the request
   parameters.
3. **For the CloudWatch agent:** read the agent log
   `/opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log`
   on the host. Look for errors like "Failed to send metric data" or
   "AccessDeniedException". Verify the agent config has a `metrics`
   section.
4. **For EMF:** locate the log group where EMF blobs are written.
   Filter for the application's logs and inspect the JSON structure:
   ```bash
   aws logs filter-log-events \
     --log-group-name <emf-log-group> \
     --filter-pattern '{ $.LogGroup = "<emf-log-group>" }' \
     --start-time <epoch-ms> --limit 10
   ```
   A valid EMF blob has:
   ```json
   {
     "_aws": {
       "CloudWatchMetrics": [
         { "Namespace": "MyApp", "Dimensions": [["InstanceId"]], "Metrics": [{"Name": "Latency"}] }
       ],
       "Timestamp": <epoch-ms>
     },
     "InstanceId": "i-abc",
     "Latency": 42
   }
   ```
   Missing `_aws`, `CloudWatchMetrics`, `Dimensions`, or `Metrics`
   invalidates the blob — CloudWatch Logs silently drops the metric
   extraction while still ingesting the log line.

---

## Step 6 — CONTAINER_INSIGHTS_MISSING diagnostic walk (ECS / EKS) (moved from SKILL.md)

**Diagnostic walk:**

1. **For ECS:** verify Container Insights is enabled:
   ```bash
   aws ecs describe-cluster --cluster <name> \
     --query 'clusters[0].settings[?name==`containerInsights`].value'
   ```
   If not `enabled`, enable it:
   ```bash
   aws ecs update-cluster-settings --cluster <name> \
     --settings name=containerInsights,value=enabled
   ```
   New metrics take 3-5 minutes to appear.
2. **For EKS:** verify the agent is installed:
   ```bash
   kubectl get ds -n amazon-cloudwatch
   kubectl get pods -n amazon-cloudwatch
   ```
   If absent, install the CloudWatch agent DaemonSet and the
   `kiam` / IRSA role for the agent.
3. **For EKS with agent present:** read the agent config map and the
   agent logs:
   ```bash
   kubectl get cm cloudwatch-agent-config -n amazon-cloudwatch -o yaml
   kubectl logs -n amazon-cloudwatch -l app=cloudwatch-agent --tail=100
   ```
4. **Verify cluster activity:** an idle cluster with zero running
   tasks / pods emits no Container Insights metrics even when correctly
   configured.

---

## Step 7 — RUM_NOT_COLLECTING diagnostic walk (moved from SKILL.md)

**Diagnostic walk:**

1. **List app monitors:**
   ```bash
   aws rum list-app-monitors --query 'AppMonitorSummaries[*].{name:Name,id:Id,state:State}'
   ```
2. **Verify the web app includes the RUM snippet** with the correct
   `applicationId` and region.
3. **Verify the browser console** for blocked requests or JS errors in
   the RUM snippet loader.
4. **For custom application metrics**, verify the `dispatch` call.

---

## Step 9 — Verify the fix (validation probes per fix class) (moved from SKILL.md)

Before applying, validate the proposed fix with one of:

- **For query fixes (namespace, dimension, statistic):** re-run
  `get-metric-statistics` with the corrected parameters and confirm
  non-empty datapoints.
- **For IAM fixes:** re-run `aws iam simulate-principal-policy` with
  the updated policy source; expect `allowed`.
- **For alarm config fixes:** call `describe-alarms` after the update
  to confirm Period / EvaluationPeriods / TreatMissingData reflect the
  new values; monitor the alarm state over 2-3 evaluation windows.
- **For Container Insights enablement:** wait 3-5 minutes, then re-run
  `list-metrics --namespace ECS/ContainerInsights` (or `ContainerInsights`
  for EKS).
