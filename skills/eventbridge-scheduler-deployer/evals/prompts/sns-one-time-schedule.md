# Eval: sns-one-time-schedule

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — one-time at(2026-09-01T14:00:00), SNS target, auto-delete after completion, retry max 5

## Prompt

Create a one-time EventBridge Scheduler schedule called
campaign-launch that publishes to SNS topic marketing-alerts
(arn:aws:sns:us-east-1:123456789012:marketing-alerts) at
2026-09-01T14:00:00 UTC. Auto-delete after completion. Retry:
max 5 attempts. Pass input {"campaign": "summer-sale"}.
Tags: Environment=production, Team=marketing.
