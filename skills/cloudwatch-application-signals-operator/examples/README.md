# End-to-End Example: CloudWatch Application Signals Operation

A walkthrough showing how to use the
`cloudwatch-application-signals-operator` skill from invocation through
verification. Mirrors the structured-eval pattern of shipping a
concrete worked example per skill.

---

## Scenario

You are enabling Application Signals for a critical payments service,
creating an SLO with MWMBR burn rate alerts. The operation needs:

- Service: payments-api
- Operation: POST /charge
- SLO: 99.9% availability, 30-day rolling interval
- Warning threshold: 99.95%
- Burn rate alerts: fast burn (5m/1h, 14.4x → page), slow burn (30m/6h, 6.0x → ticket)
- SNS topics: critical-alerts (page), warning-tickets (ticket)
- OTel SDK: already enabled (Python opentelemetry)
- Anomaly detection: on latency P99
- Canary alarm: per endpoint
- Tags: Environment=production, Team=payments, Tier=critical

---

## Step 1 — Invoke the skill

### Option A: Natural language

```
You: "Enable Application Signals for payments-api. Create an SLO
      at 99.9% availability over 30 days. Configure MWMBR burn rate
      alerts — fast burn pages critical-alerts, slow burn tickets
      warning-tickets. Add anomaly detection on latency."
```

### Option B: CLI routing

```bash
node cli/bin/cli.js route "application signals slo burn rate"
```

---

## Step 2 — Skill produces the OPERATION_COMPLETED checklist

```text
APP_SIGNALS: payments-api (POST-/charge)
VERDICT: OPERATION_COMPLETED
CHECKLIST:
  [✓] OTel instrumentation: enabled (SDK — Python opentelemetry)
  [✓] Application Signals: enabled (us-east-1)
  [✓] Service discovered: payments-api (traces flowing — last trace 30s ago)
  [✓] SLI metrics: availability (99.97%) + latency P99 (287ms)
  [✓] SLO: payments-api-charge-availability (target 99.9%, interval 30 days rolling)
  [✓] Warning threshold: 99.95%
  [✓] Burn rate alerts: fast burn (5m/1h, 14.4x → SNS critical-alerts → page) + slow burn (30m/6h, 6.0x → SNS warning-tickets → ticket)
  [✓] SNS topic: arn:aws:sns:us-east-1:123456789012:critical-alerts (3 subscriptions)
  [✓] Service map: auto-generated (4 services, 12 edges)
  [✓] RUM integration: enabled (app monitor: payments-frontend, EnableXRay: true)
  [✓] X-Ray correlation: enabled (drill-down from SLO to trace)
  [✓] Anomaly detection: enabled on latency P99 (band: 2 stdev)
  [✓] Canary alarm: payments-api-canary (1-min interval, 60s timeout)
  [✓] Tags: Environment=production, Team=payments, Tier=critical
VERIFICATION_COMMANDS:
  aws application-signals list-service-level-objectives
  aws application-signals get-service-level-objective --id payments-api-charge-availability
  aws cloudwatch describe-alarms --alarm-name-prefix payments-api
```

---

## Step 3 — Create the SLO

```bash
# Create the SLO
aws application-signals create-service-level-objective \
  --name "payments-api-charge-availability" \
  --description "99.9% availability for payments-api POST /charge over 30 days" \
  --sli-config '{
    "SliMetricType": "Availability",
    "MetricSourceData": {
      "ServiceMetric": {
        "MetricName": "ErrorRate",
        "Namespace": "AWS/ApplicationSignals",
        "Dimensions": [
          {"Name": "ServiceName", "Value": "payments-api"},
          {"Name": "Operation", "Value": "POST-/charge"}
        ],
        "Stat": "Average",
        "Period": 60
      }
    }
  }' \
  --goal '{
    "Interval": {
      "RollingInterval": {
        "DurationUnit": "DAY",
        "Duration": 30
      }
    },
    "AttainmentGoal": 99.9,
    "WarningThreshold": 99.95
  }' \
  --tags '[{"Key":"Environment","Value":"production"},{"Key":"Team","Value":"payments"},{"Key":"Tier","Value":"critical"}]'
```

---

## Step 4 — Configure MWMBR burn rate alerts

```bash
# Fast burn alarm — PAGE (5m/1h window, 14.4x threshold)
aws cloudwatch put-metric-alarm \
  --alarm-name "payments-api-fast-burn-page" \
  --alarm-description "Fast burn rate — page on-call. 14.4x burn rate over 5m+1h windows." \
  --namespace AWS/ApplicationSignals \
  --metric-name BurnRate \
  --dimensions \
    Name=ServiceName,Value=payments-api \
    Name=SLOName,Value=payments-api-charge-availability \
    Name=BurnRateType,Value=FastBurn \
  --statistic Maximum \
  --period 300 \
  --threshold 14.4 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --datapoints-to-alarm 2 \
  --treat-missing-data notBreaching \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:critical-alerts

# Slow burn alarm — TICKET (30m/6h window, 6.0x threshold)
aws cloudwatch put-metric-alarm \
  --alarm-name "payments-api-slow-burn-ticket" \
  --alarm-description "Slow burn rate — create ticket. 6.0x burn rate over 30m+6h windows." \
  --namespace AWS/ApplicationSignals \
  --metric-name BurnRate \
  --dimensions \
    Name=ServiceName,Value=payments-api \
    Name=SLOName,Value=payments-api-charge-availability \
    Name=BurnRateType,Value=SlowBurn \
  --statistic Maximum \
  --period 1800 \
  --threshold 6.0 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --datapoints-to-alarm 2 \
  --treat-missing-data notBreaching \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:warning-tickets
```

---

## Step 5 — Configure anomaly detection on latency

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "payments-api-latency-anomaly" \
  --alarm-description "Latency P99 anomaly — outside 2-stdev band" \
  --namespace AWS/ApplicationSignals \
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

---

## Step 6 — Verify

```bash
# List SLOs
aws application-signals list-service-level-objectives --output table

# Get SLO details
aws application-signals get-service-level-objective \
  --id payments-api-charge-availability

# Verify alarms
aws cloudwatch describe-alarms \
  --alarm-name-prefix payments-api \
  --output table

# Verify SLO burn rate metric exists
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationSignals \
  --metric-name BurnRate \
  --dimensions \
    Name=ServiceName,Value=payments-api \
    Name=SLOName,Value=payments-api-charge-availability \
  --start-time 2026-08-11T00:00:00Z \
  --end-time 2026-08-11T23:59:59Z \
  --period 300 \
  --statistics Maximum \
  --output table
```

---

## What the skill catches that a naive operation misses

| Configuration | Naive operation | Skill output | Why the skill is right |
|---|---|---|---|
| Burn rate | Single threshold (14.4x only) | MWMBR: fast burn (14.4x page) + slow burn (6.0x ticket) | Single threshold misses chronic degradation; MWMBR catches both acute and chronic |
| Warning threshold | Not set | 99.95% warning | Without warning, you only learn after SLO breach |
| SLI metrics | Manually created | Auto-derived from traces | Application Signals derives SLIs automatically; manual creation is redundant |
| SNS subscriptions | Not verified | Subscription count checked | Alerts fire silently without subscriptions |
| Anomaly detection | Not configured | Enabled on latency P99 | Catches latency regressions before SLO breach |
| OTel prerequisite | Assumed | Verified (SDK enabled) | Application Signals is useless without OTel traces |

---

## Related artifacts

- **Skill definition:** `skills/cloudwatch-application-signals-operator/SKILL.md`
- **SLO and Burn Rate guide:** `skills/cloudwatch-application-signals-operator/references/slo-and-burn-rate.md`
- **Instrumentation and Service Map guide:** `skills/cloudwatch-application-signals-operator/references/instrumentation-and-service-map.md`
- **Eval suite:** `skills/cloudwatch-application-signals-operator/evals/evals.json`
- **Legacy test cases:** `skills/cloudwatch-application-signals-operator/eval/test-cases.yaml`
