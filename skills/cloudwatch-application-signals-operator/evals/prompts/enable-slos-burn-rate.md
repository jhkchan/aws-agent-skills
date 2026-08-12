# Eval: enable-slos-burn-rate

**Difficulty:** hard
**Branch:** OPERATION_COMPLETED — 99.9% availability SLO, 30-day rolling interval, MWMBR fast burn (5m/1h, 14.4x → page) + slow burn (30m/6h, 6.0x → ticket), auto-derived SLI metrics

## Prompt

Enable Application Signals for service payments-api, operation
POST /charge. Create an SLO with 99.9% availability target over
30-day rolling interval. Warning threshold 99.95%. Configure
MWMBR burn rate alerts: fast burn (5m/1h, 14.4x) pages SNS topic
critical-alerts, slow burn (30m/6h, 6.0x) tickets SNS topic
warning-tickets. OTel SDK instrumentation already enabled.
Tags: Environment=production, Team=payments, Tier=critical.
