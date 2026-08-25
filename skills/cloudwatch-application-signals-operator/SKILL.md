---
name: cloudwatch-application-signals-operator
description: 'Operates AWS CloudWatch Application Signals with production defaults: enablement via OpenTelemetry (OTel) SDK instrumentation or auto-instrumentation, service level objectives (SLO) creation (target percentage, interval), SLI metrics (availability, latency) derived automatically from traces, burn rate alerts (fast burn = page, slow burn = ticket) using multi-window multi-burn-rate (MWMBR) algorithm, service map visualization, CloudWatch RUM integration for client-side telemetry, correlation with X-Ray traces, service hierarchy (service → operation), canary alarms, anomaly detection on SLI metrics, and multi-service SLO tracking. Emits an OPERATION_COMPLETED checklist with verification commands. Use when enabling Application Signals, creating SLOs, setting up burn rate alerts, visualizing service maps, or. Triggers: application signals, slo creation, sli metrics, burn rate alert, service map, cloudwatch rum, otel instrumentation, multi-burn- rate, x-ray correlation, canary alarm, anomaly detection slo.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live operation: AWS CLI v2 with cloudwatch and application-signals access. Works with Terraform aws_cloudwatchobservability_access_policy and CloudFormation AWS::ApplicationSignals::ServiceLevelObjective resources.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Management
  task_type: operate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: OPERATION_COMPLETED | REVIEW_REQUIRED
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, cloudwatch, application-signals, slo, sli, burn-rate, cloudops, operate, observability, opentelemetry
  dependencies: aws-orchestrator
  keywords: aws, cloudwatch, application signals, slo, sli, burn rate, otel, opentelemetry, service map, cloudops, operate, x-ray, rum, observability
  when_to_use: Invoke when the user wants to enable Application Signals, create service level objectives (SLOs), set up burn rate alerts (fast/slow burn), visualize service maps, integrate CloudWatch RUM, correlate traces with X-Ray, configure anomaly detection on SLI metrics, or track SLOs across multiple services. Do NOT invoke for basic CloudWatch alarm creation (use cloudwatch-alarm-operator), CloudWatch Logs analysis (use cloudwatch-logs-insights-troubleshooter), or general X-Ray tracing setup (use xray-tracing-deployer).
---

# CloudWatch Application Signals Operator

An AWS CloudOps agent skill that operates CloudWatch Application Signals
with correct defaults. The skill walks the OTel instrumentation
enablement, SLI metric derivation from traces, SLO creation (target
percentage, interval), burn rate alert configuration (multi-window
multi-burn-rate: fast burn = page, slow burn = ticket), service map
visualization, RUM integration, X-Ray trace correlation, service
hierarchy (service → operation), canary alarms, anomaly detection on
SLI metrics, and multi-service SLO tracking, captures the observability
topology, explains why each default matters, and emits an
OPERATION_COMPLETED checklist with copy-pasteable verification
commands.

## Activation keywords

Application Signals enable, SLO creation, SLI metrics, burn rate alert,
multi-window multi-burn-rate, service map visualization, CloudWatch RUM
integration, X-Ray trace correlation, OTel instrumentation, anomaly
detection on SLI, canary alarm.

## STRICT output contract

When this skill is invoked with an Application-Signals operation request
(enable Application Signals, create SLOs, set up burn rate alerts,
visualize service maps, or integrate RUM), the agent MUST respond with
the OPERATION_COMPLETED checklist defined in the "Output format" section
using the literal all-caps labels `APP_SIGNALS:`, `VERDICT:`,
`CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface the checklist
with prose, headings, or disclaimers — emit the block as the first lines
of the response. This contract is what assertion-based evals and
downstream operation pipelines rely on; deviating from the literal
labels breaks automation silently.

If any prerequisite is missing, the verdict is `REVIEW_REQUIRED`
with a specific gap citation in the checklist (marked `[✗]`), and
`OPERATION_COMPLETED` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before operation |
| Step 1 — Enablement (OTel SDK / auto-instrumentation) | Core setup |
| Step 2 — Service auto-discovery | How services appear |
| Step 3 — SLI metrics (availability, latency) | Derived from traces |
| Step 4 — SLO creation (target, interval) | Objective definition |
| Step 5 — Burn rate alerts (MWMBR) | Fast burn = page, slow burn = ticket |
| Step 6 — Service map visualization | Topology view |
| Step 7 — CloudWatch RUM integration | Client-side telemetry |
| Step 8 — X-Ray trace correlation | End-to-end tracing |
| Step 9 — Service hierarchy (service → operation) | Organization |
| Step 10 — Canary alarms and anomaly detection | Proactive monitoring |
| Step 11 — Multi-service SLO tracking | Fleet observability |
| Step 12 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/slo-and-burn-rate.md | SLO + burn rate detail |
| references/instrumentation-and-service-map.md | OTel + service map detail |

## Mindset

**One-line takeaway:** CloudWatch Application Signals auto-discovers
your services via OpenTelemetry (OTel) instrumentation, automatically
derives SLI metrics (availability, latency) from traces, and lets you
define SLOs with burn rate alerts that page on fast burn (immediate
budget depletion) and ticket on slow burn (gradual budget depletion).
SLI metrics are NOT manually defined — they are derived from the
traces that Application Signals collects.

Three misconceptions dominate Application Signals misconfiguration at
operation time:

- **"Application Signals requires manual metric configuration."** It
  does NOT. Application Signals auto-discovers services from OTel
  traces and automatically derives SLI metrics (availability, latency)
  from those traces. You do NOT create CloudWatch metrics or alarms
  for the SLIs — Application Signals generates them. Your job is to
  define SLOs (target percentage, interval) on top of the auto-derived
  SLIs, and configure burn rate alerts.

- **"SLO burn rate is a single threshold."** It is NOT. The multi-
  window multi-burn-rate (MWMBR) algorithm uses multiple evaluation
  windows simultaneously. A FAST burn rate (short window, e.g., 5
  minutes) detects immediate budget depletion and triggers a PAGE.
  A SLOW burn rate (long window, e.g., 1 hour) detects gradual budget
  depletion and triggers a TICKET. Both must fire for the alert to
  trigger — this reduces false positives while catching both acute and
  chronic issues.

- **"OTel instrumentation is optional for Application Signals."** It
  is NOT optional — it is the foundational requirement. Application
  Signals works by consuming OTel traces. Without OTel SDK
  instrumentation (or auto-instrumentation via CloudWatch Agent), no
  traces are emitted, no services are discovered, no SLIs are derived,
  and no SLOs can be created. The OTel layer IS Application Signals'
  data source.

## Configuration dependency graph (novel heuristic)

Application Signals configurations are NOT independent. OTel
instrumentation must be enabled before services can be discovered. SLI
metrics are derived from traces, so SLOs depend on traces existing.
Burn rate alerts depend on SLOs. Use this graph to sequence operation.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| OTel instrumentation | Application or CloudWatch Agent configured to emit OTel traces | Without OTel, NO services are discovered and NO SLIs are derived | trace emission |
| Application Signals enablement | CloudWatch Observability Access Policy attached to the account | Application Signals toggle in console/CLI must be enabled | service discovery |
| Service auto-discovery | OTel traces flowing; Application Signals enabled | Services appear within ~15 minutes of first trace emission | service inventory |
| SLI metrics (availability, latency) | Service discovered; traces contain operation-level spans | SLIs are derived automatically — NOT manually created | SLO definition |
| SLO creation (target, interval) | At least one SLI exists for the service/operation | Interval must be 1-30 days; target must be 0-100% | burn rate alerts |
| Burn rate alerts (MWMBR) | SLO defined; SNS topic exists for notifications | Fast burn window + slow burn window must BOTH fire for alert | proactive detection |
| Service map | Multiple services emitting traces | Service map shows service-to-service calls based on trace context propagation | topology view |
| RUM integration | CloudWatch RUM app monitor created; OTel on backend | RUM provides client-side traces; correlation with server traces via trace ID | end-to-end observability |
| X-Ray correlation | X-Ray tracing enabled on services | Application Signals and X-Ray share trace data; Application Signals provides higher-level views | drill-down |
| Anomaly detection on SLI | SLI metric exists; sufficient data for baseline (~2 weeks) | Anomaly detection learns the normal pattern; alerts on deviations | proactive anomaly alerts |

**The OTel-instrumentation-first row is the one a baseline model misses.**
Application Signals is not a standalone service — it consumes OTel
traces. If you enable Application Signals in the console but have no
OTel instrumentation, the service list is empty, no SLIs appear, and
no SLOs can be created. The instrumentation layer must come first.

**Cross-dependency gotchas:**
- Application Signals and X-Ray both consume trace data, but Application
  Signals provides higher-level abstractions (SLOs, service maps, SLI
  metrics). X-Ray is lower-level (raw traces, service graphs, traces
  list). They complement each other.
- RUM integration requires both a RUM app monitor (client-side) AND OTel
  on the backend. Without backend OTel, RUM traces have no server-side
  context to correlate with.
- Burn rate alerts use SNS topics. If the SNS topic does not exist or
  the subscription is not configured, alerts fire but notifications
  are silently dropped.
- SLO interval is fixed at creation time. Changing the interval requires
  deleting and recreating the SLO.

## Expert heuristic: fast burn vs slow burn (MWMBR)

Expert heuristic — fast burn vs slow burn (MWMBR) deep dive (error-budget math, window pairs, both-windows-must-fire) moved verbatim to [references/slo-and-burn-rate.md](references/slo-and-burn-rate.md).
Load on demand when tuning burn-rate windows and thresholds.

## Expert heuristic: SLI auto-derivation from traces

Expert heuristic — SLI auto-derivation from traces (availability and latency derivation, no manual metrics) moved verbatim to [references/slo-and-burn-rate.md](references/slo-and-burn-rate.md).
Load on demand when SLI metrics are missing or when explaining what Application Signals computes for you.

## Expert heuristic: service hierarchy and operation-level SLOs

Expert heuristic — service hierarchy and operation-level SLOs (service vs operation SLO binding) moved verbatim to [references/instrumentation-and-service-map.md](references/instrumentation-and-service-map.md).
Load on demand when deciding service-level vs operation-level SLO targets.

## Prerequisites (verify before operation)

Before emitting operation commands, verify these prerequisites. If any
are missing, the verdict is **REVIEW_REQUIRED**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| OTel SDK instrumentation or CloudWatch Agent auto-instrumentation | Application Signals consumes OTel traces; without it, no data | Check application code for OTel SDK or CloudWatch Agent config |
| CloudWatch Observability Access Policy attached | Enables Application Signals data collection | `aws cloudwatch describe-alarms` (verify Observability access) |
| Application Signals enabled in the account/region | The feature must be explicitly enabled | Check CloudWatch console → Application Signals |
| Services discovered (traces flowing) | SLOs require existing SLI metrics | Verify service list is non-empty |
| SNS topic for burn rate alerts | Alert notifications need an SNS topic | `aws sns list-topics` |
| CloudWatch RUM app monitor (for RUM integration) | Client-side telemetry requires a RUM app monitor | `aws rum list-app-monitors` |
| IAM permissions for application-signals API | SLO creation/modification needs API access | Check IAM policy for `application-signals:*` |
| Sufficient trace data for baseline (for anomaly detection) | Anomaly detection needs ~2 weeks of data for learning | Verify trace volume in CloudWatch Service Map |

If any prerequisite is missing, output `VERDICT: REVIEW_REQUIRED`
and cite the specific gap.

## Step 1 — Enablement (OTel SDK / auto-instrumentation)

### Option A: OTel SDK instrumentation (application-level)

Option A worked example — OTel SDK Python instrumentation code moved verbatim to [references/instrumentation-and-service-map.md](references/instrumentation-and-service-map.md).
Load on demand when writing the SDK instrumentation boilerplate.

### Option B: CloudWatch Agent auto-instrumentation

Option B worked example — CloudWatch Agent SSM auto-instrumentation sequence moved verbatim to [references/instrumentation-and-service-map.md](references/instrumentation-and-service-map.md).
Load on demand when choosing agent-based injection over SDK code.

## Step 2 — Service auto-discovery

Once OTel traces are flowing, Application Signals auto-discovers services
within ~15 minutes.

```text
Service discovery flow:
  1. Application emits OTel traces (via SDK or auto-instrumentation)
  2. CloudWatch Agent collects traces
  3. Application Signals processes traces and identifies services
  4. Services appear in the Application Signals console
  5. SLI metrics (availability, latency) are automatically derived
  6. Service map is populated based on trace context propagation
```

**Verify discovered services:**

```bash
# List discovered services (via CloudWatch metrics namespace)
aws cloudwatch list-metrics \
  --namespace AWS/ApplicationSignals \
  --query 'Metrics[*].Dimensions[?Name==`ServiceName`].Value' \
  --output table
```

## Step 3 — SLI metrics (availability, latency)

SLI metrics are automatically derived from traces. They appear in the
`AWS/ApplicationSignals` CloudWatch namespace.

| SLI Metric | Description | Auto-derived |
|---|---|---|
| `ErrorRate` | Percentage of error responses | From span status |
| `Latency` | Response time (P50, P90, P95, P99) | From span duration |
| `CallCount` | Number of requests | From span count |
| `FaultRate` | Percentage of fault responses (5xx) | From span status |

```bash
# View SLI metrics for a discovered service
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationSignals \
  --metric-name Latency \
  --dimensions Name=ServiceName,Value=payments-api Name=Operation,Value=POST-/charge \
  --start-time 2026-08-11T00:00:00Z \
  --end-time 2026-08-11T23:59:59Z \
  --period 300 \
  --statistics Average \
  --output table
```

## Step 4 — SLO creation (target, interval)

SLOs define a target percentage and evaluation interval on top of SLI
metrics.

```bash
# Create a service-level SLO
aws application-signals create-service-level-objective \
  --name "payments-api-availability-slo" \
  --description "99.9% availability for payments-api over 30 days" \
  --sli-config '{"SliMetricType": "Availability", "MetricSourceData": {...}}' \
  --request-based-sli-config '...' \
  --goal '{"Interval": {"Interval": 30, "RollingInterval": {"DurationUnit": "DAY", "Duration": 30}}, "AttainmentGoal": 99.9, "WarningThreshold": 99.95}'
```

**SLO parameters:**

| Parameter | Description | Allowed values |
|---|---|---|
| `AttainmentGoal` | Target percentage | 0-100 (e.g., 99.9) |
| `Interval` | Evaluation window | 1-30 days (rolling or calendar) |
| `WarningThreshold` | Warning level (below goal but above breach) | 0-100 |
| `SliMetricType` | Metric type | Availability, Latency |
| `Operation` | Target operation (for operation-level SLO) | Service operation name |

## Step 5 — Burn rate alerts (MWMBR)

Burn rate alerts use the multi-window multi-burn-rate algorithm. Create
alarms on the burn rate metrics:

```bash
# Create a fast-burn alarm (page)
aws cloudwatch put-metric-alarm \
  --alarm-name "payments-api-fast-burn" \
  --alarm-description "Fast burn rate — page on-call" \
  --namespace AWS/ApplicationSignals \
  --metric-name BurnRate \
  --dimensions Name=ServiceName,Value=payments-api Name=SLOName,Value=payments-api-availability-slo \
  --statistic Maximum \
  --period 300 \
  --threshold 14.4 \
  --comparison-operator GreaterThanThreshold \
  --datapoints-to-alarm 1 \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:critical-alerts

# Create a slow-burn alarm (ticket)
aws cloudwatch put-metric-alarm \
  --alarm-name "payments-api-slow-burn" \
  --alarm-description "Slow burn rate — create ticket" \
  --namespace AWS/ApplicationSignals \
  --metric-name BurnRate \
  --dimensions Name=ServiceName,Value=payments-api Name=SLOName,Value=payments-api-availability-slo \
  --statistic Maximum \
  --period 3600 \
  --threshold 6.0 \
  --comparison-operator GreaterThanThreshold \
  --datapoints-to-alarm 1 \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:warning-tickets
```

**MWMBR window/threshold combinations:**

| Alert type | Short window | Long window | Threshold | Action |
|---|---|---|---|---|
| Fast burn | 5 min | 1 hour | 14.4x | Page |
| Slow burn | 30 min | 6 hours | 6.0x | Ticket |
| Slow burn | 2 hours | 1 day | 3.0x | Ticket |
| Slow burn | 6 hours | 3 days | 1.0x | Ticket |

## Step 6 — Service map visualization

The service map is auto-generated from trace context propagation. It
shows service-to-service call relationships.

```text
Service Map (auto-generated):
  Client → API Gateway → payments-api → database
                       ↓
                     RUM → payments-api (correlation)

  Green  = healthy (SLI within target)
  Yellow = degraded (SLI approaching breach)
  Red    = unhealthy (SLI breaching)
```

The service map is accessible in the CloudWatch console under
Application Signals. No CLI/API call creates it — it is derived from
trace data.

## Step 7 — CloudWatch RUM integration

Step 7 — CloudWatch RUM integration (app-monitor creation CLI, EnableXRay correlation) moved verbatim to [references/instrumentation-and-service-map.md](references/instrumentation-and-service-map.md).
Load on demand when wiring client-side RUM telemetry.

## Step 8 — X-Ray trace correlation

Step 8 — X-Ray trace correlation (drill-down flow, service map vs service graph) moved verbatim to [references/instrumentation-and-service-map.md](references/instrumentation-and-service-map.md).
Load on demand when correlating Application Signals views with raw X-Ray traces.

## Step 9 — Service hierarchy (service → operation)

Application Signals organizes telemetry as Service → Operation:

```text
Service: payments-api
  Operations:
    POST /charge     — availability SLI, latency SLI
    GET /status      — availability SLI, latency SLI
    POST /refund     — availability SLI, latency SLI
    GET /health      — availability SLI, latency SLI

  Service-level SLI = aggregate of all operations
  Operation-level SLI = individual operation metrics
```

SLOs can be defined at either level. For critical operations (e.g., POST
/charge), use operation-level SLOs with tighter targets.

## Step 10 — Canary alarms and anomaly detection

Step 10 — canary and anomaly-detection alarm CLI payloads moved verbatim to [references/slo-and-burn-rate.md](references/slo-and-burn-rate.md).
Load on demand when adding Synthetics canaries or ANOMALY_DETECTION_BAND alarms on SLI metrics.

## Step 11 — Multi-service SLO tracking

Step 11 — multi-service SLO tracking CLI payloads moved verbatim to [references/slo-and-burn-rate.md](references/slo-and-burn-rate.md).
Load on demand when building fleet-level SLO dashboards.

## Step 12 — Recent features

Recent AWS features (2023-2026) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when deciding between GA mechanisms and older flows.

## NEVER do these things

1. **NEVER enable Application Signals without OTel instrumentation.**
   Application Signals consumes OTel traces. Without instrumentation,
   no services are discovered, no SLIs appear, and no SLOs can be
   created. The instrumentation layer MUST come first.

2. **NEVER manually create CloudWatch metrics for Application Signals
   SLIs.** SLIs (availability, latency) are auto-derived from traces.
   Manually creating them in the AWS/ApplicationSignals namespace
   conflicts with the auto-derived metrics.

3. **NEVER use a single burn rate threshold.** The MWMBR algorithm uses
   multiple windows (fast + slow) to balance sensitivity and noise. A
   single threshold either pages too much (too sensitive) or misses
   chronic issues (too insensitive).

4. **NEVER define an SLO without a warning threshold.** The
   WarningThreshold alerts before the SLO is breached, giving time to
   react. Without it, you only learn about SLO breaches after they
   happen.

5. **NEVER forget the SNS topic for burn rate alerts.** Burn rate
   alarms need an SNS topic with subscriptions. Without a configured
   subscription, alerts fire but notifications are silently dropped.

6. **NEVER assume service map appears instantly.** Service
   auto-discovery takes ~15 minutes after the first trace is emitted.
   If the service map is empty, wait for trace propagation before
   troubleshooting.

7. **NEVER use Application Signals as a replacement for X-Ray.**
   Application Signals provides higher-level views (SLOs, service maps,
   SLI metrics). X-Ray provides raw trace detail. They complement each
   other. Use both for full observability.

8. **NEVER enable RUM without backend OTel instrumentation.** RUM
   provides client-side traces. Without backend OTel, there is no
   server-side context to correlate with. The end-to-end view is broken.

9. **NEVER change the SLO interval after creation.** Changing the
   interval (e.g., from 7 days to 30 days) requires deleting and
   recreating the SLO. The interval is immutable after creation.

10. **NEVER rely solely on canary alarms for availability monitoring.**
    Canary alarms test synthetic checks. SLI-based burn rate alerts
    monitor real user traffic. Both are needed — canaries catch
    outages that may not affect real traffic yet; SLI alerts catch
    real-world degradation.

## Output format

```text
APP_SIGNALS: <service-name> (<operation|service-level>)
VERDICT: OPERATION_COMPLETED | REVIEW_REQUIRED
CHECKLIST:
  [✓|✗] OTel instrumentation: enabled (SDK | auto-instrumentation)
  [✓|✗] Application Signals: enabled (account/region)
  [✓|✗] Service discovered: <service-name> (traces flowing)
  [✓|✗] SLI metrics: availability + latency (auto-derived from traces)
  [✓|✗] SLO: <slo-name> (target <percentage>%, interval <N> days)
  [✓|✗] Warning threshold: <percentage>%
  [✓|✗] Burn rate alerts: fast burn (5m/1h, 14.4x → page) + slow burn (30m/6h, 6.0x → ticket)
  [✓|✗] SNS topic: <topic-arn> (subscriptions configured)
  [✓|✗] Service map: auto-generated (traces propagating)
  [✓|✗] RUM integration: <enabled|disabled> (app monitor: <name>)
  [✓|✗] X-Ray correlation: enabled (shared trace data)
  [✓|✗] Anomaly detection: <enabled|disabled> on SLI metrics
  [✓|✗] Canary alarm: <configured|none>
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws application-signals list-service-level-objectives
  aws application-signals get-service-level-objective --id <slo-id>
  aws cloudwatch describe-alarms --alarm-name-prefix <service-name>
```

### Worked example — SLO with MWMBR burn rate alerts

Worked example — filled-in OPERATION_COMPLETED checklist for payments-api (POST-/charge) moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when formatting a real OPERATION_COMPLETED response.

## Error handling

Error-handling deep dive (no services appearing, SLI metrics missing, burn-rate alarms not firing, InvalidRequest, incomplete topology, RUM correlation) moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand when an Application Signals operation does not behave as expected.

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — Recent AWS features (2023-2026) moved from SKILL.md
- [references/error-handling.md](references/error-handling.md) — error-handling deep dive moved from SKILL.md
- [references/worked-examples.md](references/worked-examples.md) — filled-in OPERATION_COMPLETED worked example moved from SKILL.md
- [references/instrumentation-and-service-map.md](references/instrumentation-and-service-map.md) — OTel + service map detail; now also holds the service-hierarchy heuristic, Step 1 Options A/B, and Steps 7-8 moved from SKILL.md
- [references/slo-and-burn-rate.md](references/slo-and-burn-rate.md) — SLO + burn rate detail; now also holds the MWMBR and SLI-derivation heuristics and Steps 10-11 moved from SKILL.md

## Domain

AWS CloudOps / CloudWatch Application Signals Service-Level Objective
Management & Burn Rate Alert Operations.

## AWS documentation

- **Application Signals** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Application-Signals.html
- **Enabling Application Signals** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Application-Signals-Enable.html
- **Creating SLOs** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Application-Signals-Create-SLO.html
- **Burn rate alarms** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Application-Signals-Burn-Rate.html
- **Service map** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Application-Signals-Service-Map.html
- **RUM integration** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-RUM.html
- **OTel instrumentation** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Application-Signals-Instrumentation.html
- **X-Ray correlation** — https://docs.aws.amazon.com/xray/latest/devguide/aws-xray.html
- **CloudWatch Anomaly Detection** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Anomaly_Detection.html

