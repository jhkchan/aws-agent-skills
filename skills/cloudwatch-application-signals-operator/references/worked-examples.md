# Worked Examples (load on demand) — CloudWatch Application Signals Operator

Secondary worked examples and filled-in checklists moved verbatim from SKILL.md. Loaded on demand.

---

## Worked example — SLO with MWMBR burn rate alerts (moved from SKILL.md)

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
