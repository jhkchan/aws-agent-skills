# Baseline (no-skill) — service-map-correlation

> This is the response a model produces **without** the skill
> definition. It mentions the services but does not explain how the
> service map is auto-generated from trace context, omits the RUM-X-Ray
> correlation via trace IDs, and misses the OPERATION_COMPLETED
> checklist format. Generated for with-skill-vs-baseline comparison.

---

The services in the architecture are frontend, api-gateway, orders-api,
inventory-api, and payments-api. They should show up in the CloudWatch
console. X-Ray traces will show the requests.

RUM is enabled for the frontend. The traces should be visible in both
CloudWatch and X-Ray.
