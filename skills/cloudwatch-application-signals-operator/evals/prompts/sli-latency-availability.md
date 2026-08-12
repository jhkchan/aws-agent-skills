# Eval: sli-latency-availability

**Difficulty:** hard
**Branch:** OPERATION_COMPLETED — SLI auto-derivation from traces, operation-level latency targets (P99), anomaly detection on latency, availability SLI

## Prompt

Verify SLI metrics for service checkout-api. Operations:
GET /cart, POST /checkout, GET /order-status. Need latency SLI
(P99 < 500ms for POST /checkout, P99 < 200ms for GET endpoints)
and availability SLI (99.95% all operations). Enable anomaly
detection on latency P99. OTel auto-instrumentation via CloudWatch
Agent is configured. Tags: Environment=production, Team=checkout.
