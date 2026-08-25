# SLO and Burn Rate — CloudWatch Application Signals Operator

Deep reference on service level objectives (SLOs), SLI metric
auto-derivation from traces, the multi-window multi-burn-rate (MWMBR)
algorithm, burn rate alert configuration, warning thresholds, anomaly
detection on SLI metrics, and canary alarms. Loaded on demand by the
skill — kept out of the main SKILL.md body so the operation procedure
stays scannable.

## SLO fundamentals

### What is an SLO?

A Service Level Objective (SLO) is a target reliability goal for a
service or operation. It consists of:

- **SLI (Service Level Indicator):** the metric being measured
  (availability, latency)
- **Target:** the percentage goal (e.g., 99.9%)
- **Interval:** the evaluation window (e.g., 30 days rolling)
- **Warning threshold:** a softer target that alerts before the SLO is
  breached

```text
SLO = SLI + Target + Interval

Example:
  SLI: availability (auto-derived from traces)
  Target: 99.9%
  Interval: 30 days rolling
  Warning: 99.95%

  Error budget = (100% - 99.9%) = 0.1% of requests can fail
  Over 30 days with 1M requests/day: 30,000 requests can fail
```

### Error budget

The error budget is the amount of unreliability allowed before the SLO
is breached:

```text
SLO target: 99.9% availability
Error budget: 0.1% (100% - 99.9%)

Over 30-day interval with 10M total requests:
  Allowed failures: 10,000,000 × 0.001 = 10,000 requests

If actual failures = 8,000:
  Budget consumed: 80%
  Burn rate: actual error rate / allowed error rate
  → 0.08% / 0.1% = 0.8x (under budget consumption rate)

If actual failures = 15,000:
  Budget consumed: 150% → SLO BREACHED
```

### Rolling vs calendar intervals

| Interval type | Description | Behavior |
|---|---|---|
| Rolling | Slides forward in time (e.g., last 30 days from now) | Smooths out daily variation; always reflects recent history |
| Calendar | Fixed period (e.g., calendar month) | Resets at period boundary; may spike at reset |

**Recommendation:** use rolling intervals for operational SLOs (they
always reflect recent behavior). Use calendar intervals for compliance/
reporting SLOs (they align with reporting cycles).

## SLI auto-derivation from traces

### How Application Signals derives SLIs

Application Signals does NOT require manual metric creation. SLIs are
derived from OTel traces automatically:

```text
Availability SLI derivation:
  1. Each trace has a root span with a status (OK or ERROR)
  2. Application Signals counts OK spans and total spans per operation
  3. Availability = OK spans / total spans × 100%

  Example for POST /charge (1000 traces):
    OK: 9990
    ERROR: 10
    Availability: 9990 / 10000 = 99.90%

Latency SLI derivation:
  1. Each trace has a span duration (in milliseconds)
  2. Application Signals computes percentiles (P50, P90, P95, P99)
  3. Latency SLI = percentage of requests under a threshold

  Example for POST /charge (1000 traces):
    P99 latency: 287ms
    Threshold: 500ms
    Latency SLI: 99.5% of requests under 500ms
```

### SLI metric namespace

Auto-derived SLIs appear in the `AWS/ApplicationSignals` CloudWatch
namespace:

| Metric | Dimensions | Description |
|---|---|---|
| `ErrorRate` | ServiceName, Operation | Percentage of error responses |
| `FaultRate` | ServiceName, Operation | Percentage of fault (5xx) responses |
| `Latency` | ServiceName, Operation | Response latency (ms) |
| `CallCount` | ServiceName, Operation | Number of calls |

### Verifying SLI metrics

```bash
aws cloudwatch list-metrics \
  --namespace AWS/ApplicationSignals \
  --query 'Metrics[*].Dimensions[?Name==`ServiceName`].Value' \
  --output table

aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationSignals \
  --metric-name ErrorRate \
  --dimensions Name=ServiceName,Value=payments-api Name=Operation,Value=POST-/charge \
  --start-time 2026-08-11T00:00:00Z \
  --end-time 2026-08-11T23:59:59Z \
  --period 300 \
  --statistics Average \
  --output table
```

## Multi-window multi-burn-rate (MWMBR)

### The problem with single-threshold burn rate

A single burn rate threshold either:
- **Too high:** misses chronic slow-burn degradation
- **Too low:** too many false positives from brief spikes

### MWMBR solution

MWMBR uses MULTIPLE evaluation windows simultaneously. An alert fires
only when BOTH the short window AND the long window exceed the burn
rate threshold. This reduces false positives while catching both acute
and chronic issues.

```text
MWMBR algorithm:
  ┌────────────────────────────────────────────────────────────────┐
  │ Window pair          │ Burn rate │ Action │ Rationale           │
  ├──────────────────────┼───────────┼────────┼─────────────────────┤
  │ 5 min + 1 hour       │ 14.4x     │ Page   │ Acute: 2% of budget │
  │                      │           │        │ consumed in 1 hour  │
  ├──────────────────────┼───────────┼────────┼─────────────────────┤
  │ 30 min + 6 hours     │ 6.0x      │ Ticket │ Subacute: 5% budget │
  │                      │           │        │ in 6 hours          │
  ├──────────────────────┼───────────┼────────┼─────────────────────┤
  │ 2 hours + 1 day      │ 3.0x      │ Ticket │ Moderate: 10% budget│
  │                      │           │        │ in 1 day            │
  ├──────────────────────┼───────────┼────────┼─────────────────────┤
  │ 6 hours + 3 days     │ 1.0x      │ Ticket │ Chronic: 10% budget │
  │                      │           │        │ in 3 days           │
  └────────────────────────────────────────────────────────────────┘

  BOTH windows must exceed the threshold for the alert to fire.

  Example: fast burn page
    Short window (5 min): burn rate = 15.0x (> 14.4x ✓)
    Long window (1 hour): burn rate = 14.8x (> 14.4x ✓)
    → BOTH exceed → PAGE

  Example: brief spike (no alert)
    Short window (5 min): burn rate = 20.0x (> 14.4x ✓)
    Long window (1 hour): burn rate = 5.0x (< 14.4x ✗)
    → Only short window exceeds → NO ALERT (not sustained)
```

### Why 14.4x for fast burn?

The 14.4x rate means the error budget is consumed at 14.4 times the
planned rate. For a 30-day SLO with 0.1% error budget:

```text
Budget = 0.1% × 30 days = 0.03% per day = 43.2 minutes

At 14.4x burn rate:
  Budget consumed per hour = 14.4 × (0.03% / 24) = 0.018%
  Time to exhaust = 100% / 0.018% ≈ 2 hours

  → A 14.4x burn rate exhausts the budget in ~2 hours
  → This is acute enough to page immediately
```

### Implementing MWMBR alerts

**Fast burn alarm (page):**

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "payments-api-fast-burn-page" \
  --namespace AWS/ApplicationSignals \
  --metric-name BurnRate \
  --dimensions Name=ServiceName,Value=payments-api Name=SLOName,Value=payments-api-availability-slo Name=BurnRateType,Value=FastBurn \
  --statistic Maximum \
  --period 300 \
  --threshold 14.4 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --datapoints-to-alarm 2 \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:critical-alerts
```

**Slow burn alarm (ticket):**

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "payments-api-slow-burn-ticket" \
  --namespace AWS/ApplicationSignals \
  --metric-name BurnRate \
  --dimensions Name=ServiceName,Value=payments-api Name=SLOName,Value=payments-api-availability-slo Name=BurnRateType,Value=SlowBurn \
  --statistic Maximum \
  --period 1800 \
  --threshold 6.0 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --datapoints-to-alarm 2 \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:warning-tickets
```

## Warning thresholds

The warning threshold alerts BEFORE the SLO is breached:

```text
SLO target: 99.9% (error budget: 0.1%)
Warning threshold: 99.95% (warning budget: 0.05%)

If availability drops to 99.96%:
  → Below warning threshold (99.95%) but above SLO target (99.9%)
  → Warning alert fires (not critical)

If availability drops to 99.85%:
  → Below SLO target (99.9%)
  → SLO breached + burn rate alerts escalate
```

## Anomaly detection on SLI metrics

CloudWatch Anomaly Detection creates a dynamic band around SLI metrics:

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "payments-api-latency-anomaly" \
  --metrics '[
    {
      "Id": "m1",
      "MetricStat": {
        "Metric": {
          "Namespace": "AWS/ApplicationSignals",
          "MetricName": "Latency",
          "Dimensions": [
            {"Name": "ServiceName", "Value": "payments-api"},
            {"Name": "Operation", "Value": "POST-/charge"}
          ]
        },
        "Period": 300,
        "Stat": "p99"
      },
      "ReturnData": true
    },
    {
      "Id": "ad1",
      "Expression": "ANOMALY_DETECTION_BAND(m1, 2)"
    }
  ]' \
  --threshold-metric-id ad1 \
  --comparison-operator LessThanLowerOrGreaterThanUpperThreshold \
  --evaluation-periods 1 \
  --datapoints-to-alarm 1 \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:warning-tickets
```

The band uses 2 standard deviations. The model trains on ~2 weeks of
historical data and adapts over time.

## Canary alarms

Canary alarms use CloudWatch Synthetics to run synthetic checks:

```bash
# Create a canary
aws synthetics create-canary \
  --name payments-api-canary \
  --code '{"S3Bucket":"canary-scripts","S3Key":"payments.zip","Handler":"index.handler"}' \
  --schedule '{"Expression":"rate(1 minute)"}' \
  --run-config '{"TimeoutInSeconds":60}' \
  --artifact-config '{"S3Bucket":"canary-artifacts"}'
```

The canary hits the endpoint every minute. If the canary fails, it
triggers a CloudWatch alarm. This provides an external perspective
that complements SLI-based alerts.

## Common SLO pitfalls

### Pitfall 1: SLO target too aggressive

A 99.999% SLO leaves only 0.001% error budget. This is nearly
impossible to maintain and creates constant noise.

**Fix:** start with 99.9% and tighten as the service matures.

### Pitfall 2: Single burn rate threshold

Using one threshold (e.g., 14.4x only) misses slow-burn degradation
that gradually exhausts the budget.

**Fix:** use MWMBR with both fast and slow windows.

### Pitfall 3: No warning threshold

Without a warning, you only learn about problems after the SLO is
already breached.

**Fix:** set WarningThreshold to 50% above the target (e.g., 99.95%
warning for 99.9% target).

### Pitfall 4: SNS topic without subscriptions

Burn rate alerts fire but notifications are silently dropped.

**Fix:** verify SNS topic has active subscriptions before relying on
alerts.
---

## Expert heuristic: fast burn vs slow burn (MWMBR) (moved from SKILL.md)

A baseline model says "set a burn rate threshold at 14.4x." The correct
heuristic recognizes that multi-window multi-burn-rate (MWMBR) uses
multiple windows simultaneously to balance sensitivity and noise.

```text
Burn rate concept:
  An SLO has an error budget. For 99.9% availability over 30 days:
    Error budget = 0.1% × 30 days = 43.2 minutes

  Burn rate = actual error rate / allowed error rate
    Burn rate 1.0 = consuming budget at exactly the planned rate
    Burn rate 2.0 = consuming budget 2x faster than planned
    Burn rate 14.4 = consuming budget 14.4x faster (will exhaust in ~2 hours)

Multi-window multi-burn-rate (MWMBR):
  ┌────────────────────────────────────────────────────────────┐
  │ Alert type     │ Short window │ Long window │ Burn rate │ Action │
  ├────────────────┼──────────────┼─────────────┼───────────┼────────┤
  │ Fast burn PAGE │ 5 minutes    │ 1 hour      │ 14.4x     │ Page   │
  │ Slow burn      │ 30 minutes   │ 6 hours     │ 6.0x      │ Ticket │
  │ Slow burn      │ 2 hours      │ 1 day       │ 3.0x      │ Ticket │
  │ Slow burn      │ 6 hours      │ 3 days      │ 1.0x      │ Ticket │
  └────────────────────────────────────────────────────────────┘

  BOTH windows must exceed the burn rate for the alert to fire.
  This reduces false positives: a brief spike alone does not trigger
  a page unless the long-window burn rate is also elevated.
```

**Key implication:** the fast-burn 5m/1h window at 14.4x is for acute
incidents (page). The slow-burn windows at lower rates are for chronic
degradation (ticket). Both are needed — fast burn catches outages; slow
burn catches slow drifts that would eventually exhaust the error budget.
---

## Expert heuristic: SLI auto-derivation from traces (moved from SKILL.md)

A baseline model says "create CloudWatch metrics for availability and
latency." The correct heuristic recognizes that Application Signals
DERIVES SLIs from OTel traces — you do NOT create them.

```text
How SLIs are derived from traces:

  Availability SLI:
    Traces contain span status (OK / ERROR).
    Availability = (OK spans / total spans) for an operation.
    Example: 9999 OK / 10000 total = 99.99% availability.

  Latency SLI:
    Traces contain span duration.
    Latency SLI = percentage of requests under a threshold (e.g., P99 < 500ms).
    Example: 9900 / 10000 requests under 500ms = 99.0% latency SLI.

  These metrics are AUTOMATICALLY computed by Application Signals.
  You do NOT create CloudWatch custom metrics or Metric Math expressions.
  You define SLOs ON TOP of these auto-derived SLIs.
```

**Key implication:** if availability or latency SLIs are not appearing,
the issue is upstream — OTel traces are not flowing or the service has
not been discovered. Fix the instrumentation first; the SLIs follow.
---

## Step 10 — Canary alarms and anomaly detection (moved from SKILL.md)

### Canary alarms

Canary alarms monitor synthetic checks against your service endpoints.
They complement SLI-based alarms by testing from an external perspective.

```bash
# Create a CloudWatch Synthetics canary
aws synthetics create-canary \
  --name payments-api-canary \
  --code '{"S3Bucket": "canary-scripts", "S3Key": "payments-canary.zip", "Handler": "index.handler"}' \
  --schedule '{"Expression": "rate(1 minute)"}' \
  --run-config '{"TimeoutInSeconds": 60}'
```

### Anomaly detection on SLI metrics

CloudWatch Anomaly Detection learns the normal pattern of SLI metrics
and alerts on deviations:

```bash
# Create an anomaly detection alarm on latency SLI
aws cloudwatch put-metric-alarm \
  --alarm-name "payments-api-latency-anomaly" \
  --namespace AWS/ApplicationSignals \
  --metric-name Latency \
  --dimensions Name=ServiceName,Value=payments-api Name=Operation,Value=POST-/charge \
  --statistic P99 \
  --period 300 \
  --threshold-metric-id ad1 \
  --comparison-operator LessThanLowerOrGreaterThanUpperThreshold \
  --evaluation-periods 1 \
  --datapoints-to-alarm 1 \
  --metrics '[{"Id":"m1","MetricStat":{"Metric":{"Namespace":"AWS/ApplicationSignals","MetricName":"Latency","Dimensions":[{"Name":"ServiceName","Value":"payments-api"},{"Name":"Operation","Value":"POST-/charge"}]},"Period":300,"Stat":"P99"},"ReturnData":true},{"Id":"ad1","Expression":"ANOMALY_DETECTION_BAND(m1, 2)"}]' \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:warning-tickets
```
---

## Step 11 — Multi-service SLO tracking (moved from SKILL.md)

For organizations with many services, track SLOs across the fleet:

```bash
# List all SLOs
aws application-signals list-service-level-objectives \
  --max-results 50 \
  --output table

# Get SLO status for a specific SLO
aws application-signals get-service-level-objective \
  --id <slo-id>
```

**Key implication:** create a CloudWatch dashboard aggregating SLO
status across services for a fleet-level view. This enables proactive
identification of services approaching SLO breaches.
