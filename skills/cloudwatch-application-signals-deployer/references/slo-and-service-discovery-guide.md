# SLO and Service Discovery Guide — Application Signals Deployer

Deep reference on ServiceLevelObjective internals (period-based vs
request-based SLI), service discovery internals, burn-rate math, the
full NEVER list, and edge-case handling.

## SLI types — PeriodBased vs RequestBased

CloudWatch Application Signals SLOs support two evaluation types:

### PeriodBased SLO (most common)

- **Use for:** rate-style SLIs (uptime, ratio of good requests, latency
  percentile attainment).
- **Evaluation:** the goal is evaluated on a fixed time interval
  (rolling or calendar). Each interval contributes a "data point" toward
  the attainment.
- **Metric:** a single `MetricStat` defining what counts as "good".

```yaml
EvaluationType: PeriodBased
Goal:
  Interval:
    RollingInterval:
      DurationUnit: DAY
      Duration: 28
    BurnRates:
      - RollupInterval: MINUTE
      - RollupInterval: HOUR
  AttainmentGoal: 0.999
  WarningThreshold: 0.995
RequestBasedSliConfig:
  MetricThreshold: 0.25
  GoodRequestsMetric: { ... }
```

### RequestBased SLO

- **Use for:** SLIs expressed as a fraction of requests meeting a
  criterion (e.g., 99.9% of requests succeed).
- **Evaluation:** each request contributes to attainment. The SLO
  numerator / denominator are `GoodRequestsMetric` and
  `TotalRequestsMetric`.
- **More accurate than PeriodBased** for low-traffic services — a single
  failed request in 100 produces 99% attainment (vs PeriodBased which
  marks the entire minute as "bad").

```yaml
EvaluationType: PeriodBased  # RequestBased is expressed via RequestBasedSliConfig
RequestBasedSliConfig:
  MetricThreshold: 200  # success = HTTP status < 200... no, see below
  GoodRequestsMetric: { ... }
  TotalRequestsMetric: { ... }
```

**`MetricThreshold` semantics:** for availability SLOs, `MetricThreshold`
is the maximum HTTP status code considered "good" (e.g., `200` means
2xx/3xx are good, 4xx and 5xx are faults). For latency SLOs,
`MetricThreshold` is the maximum acceptable latency in seconds (e.g.,
`0.25` = 250ms).

## SLO Goal structure

```yaml
Goal:
  Interval:
    RollingInterval:
      DurationUnit: DAY | HOUR | MINUTE
      Duration: <integer>
    CalendarInterval:
      StartAt: <RFC3339 timestamp>
      DurationUnit: MONTH | WEEK | DAY
      Duration: <integer>
    BurnRates:
      - RollupInterval: MINUTE | HOUR | DAY
      - RollupInterval: MINUTE | HOUR | DAY
  AttainmentGoal: 0.<precision>     # e.g., 0.999 for 99.9%
  WarningThreshold: 0.<precision>   # must be > AttainmentGoal
```

- **AttainmentGoal** is a float 0-1. Three nines = 0.999; four nines =
  0.9999.
- **WarningThreshold** must be greater than `AttainmentGoal` (it's the
  "fall below this and you'll breach soon" line, expressed as remaining
  budget). Common warning = 1.5x the burn rate of `AttainmentGoal`.
- **RollingInterval** vs **CalendarInterval:** rolling is the right
  default for most SLOs. Calendar intervals are for monthly/quarterly
  compliance reporting (e.g., SRE team reports monthly attainment).

## Burn-rate math

The SLO `BurnRates` array publishes derived `BurnRate` metrics in the
`AWS/ApplicationSignals` namespace. The burn rate is:

```
burn_rate = (consumed_budget_in_window) / (total_budget_for_window)
```

Where consumed budget = `1 - (observed_attainment / target_attainment)`
over the window. A burn rate of 1.0 means you're consuming budget at
exactly the rate that breaches the SLO over the full period. A burn
rate of 14.4x means you'll exhaust the budget in 1/14.4 of the period
(for a 28-day SLO, that's ~46 hours; on a 5-minute window, that's
~21 seconds — fast enough to page before users notice).

### Multi-window thresholds (industry standard)

| Window | Threshold | Action | Budget consumed |
|---|---|---|---|
| 5 min | 14.4x | Page (high urgency) | 2% of total budget in 5 min |
| 1 hour | 6x | Page (high urgency) | 10% of total budget in 1 hour |
| 6 hours | 3x | Ticket (low urgency) | 10% of total budget in 6 hours |
| 1 day | 1x | Ticket (low urgency) | budget on track to drain |

These thresholds come from the Google SRE Workbook (Chapter 5). They
assume a 30-day SLO window; for a 7-day SLO, halve the thresholds
(e.g., 5-min at 7.2x).

### Wiring to CloudWatch alarms

The `BurnRate` metric has dimensions `SLOId` and `RollupInterval`. The
alarm period must match the SLO's `RollupInterval`:

```bash
# Fast burn — 5-minute window
aws cloudwatch put-metric-alarm \
  --alarm-name payments-api-slo-burn-fast \
  --namespace AWS/ApplicationSignals \
  --metric-name BurnRate \
  --dimensions Name=SLOId,Value=${SLO_ID} Name=RollupInterval,Value=MINUTE \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 14.4 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions <sns-page-topic>
```

**Critical:** set `--treat-missing-data noData` so missing RED metrics
during deployments do not trigger false pages.

## Service discovery internals

Application Signals builds the service map from three sources, in order
of precedence:

1. **Trace-derived (default).** Each X-Ray trace carries the
   `service.name` OTel resource attribute (set via
   `OTEL_RESOURCE_ATTRIBUTES` or `AWS_SERVICE_NAME`). Application
   Signals creates a node for each unique `service.name +
   environment` tuple. Edges are derived from trace parent-child
   relationships (the calling service's trace is the parent; the
   called service's trace is the child).
2. **CloudMap enrichment.** When a trace references a CloudMap service
   (the trace's `http.url` resolves to a CloudMap service DNS name,
   or the OTel Kubernetes attributes processor adds the CloudMap
   service ID), Application Signals joins on `service.name` and
   surfaces the CloudMap namespace in the service detail page.
3. **Kubernetes service enrichment.** The OTel Operator's
   `k8sattributes` processor adds `k8s.pod.name`,
   `k8s.namespace.name`, `k8s.deployment.name`, and
   `k8s.service.name` to trace resources. Application Signals
   displays these in the service detail page but does NOT key nodes
   on them — the key is still `AWS_SERVICE_NAME`.

### Discovery timing

- First trace to first service map node: **~5-10 minutes** (Application
  Signals processes traces in batches).
- Topology updates (new downstream dependencies): **~15-30 minutes**
  after the first cross-service trace.
- Service deletion from map: **stale nodes are removed after 30 days
  of no traces.**

### Cross-Region and cross-account behavior

- Application Signals does NOT merge service maps across Regions. Each
  Region's service map is independent.
- Cross-account service map: when CloudWatch cross-account observability
  is configured, the monitoring account sees services from monitored
  accounts in its service map. Each monitored account still writes its
  own RED metrics.

## Full NEVER list (extended)

1. NEVER skip the `CloudWatchApplicationSignalsReportServiceAccess` IAM
   policy on the workload role. The agent runs without error but
   produces zero metrics and no service-map nodes — silent failure.
2. NEVER omit `AWS_SERVICE_NAME` and `AWS_APPLICATION_ENVIRONMENT` env
   vars. Without them, services collapse into one node, SLOs cannot
   bind, and burn-rate alarms never fire.
3. NEVER set X-Ray sampling to 0% on a service with an SLO. RED metrics
   derive from traces; 0% sampling blanks Rate, Errors, and Duration.
4. NEVER create an SLO before its target service has appeared in
   `aws application-signals list-services`. CloudFormation rolls back;
   the SLO never binds to a service key.
5. NEVER mismatch the SLO interval and the burn-rate alarm period. A
   5-minute burn-rate alarm against a 1-day-only SLO interval produces
   either flapping or permanently non-firing alarms.
6. NEVER use `AWS_SERVICE_NAME` set to the team name or environment.
   The service name should match the workload (e.g.,
   `payments-api`), not the team (`team-payments`).
7. NEVER assume Application Signals is opted in across Regions. Opt-in
   is Region-scoped; verify each Region with `list-services`.
8. NEVER delete the AWS service-linked role
   `AWSServiceRoleForCloudWatchApplicationSignals`. It auto-recreates,
   but deletion causes up to 15 minutes of metric loss.
9. NEVER create more than 2 SLOs per service. Availability + latency
   covers 90% of use cases; additional SLOs fragment alarm budget and
   operator attention.
10. NEVER publish custom metrics to `AWS/ApplicationSignals` namespace
    from your application. Application Signals owns this namespace;
    custom metrics collide with derived RED metrics.
11. NEVER use `OTEL_RESOURCE_ATTRIBUTES` to override `service.name`
    inconsistently with `AWS_SERVICE_NAME`. The two must match, or
    Application Signals creates duplicate nodes.
12. NEVER raise X-Ray sampling to 100% permanently on a
    high-traffic service. X-Ray has per-Region ingestion quotas;
    sustained 100% sampling triggers throttling and drops the traces
    that drive RED metrics.
13. NEVER use CalendarInterval SLOs for low-traffic services.
    CalendarInterval requires sufficient request volume per calendar
    window; RollingInterval is more forgiving for sparse traffic.

## Edge-case handling (extended)

### Service missing from service map after 15 minutes

**Most common causes (in order of frequency):**

1. **Missing `CloudWatchApplicationSignalsReportServiceAccess` on the
   workload role.** Check
   `aws iam list-attached-role-policies --role-name <role>`.
2. **`AWS_SERVICE_NAME` unset.** Check the container env vars in the
   task definition / pod spec.
3. **X-Ray sampling rule deleted or set to 0%.** Run
   `aws xray get-sampling-rules`.
4. **ADOT collector sidecar crashed.** Check the
   `/ecs/<service>-otel` or equivalent log group for
   `TraceExporter` errors.
5. **Workload in a private subnet with no VPC endpoint to X-Ray.**
   Add the `com.amazonaws.<region>.xray` interface endpoint.

### RED metrics blank but traces visible in X-Ray

If `aws xray get-trace-summaries` shows traces but CloudWatch
`AWS/ApplicationSignals` namespace has no metrics for the service:

1. **Sampling rule exists but `FixedRate=0`.** Update per Step 5.
2. **`service.name` attribute missing from traces.** Check
   `OTEL_RESOURCE_ATTRIBUTES` includes `service.name=<name>`.
3. **ADOT collector config missing the `awsemf` exporter.** The
   collector must export to CloudWatch via `awsemf`, not just to
   X-Ray via `awsxray`.

### SLO creation fails with `ServiceNotFound`

The SLO's `RequestBasedSliConfig` references a service that has not yet
been discovered. Wait for the service to appear in
`aws application-signals list-services --query
'ServiceSummaries[?KeyAttributes.Name==\`<name>\`]'`, then create the
SLO. Application Signals considers a service "discovered" after at
least 5 traces have been received in a 15-minute window.

### Lambda auto-instrumentation fails silently

The ADOT Lambda layer ARN is Region-specific and architecture-specific.
Verify:

- The layer ARN matches `<region>` and the function's architecture
  (`x86_64` vs `arm64`).
- The Lambda execution role has
  `CloudWatchApplicationSignalsReportServiceAccess` and
  `AWSXrayWriteOnlyAccess` attached.
- `AWS_SERVICE_NAME` and `AWS_APPLICATION_ENVIRONMENT` are set in the
  function's environment variables.
- Cold-start traces are visible in X-Ray (`aws xray
  get-trace-summaries`).

### Multiple services collapse into one node

`AWS_SERVICE_NAME` is identical across services, or unset (defaults to
the container image name). Set a unique `AWS_SERVICE_NAME` per
workload. The fix is immediate for new traces; old traces retain the
old service name and stay on the collapsed node for up to 30 days.

### EKS mutating webhook does not inject

1. **Operator namespace missing.** Verify
   `kubectl get ns opentelemetry-operator-system`.
2. **Annotation on the wrong level.** The annotation must be on the
   pod template spec (`deploy.spec.template.metadata.annotations`),
   not the deployment metadata. `kubectl annotate deploy <name>`
   applies to both, but `kubectl annotate deploy <name>
   --overwrite=false` checks.
3. **Webhook certificate expired.** The operator uses an
   admission webhook; if cert-manager is uninstalled, the
   webhook cert expires in 1 year. Re-run the helm upgrade with
   `--set admissionWebhooks.certManager.enabled=true`.

### Custom metric SLO

Custom metrics are supported via `RequestBasedSliConfig` with both
`GoodRequestsMetric` and `TotalRequestsMetric` as math expressions.
The metrics MUST be in the `AWS/ApplicationSignals` namespace
(Application Signals owns this namespace). For custom application
metrics, publish to a separate namespace (e.g.,
`MyApp/SLI`) and reference them in the SLO's
`RequestBasedSliConfig.GoodRequestsMetric.MetricStat.Metric.Namespace`.

### Burn-rate alarm never fires

1. **SLO has no `BurnRates` array.** Without it, the `BurnRate` metric
   is not published. Add `BurnRates: [{RollupInterval: MINUTE}, ...]`.
2. **Alarm period mismatched to `RollupInterval`.** The alarm
   `--period` must equal the `RollupInterval` (300 seconds for
   MINUTE-rollup). This is non-obvious because the metric name
   `BurnRate` is the same across rollups.
3. **`--treat-missing-data breaching`** set incorrectly. Use `noData`
   so missing RED metrics during deployments do not trigger false
   pages.

### Cross-Region SLO

Application Signals does NOT merge across Regions. For a multi-Region
service:

- Create per-Region SLOs (e.g., `payments-api-availability-slo-us-east-1`,
  `payments-api-availability-slo-eu-west-1`).
- Create per-Region burn-rate alarms.
- Do NOT attempt a "global" SLO via cross-Region metric math — the
  `BurnRate` metric is not designed for this.

## Workload-specific defaults

| Workload | Sampling | SLO type | SLO target | Alarms |
|---|---|---|---|---|
| High-traffic API (>100 RPS) | 1-5% | RequestBased availability | 99.9% | Fast + medium + slow burn |
| Low-traffic API (<10 RPS) | 50-100% | PeriodBased availability | 99.5% | Fast + slow burn |
| Internal microservice | 5% | RequestBased availability | 99.5% | Slow burn only |
| Batch worker | 5% | PeriodBased latency (p95) | <2m per job | Slow burn only |
| Lambda API | 100% (cold-start matters) | RequestBased availability | 99.9% | Fast + medium + slow burn |
| EC2 long-running service | 5% | PeriodBased availability | 99.9% | Fast + slow burn |

## IAM policy reference

The `CloudWatchApplicationSignalsReportServiceAccess` managed policy
grants:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:PutMetricData",
        "cloudwatch:PutMetricStream",
        "application-signals:BatchGetServiceLevelObjectiveReports",
        "application-signals:PutServiceLevelObjective"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "cloudwatch:namespace": [
            "AWS/ApplicationSignals",
            "AWS/ApplicationSignalsClient"
          ]
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:log-group:/aws/application-signals/*"
    }
  ]
}
```

The condition key restricts `PutMetricData` to the Application Signals
namespaces, preventing the agent from writing arbitrary metrics. This
is why you cannot publish custom application metrics to
`AWS/ApplicationSignals` from your code — IAM denies it.

## Reference links

- **Application Signals User Guide** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Application-Signals.html
- **ServiceLevelObjective CloudFormation** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-applicationsignals-servicelevelobjective.html
- **Burn rate formulas (Google SRE Workbook Ch 5)** — https://sre.google/workbook/alerting-on-slos/
- **AWS Distro for OpenTelemetry docs** — https://aws-observability.github.io/aws-otel-introduction/
- **X-Ray Sampling Rules** — https://docs.aws.amazon.com/xray/latest/devguide/xray-console-sampling.html
