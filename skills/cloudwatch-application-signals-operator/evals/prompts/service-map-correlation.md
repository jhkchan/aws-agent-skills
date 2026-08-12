# Eval: service-map-correlation

**Difficulty:** hard
**Branch:** OPERATION_COMPLETED — service map auto-generated from traces, X-Ray drill-down enabled, RUM correlated via trace IDs, end-to-end observability

## Prompt

Verify service map and trace correlation for the microservices
architecture: frontend (RUM enabled), api-gateway, orders-api,
inventory-api, payments-api. Need X-Ray drill-down from SLO
status to individual traces. RUM app monitor storefront-rum
with EnableXRay true. All services have OTel SDK instrumentation.
Tags: Environment=production, Team=platform.
