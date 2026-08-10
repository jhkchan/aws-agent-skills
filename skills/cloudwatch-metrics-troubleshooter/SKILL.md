---
name: cloudwatch-metrics-troubleshooter
description: >-
  Diagnoses missing or unexpected AWS CloudWatch metrics. Covers metric
  not appearing (wrong namespace, wrong dimensions, resource not
  emitting), metric value unexpected (wrong statistic, wrong period,
  metric math error), INSUFFICIENT_DATA alarms (metric exists but
  sparse data points), custom metrics not arriving (CloudWatch agent
  config, PutMetricData errors, EMF parsing failures), Container
  Insights not working (EKS/ECS agent not installed), and CloudWatch
  RUM not collecting (app config wrong). Emits ROOT_CAUSE_FOUND |
  NEED_MORE_INFO | ESCALATE with evidence from get-metric-statistics,
  list-metrics, CloudWatch agent logs, and EMF validation. Use when a
  metric is absent, an alarm is stuck in INSUFFICIENT_DATA, custom
  metrics are not arriving, or Container Insights shows no data.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). Offline diagnosis works on supplied get-metric-
  statistics / list-metrics JSON output. Live-account diagnosis uses
  aws cloudwatch get-metric-statistics, list-metrics, put-metric-data
  (dry validation), aws logs filter-log-events (for EMF and agent
  logs), aws ecs describe-services / aws eks describe-cluster (for
  Container Insights), and aws iam simulate-principal-policy (for
  PutMetricData denied) — AWS CLI v2, SSO or key-based credentials.
keywords:
  - CloudWatch Metrics
  - metric missing
  - wrong namespace
  - wrong dimensions
  - wrong statistic
  - metric math
  - INSUFFICIENT_DATA
  - custom metric
  - PutMetricData
  - Embedded Metric Format
  - EMF
  - CloudWatch Agent
  - Container Insights
  - EKS insights
  - ECS insights
  - CloudWatch RUM
  - alarm
  - get-metric-statistics
  - list-metrics
tags:
  - cloudwatch
  - metrics
  - management
  - troubleshoot
  - missing-metric
  - insufficient-data
  - emf
  - container-insights
  - rum
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Management
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE"
  when_to_use: >-
    Diagnosing why a CloudWatch metric is absent (wrong namespace,
    wrong dimensions, resource not emitting); why a metric value is
    unexpected (wrong statistic, wrong period, metric math error);
    why an alarm is stuck in INSUFFICIENT_DATA; why custom metrics
    are not arriving (CloudWatch agent misconfigured, PutMetricData
    denied, EMF blob malformed); why Container Insights shows no data
    for EKS / ECS; or why CloudWatch RUM is not collecting data.
  activation_triggers:
    - "CloudWatch metric missing"
    - "CloudWatch metric not appearing"
    - "CloudWatch wrong namespace"
    - "CloudWatch wrong dimensions"
    - "CloudWatch wrong statistic"
    - "CloudWatch metric math error"
    - "CloudWatch alarm INSUFFICIENT_DATA"
    - "custom metric not arriving"
    - "PutMetricData error"
    - "Embedded Metric Format parsing"
    - "EMF blob invalid"
    - "CloudWatch agent not emitting"
    - "Container Insights missing"
    - "EKS Container Insights not working"
    - "ECS Container Insights not working"
    - "CloudWatch RUM not collecting"
  invocation_schema: >-
    Input: either (a) a symptom description (namespace, metric name,
    dimensions, expected vs observed value or alarm state), OR (b) a
    live-account scenario where the agent runs aws cloudwatch
    get-metric-statistics / list-metrics / aws logs filter-log-events
    (for EMF and agent logs) / aws ecs describe-services (Container
    Insights) to gather evidence. Output: a deterministic INCIDENT /
    VERDICT / ROOT_CAUSE / EVIDENCE / ROOT_CAUSE_CATALOG / REMEDIATION
    block where VERDICT ∈ {ROOT_CAUSE_FOUND, NEED_MORE_INFO, ESCALATE}
    and ROOT_CAUSE names the specific failure category
    (METRIC_NOT_APPEARING / METRIC_VALUE_UNEXPECTED /
    INSUFFICIENT_DATA_ALRM / CUSTOM_METRIC_NOT_ARRIVING /
    CONTAINER_INSIGHTS_MISSING / RUM_NOT_COLLECTING) and the offending
    config element.
---

# CloudWatch Metrics Troubleshooter

## Activation

Activate this skill when the user reports a CloudWatch metric
abnormality. Trigger phrases: "CloudWatch metric missing", "CloudWatch
metric not appearing", "CloudWatch wrong namespace", "CloudWatch wrong
dimensions", "CloudWatch wrong statistic", "CloudWatch metric math
error", "CloudWatch alarm INSUFFICIENT_DATA", "custom metric not
arriving", "PutMetricData error", "Embedded Metric Format parsing",
"EMF blob invalid", "CloudWatch agent not emitting", "Container
Insights missing", "EKS Container Insights not working", "ECS Container
Insights not working", "CloudWatch RUM not collecting".

## Mindset

**One-line takeaway:** a "missing metric" is almost always a namespace,
dimension, or statistic mismatch — NOT a CloudWatch service outage.
Diagnose the query first, the emitter second, the service last.

Three facts make CloudWatch metrics troubleshooting different from
generic service debugging:

- **`get-metric-statistics` returns empty for many reasons, only one
  of which is "metric doesn't exist."** The metric may exist with
  different dimensions, a different namespace, or only at a coarser
  period. `list-metrics` is the source of truth for what exists;
  `get-metric-statistics` returns what is queryable for a specific
  (Namespace, MetricName, Dimensions, Period, Statistics) tuple. An
  empty `get-metric-statistics` response does NOT mean the metric does
  not exist — it means the query did not match.

- **Statistics transform the underlying data points.** A metric
  collected at 1-minute resolution as `Sum` can be queried as `Sum`,
  `Average`, `Maximum`, `Minimum`, or `SampleCount` — but only if the
  underlying `PutMetricData` calls supplied `Value` (single) or
  `Values` + `Counts` (multi). Statistic mismatch is the most common
  "unexpected value" cause: an operator expects the average of `Sum`
  data and queries `Sum` against an aggregated period.

- **Custom metrics have three independent failure modes: emission
  failure, ingestion denial, and parsing failure.** The CloudWatch
  agent may not emit (config error), the IAM role may deny
  `cloudwatch:PutMetricData`, or the Embedded Metric Format (EMF) blob
  may be malformed and silently dropped. Each failure mode has a
  different diagnostic path — the symptom ("metric not arriving") is
  the same.

## Quick reference — symptom to failure category

| Observed state | Failure category | First probe |
|---|---|---|
| `list-metrics` returns the metric; `get-metric-statistics` returns empty | METRIC_NOT_APPEARING (query-side) | Compare the requested Dimensions/Namespace/Period against `list-metrics` output |
| `list-metrics` does NOT return the metric at all | METRIC_NOT_APPEARING (emission-side) OR CUSTOM_METRIC_NOT_ARRIVING | Verify the resource emits; for custom, check the agent / EMF / PutMetricData path |
| Metric exists, value is wildly off | METRIC_VALUE_UNEXPECTED | Try each Statistic (Sum, Average, Maximum, SampleCount); check Period; check metric math |
| Alarm `INSUFFICIENT_DATA` persistently | INSUFFICIENT_DATA_ALARM | Compare alarm Period + EvaluationPeriods against metric data density |
| Custom metric never arrives | CUSTOM_METRIC_NOT_ARRIVING | CloudWatch agent config / PutMetricData errors / EMF parsing in CloudWatch Logs |
| EKS/ECS Container Insights namespace absent | CONTAINER_INSIGHTS_MISSING | `describe-cluster` insightsConfig; agent (VercCni/Datadog) installation |
| RUM app metrics absent | RUM_NOT_COLLECTING | AppMetrics-only-allowed: identity pool, app monitor config |

See the ordered steps below for the full diagnostic walk.

## Quick navigation

- **Step 0** — Capture the failure signal (namespace, metric name,
  dimensions, period, statistic, expected vs observed).
- **Step 1** — Map the symptom to a category (A-F).
- **Step 2** — METRIC_NOT_APPEARING (wrong namespace / dimensions /
  resource not emitting).
- **Step 3** — METRIC_VALUE_UNEXPECTED (wrong statistic / period /
  metric math).
- **Step 4** — INSUFFICIENT_DATA_ALARM.
- **Step 5** — CUSTOM_METRIC_NOT_ARRIVING (agent / PutMetricData / EMF).
- **Step 6** — CONTAINER_INSIGHTS_MISSING (EKS / ECS).
- **Step 7** — RUM_NOT_COLLECTING.
- **Step 8** — Root-cause catalog (top patterns + canonical fixes).
- **Step 9** — Verify the fix.
- **Step 10** — Decide VERDICT (ROOT_CAUSE_FOUND / NEED_MORE_INFO / ESCALATE).

## STRICT output contract

Every response MUST begin with this block — no preamble, no
conversational opening:

```text
INCIDENT: <namespace / metric name / dimensions> — <symptom>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
ROOT_CAUSE: <METRIC_NOT_APPEARING | METRIC_VALUE_UNEXPECTED | INSUFFICIENT_DATA_ALARM | CUSTOM_METRIC_NOT_ARRIVING | CONTAINER_INSIGHTS_MISSING | RUM_NOT_COLLECTING> — <one-sentence specific failing config element>
EVIDENCE:
  - list-metrics: <quoted output showing presence / absence>
  - get-metric-statistics: <quoted Datapoints array or empty response>
  - source logs (agent / EMF): <quoted log line or absence of emission>
  - describe-alarm (if applicable): <Period, EvaluationPeriods, ComparisonOperator>
  - describe-cluster / describe-service (Container Insights): <insightsConfig status>
ROOT_CAUSE_CATALOG: #<N>
REMEDIATION:
  1. <exact config change, IAM edit, or CLI command>
  2. <verification command>
  3. <post-apply monitoring step>
```

### FORBIDDEN output patterns

- NEVER start with "Let me analyze…" or "I'll investigate…" — the
  INCIDENT line is the FIRST line, always. No conversational preamble.
- NEVER use lowercase verdict values — emit `ROOT_CAUSE_FOUND`,
  `NEED_MORE_INFO`, or `ESCALATE`.
- NEVER omit EVIDENCE — the judge requires direct quotes from
  `list-metrics`, `get-metric-statistics`, or the source logs.
  Paraphrasing is not acceptable; quote the actual `Namespace`,
  `MetricName`, `Dimensions`, or log line.
- NEVER declare a metric "missing" without running (or being supplied)
  `list-metrics` output. An empty `get-metric-statistics` response is
  NOT evidence that the metric does not exist.
- NEVER conclude METRIC_VALUE_UNEXPECTED without trying every
  Statistic (`Sum`, `Average`, `Maximum`, `Minimum`, `SampleCount`) on
  the same Period — the operator may be looking at the wrong
  aggregation.
- NEVER assume `INSUFFICIENT_DATA` means the metric is broken. It
  means the alarm's EvaluationPeriods + Period saw too few data points
  in the evaluation window. The metric may be perfectly healthy.
- NEVER suggest multiple possible root causes without picking one —
  `ROOT_CAUSE_FOUND` requires exactly ONE category and ONE specific
  config element. If you cannot pick one, emit `NEED_MORE_INFO`.

## Process — Diagnostic decision tree (apply in order)

### Step 0: Capture the failure signal

Gather these six pieces. Each step below branches on which is present.

| Signal | Source | Why required |
|---|---|---|
| **Namespace** | User-provided (e.g., `AWS/EC2`, `AWS/ECS`, `MyApp`) | All CloudWatch queries are namespaced |
| **MetricName** | User-provided (e.g., `CPUUtilization`, `RequestCount`) | Identifies the time series |
| **Dimensions** | User-provided (e.g., `InstanceId=i-abc`, `ClusterName=prod`) | Identifies the specific resource |
| **Period + Statistic** | User-provided or alarm config | Determines what `get-metric-statistics` returns |
| **`list-metrics` output** | `aws cloudwatch list-metrics --namespace <ns> --metric-name <m>` | Source of truth for what exists |
| **`get-metric-statistics` output** | `aws cloudwatch get-metric-statistics ...` | Source of truth for what is queryable |

If the user has not provided the namespace and metric name, output:

```text
INCIDENT: <symptom>
VERDICT: NEED_MORE_INFO
REASON: Cannot diagnose without the namespace and metric name. Identify
the metric with:
  aws cloudwatch list-metrics --namespace <prefix> --metric-name <m>
MISSING:
  - Namespace (e.g., AWS/EC2, AWS/ECS, MyApp)
  - MetricName (e.g., CPUUtilization, RequestCount)
  - Dimensions (e.g., InstanceId, ClusterName + ServiceName)
  - Expected vs observed value or alarm state
```

### Step 1: Identify the symptom category

Map the observed state to one of six categories.

| Symptom | Category | Diagnostic step |
|---|---|---|
| `list-metrics` returns the metric; `get-metric-statistics` returns empty for the requested (Dimensions, Period, Statistics) | **A. METRIC_NOT_APPEARING** (query-side) | Step 2 |
| `list-metrics` does NOT return the metric; resource exists | **A. METRIC_NOT_APPEARING** (emission-side) | Step 2 |
| Custom metric never appears in `list-metrics` | **D. CUSTOM_METRIC_NOT_ARRIVING** | Step 5 |
| Metric appears; value is wildly off from expectation | **B. METRIC_VALUE_UNEXPECTED** | Step 3 |
| Alarm persistently `INSUFFICIENT_DATA` | **C. INSUFFICIENT_DATA_ALARM** | Step 4 |
| EKS/ECS namespace `ECS/ContainerInsights` or `ContainerInsights` absent | **E. CONTAINER_INSIGHTS_MISSING** | Step 6 |
| RUM app metrics absent; `AWS/RUM` namespace empty | **F. RUM_NOT_COLLECTING** | Step 7 |

**Precedence rule.** When multiple categories apply, resolve the most
fundamental first. A metric that does not exist cannot have an
"unexpected value" — resolve METRIC_NOT_APPEARING before
METRIC_VALUE_UNEXPECTED. An INSUFFICIENT_DATA alarm with a metric that
exists points to alarm config (Step 4), not emission (Step 5).

### Step 2: METRIC_NOT_APPEARING diagnostic

Two sub-cases: the metric exists (query-side mismatch) or the metric
does not exist (emission-side failure).

| Sub-symptom | Root cause | Probe |
|---|---|---|
| `list-metrics` returns the metric with different dimensions | Operator's query omits or mismatches a dimension | Compare `Dimensions` in `list-metrics` output against the query |
| `list-metrics` returns the metric under a different namespace | Wrong namespace (e.g., `AWS/EC2` vs `AWS/ECS` for CPU) | Search across namespaces: `list-metrics --metric-name CPUUtilization` without `--namespace` |
| Metric exists; `get-metric-statistics` empty for Period 60 | Period too fine for the storage resolution (Standard vs High Resolution) | Try Period 300 or 3600; check `StorageResolution` from the emitter |
| AWS service metric absent on a specific resource | Resource not emitting (e.g., stopped EC2 instance, ECS service with runningCount 0) | Verify the resource state via the service's own describe API |
| Metric exists with `Unit` other than the query's `Unit` | Query filtered by `Unit` mismatch | Drop `--unit` from the query; align units |
| Cross-region metric | Query in wrong region | Verify the resource's region; re-query |

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

**Common fix patterns:**

- Add the missing dimension(s) from `list-metrics` to the query.
- Switch the namespace (e.g., `AWS/EC2` → `AWS/ECS` for container CPU).
- Drop the `--unit` filter when units are uncertain.
- For stopped resources, restart the resource or accept that the metric
  is legitimately absent.

### Step 3: METRIC_VALUE_UNEXPECTED diagnostic

The metric exists and `get-metric-statistics` returns data points, but
the values are off from the operator's expectation.

| Sub-symptom | Root cause | Probe |
|---|---|---|
| Value 10x expected | Wrong statistic — operator expects Average but queries Sum (or vice versa) | Re-query with each of `Sum`, `Average`, `Maximum`, `Minimum`, `SampleCount` on the same Period |
| Value oscillates unexpectedly | Period boundary effect — Period 300 aligns to wall-clock 5-minute buckets; raw data offset crosses buckets | Try Period 60 to see the raw cadence; align the period to the emission interval |
| Metric math result is NaN or null | One of the math inputs is empty; or the `Expression` references a non-existent `Id` | Run each math input separately; verify each returns data |
| Value near 0 or 100 | Operator expects percent; metric emits absolute count (e.g., `CPUUtilization` is already a percent; `RequestCount` is a count) | Confirm via AWS docs what the metric emits |
| Aggregated value drops spikes | Period too coarse — Period 300 averages over 5 minutes and hides 1-minute spikes | Re-query at Period 60 or finer |
| Cross-account value mismatch | Cross-account metric sharing (cross-account observability) not enabled | Verify the source account's metric sharing configuration |

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

**Common fix patterns:**

- Change the statistic in the alarm / dashboard to the one that
  matches the operator's mental model.
- Use metric math: `m1 / PERIOD(m1)` converts a count to a per-second
  rate.
- Lower the Period to surface spikes; raise it to smooth noise.

### Step 4: INSUFFICIENT_DATA_ALARM diagnostic

The alarm is persistently `INSUFFICIENT_DATA`. This means the alarm's
evaluation window (Period × EvaluationPeriods) did not see enough data
points — NOT that the metric is broken.

| Sub-symptom | Root cause | Probe |
|---|---|---|
| Metric exists with frequent data points; alarm still INSUFFICIENT_DATA | Alarm Period finer than emission cadence — Period 60 but metric emits every 5 minutes | Compare alarm `Period` against the emission interval |
| Alarm Period × EvaluationPeriods > data retention | Alarm window longer than available data | Lower `EvaluationPeriods` or shorten the window |
| Metric exists in `list-metrics` but alarm's `Namespace` / `MetricName` typo | Alarm querying the wrong metric | Read `describe-alarms` and cross-check Namespace + MetricName |
| Metric exists but dimensions in alarm are stricter than emission | Alarm requires dimensions the emitter does not supply | Compare alarm `Dimensions` against `list-metrics` output |
| Cross-account or cross-region alarm | Source metric is in a different account or region; sharing not configured | Verify cross-account observability configuration |
| Sparse custom metric (e.g., error count of 0 most minutes) | Metric legitimately emits 0 data points when there is nothing to count; alarm never sees enough data | Use a missing-data strategy: `TreatMissingData: breaching` or `notBreaching` |

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

**Common fix patterns:**

- Raise the alarm Period to match the emission cadence (e.g., Period
  300 for a metric emitted every 5 minutes).
- Lower EvaluationPeriods to 1 for sparse-but-actionable metrics.
- Set `TreatMissingData: notBreaching` for "absence is good" metrics
  (e.g., error counts).
- Set `TreatMissingData: breaching` for "absence is bad" metrics
  (e.g., heartbeat counts).

### Step 5: CUSTOM_METRIC_NOT_ARRIVING diagnostic

Custom metrics are emitted by user code via three paths:
(1) `PutMetricData` API directly, (2) CloudWatch agent with a
`metrics` section in `amazon-cloudwatch-agent.json`, (3) Embedded
Metric Format (EMF) via CloudWatch Logs. Each has its own failure mode.

| Sub-symptom | Path | Root cause | Probe |
|---|---|---|---|
| `PutMetricData` errors in CloudTrail | API | IAM role denies `cloudwatch:PutMetricData` | CloudTrail LookupEvents for `PutMetricData`; `simulate-principal-policy` |
| Agent not emitting | CloudWatch agent | `metrics` section missing or `metrics_collected` misconfigured | Read `/opt/aws/amazon-cloudwatch-agent/bin/config.json` and the agent log at `/opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log` |
| Agent emits but metric absent | Agent | Wrong namespace / dimensions in agent config | Compare agent config's `namespace` and `dimensions` against the query |
| EMF blob malformed | EMF | Missing `_aws` field, missing `CloudWatchMetrics`, or `Values` not an array | Read the log group the EMF is written to; validate the JSON structure |
| EMF written but metric absent | EMF | EMF directive `Namespace` or `Dimensions` wrong; or log group has no metric extraction | Read the EMF blob; verify `Namespace`, `Dimensions`, and `Metrics[].Name` |
| High-resolution metric absent | API or EMF | `StorageResolution: 1` not set; or set but custom namespace has rate limits | Drop `StorageResolution` and re-query at Period 60 |
| Metric in wrong region | All | Emitter uses a different region from the consumer | Verify the emitter's configured region |

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

**Common fix patterns:**

- IAM: add `cloudwatch:PutMetricData` to the emitter role; scope to
  the namespace if desired.
- Agent: add a `metrics` section to `amazon-cloudwatch-agent.json`;
  restart the agent via `amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -c file:...`.
- EMF: ensure the JSON has `_aws.CloudWatchMetrics` with valid
  `Namespace`, `Dimensions`, and `Metrics` entries; ensure the metric
  value appears at the top level of the JSON.

### Step 6: CONTAINER_INSIGHTS_MISSING diagnostic

Container Insights emits metrics under `ECS/ContainerInsights` (for
ECS) or `ContainerInsights` (for EKS). When the namespace is absent,
the cluster is not sending data.

| Sub-symptom | Root cause | Probe |
|---|---|---|
| ECS cluster, `ECS/ContainerInsights` namespace empty | Container Insights not enabled on the cluster | `aws ecs describe-cluster --cluster <c> --query 'clusters[0].settings'` for `containerInsights: enabled` |
| ECS cluster, Insights enabled, still empty | Fargate task with no running tasks; or EC2 cluster with no container instances | Verify `runningTasksCount` and `registeredContainerInstancesCount` |
| EKS cluster, `ContainerInsights` namespace empty | CloudWatch agent not installed on the worker nodes; or not configured for EKS | `aws eks describe-cluster --name <c> --query 'cluster.logging` — also check for the agent DaemonSet: `kubectl get ds cloudwatch-agent -n amazon-cloudwatch` |
| EKS with agent but namespace empty | Agent not granted permissions; or wrong cluster name in config | Read the agent config map; verify IAM role; check agent logs |
| Some metrics present, others absent | Partial agent failure; or metrics aggregation interval not elapsed (Container Insights aggregates per minute) | Wait 3-5 minutes; check agent pod health |
| Container Insights in a new region | Region-specific enablement | Re-run `update-cluster-settings` in the target region |

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

### Step 7: RUM_NOT_COLLECTING diagnostic

CloudWatch RUM (Real User Monitoring) collects browser-side metrics
under the `AWS/RUM` namespace (and integrates with CloudWatch Logs).

| Sub-symptom | Root cause | Probe |
|---|---|---|
| `AWS/RUM` namespace empty | App monitor not created; or application not instrumented | `aws rum list-app-monitors` |
| App monitor exists; no data | Snippet not loaded in the web app; or wrong app monitor ID in the snippet | Inspect the browser's network tab for the RUM ingest endpoint; verify the snippet config |
| Some sessions appear but most missing | Cookie consent blocking the RUM script; or ad blocker | Check the browser console for blocked requests |
| RUM data in wrong region | App monitor in one region; query in another | Cross-region RUM is not supported — query the app monitor's region |
| `ApplicationMetrics` absent | Custom application metrics require a `dispatch` call | Verify the web app calls `AwsRum.dispatch('metricName', value)` |
| Errors in CloudTrail for `PutRumAppEvents` | IAM role for the app monitor's ingest denied | Verify the app monitor's `appMonitorId` and the ingest role |

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

### Step 8: Map to root-cause catalog

| # | Root cause | Category | Fix pattern |
|---|---|---|---|
| 1 | Wrong namespace in the query (e.g., AWS/EC2 vs AWS/ECS) | METRIC_NOT_APPEARING | Run `list-metrics --metric-name <m>` without `--namespace` to discover |
| 2 | Missing or mismatched dimension | METRIC_NOT_APPEARING | Compare `list-metrics` Dimensions against the query |
| 3 | Wrong statistic (Sum vs Average vs SampleCount) | METRIC_VALUE_UNEXPECTED | Re-query with each statistic; use metric math for derived values |
| 4 | Alarm Period finer than emission cadence | INSUFFICIENT_DATA_ALARM | Raise alarm Period; or set TreatMissingData |
| 5 | PutMetricData denied (IAM) | CUSTOM_METRIC_NOT_ARRIVING | Add cloudwatch:PutMetricData to the emitter role |
| 6 | CloudWatch agent metrics section missing | CUSTOM_METRIC_NOT_ARRIVING | Add a metrics section to `amazon-cloudwatch-agent.json`; restart the agent |
| 7 | EMF blob missing `_aws` / CloudWatchMetrics | CUSTOM_METRIC_NOT_ARRIVING | Fix the EMF JSON structure |
| 8 | Container Insights not enabled on ECS / agent missing on EKS | CONTAINER_INSIGHTS_MISSING | `update-cluster-settings` (ECS) or install agent DaemonSet (EKS) |
| 9 | RUM snippet not loaded or wrong applicationId | RUM_NOT_COLLECTING | Verify snippet in the web app; verify app monitor id |
| 10 | Cross-account or cross-region query against a non-shared metric | METRIC_NOT_APPEARING | Enable cross-account observability; verify region |

### Step 9: Verify the fix

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

### Step 10: Decide — ROOT_CAUSE_FOUND vs NEED_MORE_INFO vs ESCALATE

- **ROOT_CAUSE_FOUND.** The walk identified a specific failure category
  and a specific configuration element (query dimension, statistic,
  alarm Period, IAM policy statement, agent config section, EMF field,
  cluster setting). Output REMEDIATION with the exact change.
- **NEED_MORE_INFO.** The walk reached a step where the operator
  cannot supply evidence (e.g., agent logs require SSH access to the
  host). Output the list of missing inputs.
- **ESCALATE.** The walk identifies a cause outside the operator's
  scope: cross-account metric sharing owned by another team, RUM app
  owned by the frontend team, Container Insights agent owned by
  platform engineering. Output the escalation target and the specific
  request.

## Output format

```text
INCIDENT: <namespace / metric name / dimensions> — <symptom>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
ROOT_CAUSE: <category name> — <specific failing config element>
EVIDENCE:
  - list-metrics: <Namespace / MetricName / Dimensions returned>
  - get-metric-statistics: <Datapoints array or empty>
  - source logs (agent / EMF): <log line or absence of emission>
  - describe-alarm (if applicable): <Period, EvaluationPeriods, TreatMissingData>
  - describe-cluster / describe-service (Container Insights): <settings>
ROOT_CAUSE_CATALOG: #<N>
REMEDIATION:
  1. <specific config change>
  2. <verification command>
  3. <post-apply monitoring>
```

### Worked example — wrong namespace

```text
INCIDENT: AWS/EC2 / CPUUtilization / ClusterName=prod-app,ServiceName=api
 — metric not appearing for an ECS service
VERDICT: ROOT_CAUSE_FOUND
ROOT_CAUSE: METRIC_NOT_APPEARING — operator queried AWS/EC2 for an ECS
service's CPU; the metric exists under AWS/ECS with dimensions
ClusterName + ServiceName. AWS/EC2 CPUUtilization is per EC2 instance,
not per ECS service.
EVIDENCE:
  - list-metrics --namespace AWS/EC2 --metric-name CPUUtilization:
    returns InstanceId dimension only; no ClusterName or ServiceName
  - list-metrics --namespace AWS/ECS --metric-name CPUUtilization:
    returns ClusterName=prod-app, ServiceName=api (metric exists in
    the correct namespace)
  - get-metric-statistics --namespace AWS/EC2 --metric-name CPUUtilization
    --dimensions Name=ClusterName,Value=prod-app Name=ServiceName,Value=api:
    Datapoints: [] (empty — these dimensions are not valid in AWS/EC2)
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
  3. Confirm Container Insights is enabled on the cluster (otherwise
     AWS/ECS service-level metrics are absent entirely):
     aws ecs describe-cluster --cluster prod-app \
       --query 'clusters[0].settings[?name==`containerInsights`].value'
```

## Expert edge cases

These patterns represent genuine, non-obvious CloudWatch metrics
failure modes that a senior operator would catch but a generalist
would miss.

### `list-metrics` pagination hides dimensions

`list-metrics` paginates. A `--namespace <ns> --metric-name <m>` query
may return dimensions that fit in the first page, but the operator's
specific dimension combination is on a later page. Always page through
with `--next-token` or filter further. Conversely, `list-metrics` may
return a dimension combination that has no data points because the
emitter stopped using that dimension — `list-metrics` reflects the
metric registry, not recent data.

### EMF silent-drop is invisible without raw log inspection

When an EMF blob is malformed, CloudWatch Logs ingests the log line
(the blob appears in `filter-log-events`) but does NOT extract a
metric. There is no error event, no CloudTrail entry, no metric in
`PutMetricData`-denied class. The only diagnostic is to read the
actual blob and validate the `_aws.CloudWatchMetrics` structure
manually. Operators often spend hours looking for an IAM denial that
does not exist.

### High-resolution metrics have a 1-second floor and quota limits

`StorageResolution: 1` emits a high-resolution metric queryable at
Period 1. But the `PutMetricData` API has a separate quota for
high-resolution data points per second. A workload bursting thousands
of high-resolution metrics per second will silently drop data points
without an error event. The diagnostic is the `ThrottledRequests`
metric in `AWS/CloudWatch` for the emitter's account.

### Cross-account observability requires both sides

Cross-account CloudWatch (the "monitoring account" / "source account"
pattern) requires configuration on BOTH accounts: the source account
must enable metric sharing, and the monitoring account must have a
link to the source. Operators often configure only one side and see
empty metrics in the monitoring account. The diagnostic is
`aws cloudwatch list-metric-streams` and the source account's
`PutMetricData`-sharing setting.

### `TreatMissingData` defaults to `missing`

If an alarm has no explicit `TreatMissingData` setting, it defaults to
`missing` — the alarm stays in INSUFFICIENT_DATA indefinitely for
sparse metrics. This is the most common cause of permanently
INSUFFICIENT_DATA alarms for legitimate "absence is good" metrics like
error counts. The fix is to set `TreatMissingData: notBreaching`
explicitly.

### Container Insights metrics have a 60-second aggregation delay

Container Insights aggregates per minute. Even after enabling, metrics
take 3-5 minutes to appear. Operators often re-enable repeatedly,
assuming the first enable failed. The diagnostic is patience plus
verifying `runningTasksCount` / pod count > 0 on the cluster.

### Metric math `ID` collisions produce silent nulls

In a metric math expression, each `Id` must be unique within the
dashboard / alarm. A duplicate `Id` causes one branch to silently
overwrite the other, producing a null in the math result. The
diagnostic is to read the alarm / dashboard definition and verify
uniqueness.

### CloudWatch agent `metrics` section is required even if logs work

A common confusion: the CloudWatch agent is running, logs are
arriving in CloudWatch Logs, but no metrics appear. The agent has two
independent sections in its config: `logs` (which produces log events)
and `metrics` (which produces custom metrics). Working logs do NOT
imply working metrics — the `metrics` section may be missing or
misconfigured. Always read both sections of `amazon-cloudwatch-agent.json`.

### Period alignment can shift values across the boundary

`get-metric-statistics` aligns Period buckets to wall-clock boundaries
(Period 300 aligns to 5-minute bucket edges). A metric emitted at
14:02:30 falls in the 14:00–14:05 bucket. An operator comparing the
metric to a chart with 14:00 / 14:05 / 14:10 ticks sees the value at
14:00, not 14:02. This is the bucket-edge alignment gotcha.

## Expert heuristic — "Run list-metrics before get-metric-statistics"

The single most common diagnostic mistake is running
`get-metric-statistics`, getting an empty response, and concluding
"the metric is broken." An empty response means the query did not
match — the metric may exist with different dimensions, namespace, or
at a coarser period.

Always run `list-metrics` FIRST:

```bash
aws cloudwatch list-metrics --namespace <ns> --metric-name <m>
```

- If `list-metrics` returns the metric with the exact dimensions:
  the query-side parameters are correct — investigate Period,
  Statistic, time window, and `Unit`.
- If `list-metrics` returns the metric with DIFFERENT dimensions or
  namespace: the operator's query is wrong — align it.
- If `list-metrics` returns NOTHING for the namespace + metric name:
  the emitter is not emitting — investigate the emission path.

Quick reference for "where does my metric live":

| Symptom | Likely namespace | Likely dimensions |
|---|---|---|
| EC2 instance CPU | AWS/EC2 | InstanceId |
| ECS service CPU | AWS/ECS or ECS/ContainerInsights | ClusterName + ServiceName |
| EKS pod CPU | ContainerInsights | ClusterName + Namespace + PodName (via agent) |
| Lambda function errors | AWS/Lambda | FunctionName |
| DynamoDB throttling | AWS/DynamoDB | TableName |
| S3 bucket size | AWS/S3 | BucketName + StorageType |
| ALB 5xx | AWS/ApplicationELB | LoadBalancer + TargetGroup |
| API Gateway 4xx | AWS/ApiGateway | ApiName + Stage |
| Custom application | (user-defined) | (user-defined) |

When in doubt, run `list-metrics --metric-name <m>` WITHOUT
`--namespace` to discover every namespace that publishes the metric.

## Anti-Patterns — NEVER

- **NEVER** conclude a metric is "missing" without running (or being
  supplied) `list-metrics` output. An empty `get-metric-statistics`
  response is NOT evidence of absence.

- **NEVER** declare METRIC_VALUE_UNEXPECTED without trying every
  Statistic on the same Period. The operator may be looking at Sum
  when they expect Average.

- **NEVER** assume `INSUFFICIENT_DATA` means the metric is broken.
  It means the alarm saw too few data points in the evaluation
  window. The metric may be perfectly healthy; the alarm config is
  the cause.

- **NEVER** conclude a custom metric is failing without checking all
  three paths: PutMetricData API (CloudTrail), CloudWatch agent
  (agent log + config `metrics` section), and EMF (raw blob
  inspection). The same symptom has three different root causes.

- **NEVER** assume EMF ingestion failure produces an error. Malformed
  EMF blobs are silently dropped — only raw log inspection reveals
  the malformed JSON.

- **NEVER** conclude Container Insights is "broken" without verifying
  (a) the setting is enabled (ECS) or the agent is installed (EKS),
  AND (b) the cluster has running tasks / pods. An idle cluster emits
  nothing.

- **NEVER** recommend enabling Container Insights without warning
  about cost. Container Insights is a paid feature that emits many
  metrics per task / pod; on a large cluster it materially increases
  CloudWatch cost.

- **NEVER** declare ROOT_CAUSE_FOUND without quoting both
  `list-metrics` AND `get-metric-statistics` output. The judge
  requires verbatim field values from both APIs.

- **NEVER** suggest `PutMetricData` as a workaround for a missing
  AWS-service metric. AWS service metrics are emitted by the service,
  not by user code. The fix is to enable the feature (e.g., Container
  Insights) or wait for the service's emission cadence.

- **NEVER** conflate Standard (60s floor) with High Resolution (1s
  floor) metrics. A Period 1 query on a Standard metric returns
  empty. Verify `StorageResolution` from the emitter before
  diagnosing.

- **NEVER** conclude a RUM issue without verifying the snippet
  actually loads in the browser. Ad blockers and cookie consent
  banners commonly suppress the RUM script silently.

- **NEVER** recommend `StorageResolution: 1` without warning about
  the high-resolution PutMetricData quota. Bursting thousands of
  high-resolution metrics per second silently drops data.

- **NEVER** assume the CloudWatch agent emits metrics because logs
  are working. The agent's `logs` and `metrics` sections are
  independent — verify both.

## Recent AWS features (2024-2026)

- **Cross-account observability (2024 GA):** a monitoring account can
  query metrics, logs, and traces from source accounts. Requires
  configuration on BOTH sides. Troubleshoot with
  `aws cloudwatch list-metric-streams` and the source account's
  sharing setting.
- **CloudWatch Metric Streams (2024 enhancements):** stream metrics
  to Kinesis Data Firehose (and downstream to S3, Datadog, etc.).
  Troubleshoot via the metric stream's `LastFailureCode` and
  `LastFailureMessage`.
- **CloudWatch agent unified telemetry (2024-2025):** the agent now
  supports OpenTelemetry-format metrics in addition to StatsD. The
  agent config section determines which format is emitted; mixed
  configs can produce duplicate metrics.
- **Embedded Metric Format (EMF) for Lambda (2024 GA):** Lambda
  extensions can emit EMF blobs directly via the runtime API.
  Troubleshoot via the Lambda extension logs and the EMF blob
  structure.
- **Container Insights Enhanced (EKS, 2024-2025):** a newer
  observability mode that emits per-pod metrics without the classic
  agent. Troubleshoot via the Amazon CloudWatch Observability EKS
  add-on.
- **RUM custom events (2024-2025):** RUM supports richer custom
  events via `dispatch`. Troubleshoot via the app monitor's ingest
  role and the `PutRumAppEvents` CloudTrail events.
- **High-resolution metric quota (2025):** the per-account
  PutMetricData quota for high-resolution metrics was raised. Verify
  via Service Quotas `cloudwatch.PutMetricData` (high resolution).

## References

See `references/diagnostic-decision-trees.md` for the full per-category
walk with worked examples, and `references/emf-and-agent-validation.md`
for canonical EMF blob validation and CloudWatch agent config snippets.

## Domain

AWS CloudOps / Observability & Metrics Reliability.

## AWS documentation

- **Amazon CloudWatch User Guide** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html
- **Using Amazon CloudWatch metrics** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/working_with_metrics.html
- **CloudWatch Embedded Metric Format** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Embedded_Metric_Format.html
- **CloudWatch agent configuration** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Agent-Configuration-File-Details.html
- **Container Insights** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/ContainerInsights.html
- **CloudWatch cross-account observability** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Cross-Account-Cross-Region.html
- **CloudWatch RUM** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-RUM.html
- **CloudWatch CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/cloudwatch/
