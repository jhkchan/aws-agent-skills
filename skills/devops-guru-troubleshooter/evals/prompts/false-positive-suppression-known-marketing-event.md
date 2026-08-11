# Eval: false-positive-suppression-known-marketing-event

**Difficulty:** hard
**Branch:** ROOT_CAUSE_FOUND — pre-announced marketing campaign is the root cause; documented suppression recommended (not auto-dismiss)

## Prompt

Diagnose this DevOps Guru insight:
Insight ID: z-9012ijkl in us-east-1
describe-insight: PROACTIVE, HIGH, OPEN, Name="Anomalous traffic
pattern on ALB app/marketing-alb", StartTime=2026-08-09T09:00Z.
list-anomalies-for-insight: RequestCount elevated 15x baseline
(200 rps -> 3000 rps); HTTPCode_Target_2XX_Count elevated
proportionally (no error rate increase); TargetResponseTime
unchanged (no latency degradation).
list-recommendations: AGGREGATE_OF_METRICS — "Investigate the
traffic source."
Context: Marketing team launched a pre-announced email + push
campaign at 2026-08-09T08:55Z targeting 500k users. The spike
is expected and the ALB is sized for it.
Region: us-east-1.
