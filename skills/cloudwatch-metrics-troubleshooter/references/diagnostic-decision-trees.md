# CloudWatch metrics diagnostic decision trees

On-demand reference for the `cloudwatch-metrics-troubleshooter` skill.
Loaded when the skill needs the full per-category walk with worked
examples. The SKILL.md contains the summary table; this file expands
each category with verbatim command output, the diagnostic walk, and
the canonical fix.

## How to use this file

1. Identify the failure category from the SKILL.md Quick Reference.
2. Jump to the matching section below.
3. Follow the walk; cross-reference evidence with the worked example.

---

## A. METRIC_NOT_APPEARING — wrong namespace / dimensions

### Signature

- `list-metrics --namespace <ns> --metric-name <m>` returns metric
  with DIFFERENT dimensions or namespace than the operator's query.
- `get-metric-statistics` returns empty `Datapoints`.

### Decision tree

1. **Run `list-metrics` without `--namespace`** to discover every
   namespace that publishes the metric.
2. **Compare dimensions** in the returned output against the operator's
   query. A metric with dimensions `ClusterName + ServiceName` cannot
   be queried with only `ClusterName`.
3. **Verify the resource exists** in the expected state. A stopped EC2
   instance emits no `CPUUtilization`. An ECS service with
   `desiredCount: 0` emits no service-level metrics.
4. **Verify the region.** Cross-region queries return empty unless
   cross-region sharing is configured.

### Top sub-causes

| Sub-cause | Fix |
|---|---|
| Wrong namespace (AWS/EC2 vs AWS/ECS) | Use the correct namespace for the resource type |
| Missing dimension | Add all dimensions from `list-metrics` output |
| Period too fine for storage resolution | Use Period 60 (Standard) or Period 1 (High Resolution) |
| Resource idle or stopped | Restart the resource; accept legitimate absence |
| Cross-region / cross-account | Re-query in the correct region; enable cross-account observability |
| `--unit` filter mismatch | Drop `--unit`; align units if needed |

### Worked example

See SKILL.md "Worked example — wrong namespace".

---

## B. METRIC_VALUE_UNEXPECTED — wrong statistic / period / math

### Signature

- Metric exists; `get-metric-statistics` returns non-empty `Datapoints`.
- Values are off from operator expectation (typically 10x or 100x).

### Decision tree

1. **Try every Statistic** on the same (Namespace, MetricName,
   Dimensions, Period):
   ```bash
   for stat in Sum Average Maximum Minimum SampleCount; do
     echo "=== $stat ==="
     aws cloudwatch get-metric-statistics --namespace <ns> \
       --metric-name <m> --dimensions <dims> \
       --start-time <iso> --end-time <iso> --period <p> \
       --statistics $stat --query 'Datapoints[*].{ts:Timestamp,value:'$stat'}'
   done
   ```
2. **Compare Period alignment.** Period 300 buckets to wall-clock
   5-minute boundaries. Period 60 to 1-minute boundaries.
3. **Inspect metric math.** Each `Id` in the math definition must
   return data; a null input produces null output.

### Top sub-causes

| Sub-cause | Fix |
|---|---|
| Operator expects Average; queries Sum | Change statistic to Average |
| Operator expects rate; queries count | Use metric math: `m1 / PERIOD(m1)` |
| Period too coarse; averages out spikes | Lower Period to 60 or finer |
| Period too fine; sparse data | Raise Period to match emission cadence |
| Metric math Id collision | Rename duplicate Ids |
| Cross-account math input empty | Enable cross-account observability |

---

## C. INSUFFICIENT_DATA_ALARM

### Signature

- Alarm state: `INSUFFICIENT_DATA` persistently.
- The metric may be perfectly healthy.

### Decision tree

1. **Read the alarm config:**
   ```bash
   aws cloudwatch describe-alarms --alarm-names <alarm> \
     --query 'MetricAlarms[0].{Namespace:Namespace,MetricName:MetricName,Dimensions:Dimensions,Period:Period,EvaluationPeriods:EvaluationPeriods,Statistic:Statistic,TreatMissingData:TreatMissingData}'
   ```
2. **Re-run `get-metric-statistics` with the alarm's exact parameters
   over the last 3 × EvaluationPeriods windows.**
3. **Compare data point count against EvaluationPeriods.** If below,
  the alarm correctly reports INSUFFICIENT_DATA.
4. **For sparse metrics**, set `TreatMissingData: notBreaching` or
   `breaching` per semantics.

### TreatMissingData semantics

| Value | Behavior on missing data |
|---|---|
| `missing` (default) | Alarm stays INSUFFICIENT_DATA |
| `notBreaching` | Missing treated as non-breaching (good for "absence is good" metrics like errors) |
| `breaching` | Missing treated as breaching (good for "absence is bad" metrics like heartbeats) |
| `ignore` | Alarm retains current state |

---

## D. CUSTOM_METRIC_NOT_ARRIVING

### Three independent emission paths

| Path | How it emits | How it fails |
|---|---|---|
| `PutMetricData` API | Direct API call from user code | IAM denies; quota exceeded; wrong region |
| CloudWatch agent | Reads system / app stats per `metrics` config | Config missing `metrics` section; agent not running; IAM denies |
| Embedded Metric Format (EMF) | JSON blob in CloudWatch Logs | Malformed JSON; missing `_aws` field; wrong log group |

### Decision tree

1. **Identify the path.** Read the emitter's code or agent config.
2. **For PutMetricData:** check CloudTrail for `PutMetricData` events.
3. **For the agent:** read `/opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log`.
4. **For EMF:** read the EMF log group directly.

---

## E. CONTAINER_INSIGHTS_MISSING

### ECS

1. **Verify enabled:**
   ```bash
   aws ecs describe-cluster --cluster <name> \
     --query 'clusters[0].settings[?name==`containerInsights`].value'
   ```
2. **Verify cluster activity:** `runningTasksCount > 0` or
   `registeredContainerInstancesCount > 0`.
3. **If newly enabled:** wait 3-5 minutes.

### EKS

1. **Verify agent DaemonSet:**
   ```bash
   kubectl get ds -n amazon-cloudwatch
   kubectl get pods -n amazon-cloudwatch
   ```
2. **Verify agent config map:**
   ```bash
   kubectl get cm cloudwatch-agent-config -n amazon-cloudwatch -o yaml
   ```
3. **Verify agent IAM role** (IRSA or instance role).

### Worked example — ECS Container Insights not enabled

```text
INCIDENT: ECS/ContainerInsights / CPUUtilization / ClusterName=prod-app,
ServiceName=api — no Container Insights metrics for ECS service
VERDICT: ROOT_CAUSE_FOUND
ROOT_CAUSE: CONTAINER_INSIGHTS_MISSING — Container Insights is not
enabled on cluster prod-app. The settings array does not include
containerInsights: enabled.
EVIDENCE:
  - list-metrics --namespace ECS/ContainerInsights: empty (no metrics
    in this namespace)
  - describe-cluster prod-app settings:
    [{"name":"containerInsights","value":"disabled"}]
  - describe-services prod-app/api: runningCount 12, desiredCount 12
    (cluster is active and would emit if Insights were enabled)
ROOT_CAUSE_CATALOG: #8 (Container Insights not enabled on ECS)
REMEDIATION:
  1. Enable Container Insights on the cluster:
     aws ecs update-cluster-settings --cluster prod-app \
       --settings name=containerInsights,value=enabled
  2. Wait 3-5 minutes, then verify:
     aws cloudwatch list-metrics --namespace ECS/ContainerInsights \
       --metric-name CPUUtilization \
       --dimensions Name=ClusterName,Value=prod-app Name=ServiceName,Value=api
     Expect: non-empty list.
  3. Note: Container Insights is a paid feature — confirm cost impact
     with the cluster owner before enabling on large production clusters.
```

---

## F. RUM_NOT_COLLECTING

### Decision tree

1. **List app monitors:**
   ```bash
   aws rum list-app-monitors --query 'AppMonitorSummaries[*].{name:Name,id:Id,state:State}'
   ```
2. **Verify the web app loads the snippet** with the correct
   `applicationId` and region.
3. **Verify the browser console** for blocked requests.
4. **For custom application metrics**, verify `dispatch` calls.

### Top sub-causes

| Sub-cause | Fix |
|---|---|
| App monitor not created | Create via `aws rum create-app-monitor` |
| Snippet missing or wrong applicationId | Add the snippet to the web app's HTML |
| Cookie consent blocking | Whitelist the RUM ingest endpoint |
| Ad blocker | Document the limitation; sample for bias |
| Wrong region | Re-create or query in the app monitor's region |
| Custom metric not dispatched | Add `AwsRum.dispatch(...)` calls |
| IAM role for ingest denied | Verify `PutRumAppEvents` permission |

---

## Common gotchas across categories

### `list-metrics` pagination

`list-metrics` paginates. The first page may not include the specific
dimension combination the operator needs. Always use `--next-token`
or broaden / narrowen the filter.

### Metric registry vs. recent data

`list-metrics` reflects the metric registry — every dimension
combination the emitter has ever used (up to ~14 days of inactivity
before pruning). A metric returned by `list-metrics` may have NO
recent data points. Always cross-reference with `get-metric-statistics`.

### High-resolution metric quota

`PutMetricData` for `StorageResolution: 1` metrics has a separate,
lower quota per second. Bursts silently drop data. The diagnostic is
the `ThrottledRequests` metric in `AWS/CloudWatch` for the emitter's
account.

### Period boundary alignment

`get-metric-statistics` aligns Period buckets to wall-clock edges
(Period 300 → 5-minute boundaries). A metric emitted at 14:02:30
lands in the 14:00–14:05 bucket, reported at timestamp 14:00.
