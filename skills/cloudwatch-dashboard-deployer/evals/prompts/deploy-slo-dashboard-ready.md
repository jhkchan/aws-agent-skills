# Eval prompt: deploy-slo-dashboard-ready

Plan the following CloudWatch dashboard creation and emit the standard
VERDICT block (DASHBOARD, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, WIDGETS, SHARING, NOTES).

Operation: create
Dashboard name: prod-slo-burn-rate
Region: us-east-1
Account: 111111111111
Widgets:
  - type: metric
    title: SLO Burn Rate — Checkout Availability
    namespace: AWS/ApplicationSignals
    metric_math:
      m1: AWS/ApplicationSignals, ConsumedRAT, Sum, ServiceName=checkout-service, SLO=checkout-availability-slo
      m2: AWS/ApplicationSignals, RequestedRAT, Sum, ServiceName=checkout-service, SLO=checkout-availability-slo
      e1: m1/m2
    period: 300
    position: x=0, y=0, w=24, h=6
    annotations:
      horizontal:
        - label: Fast burn (2h), value: 14.4
        - label: Slow burn (6h), value: 6.0
  - type: text
    title: SLO Runbook
    markdown: "# SLO Burn Rate Dashboard\n**SLO**: 99.9% availability (30-day window)\n**Fast burn**: page immediately if burn rate > 14.4x\n**Slow burn**: create ticket if burn rate > 6.0x for 1h\n**Runbook**: [Incident Response](https://runbooks.example.com/slo)"
    position: x=0, y=6, w=24, h=2

```json
{
  "MetricChecks": {
    "get-metric-statistics.AWS/ApplicationSignals.ConsumedRAT.ServiceName=checkout-service+SLO=checkout-availability-slo": {
      "datapoints": 12,
      "Sum": 3.2
    },
    "get-metric-statistics.AWS/ApplicationSignals.RequestedRAT.ServiceName=checkout-service+SLO=checkout-availability-slo": {
      "datapoints": 12,
      "Sum": 43.2
    }
  },
  "ExistingDashboard": null
}
```
