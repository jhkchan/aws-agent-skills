# Eval: multi-service-slo-tracking

**Difficulty:** hard
**Branch:** OPERATION_COMPLETED — 5 services with per-service SLOs, aggregated CloudWatch dashboard, canary alarms, fast-burn alerts per service

## Prompt

Create multi-service SLO tracking for 5 services: orders-api,
inventory-api, payments-api, shipping-api, notification-api.
Each needs a 99.9% availability SLO over 30-day rolling interval.
Create a CloudWatch dashboard aggregating all SLO statuses.
Configure fast-burn burn rate alerts for each service to SNS topic
critical-alerts. Add canary alarms for each service endpoint.
All services have OTel instrumentation. Tags: Environment=production.
