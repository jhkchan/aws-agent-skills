# Eval: missing-otel-instrumentation

**Difficulty:** easy
**Branch:** REVIEW_REQUIRED — service has no OTel SDK instrumentation and CloudWatch Agent not configured; Application Signals cannot discover services without traces

## Prompt

Enable Application Signals for service legacy-api. Create an SLO
with 99.5% availability target. Configure burn rate alerts. The
service has no OTel SDK instrumentation and CloudWatch Agent is
not configured for auto-instrumentation. Tags: Environment=staging.
