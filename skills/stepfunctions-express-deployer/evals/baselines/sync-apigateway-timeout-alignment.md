# Baseline (no-skill) — sync-apigateway-timeout-alignment

> This is the response a model produces **without** the skill definition.
> It creates the sync Express workflow and API Gateway integration but
> leaves the API Gateway timeout at the default (10s) — when the
> workflow occasionally takes 15s, API Gateway returns 504 to the client
> while Express keeps running to completion, producing a silent retry
> that may double-charge if the integration is non-idempotent.
> Generated for with-skill-vs-baseline comparison.

---

To create the sync Express workflow fronted by API Gateway:

1. Create the state machine:
```bash
aws stepfunctions create-state-machine \
  --name checkout-api \
  --definition file://definition.json \
  --role-arn arn:aws:iam::123456789012:role/checkout-api-role \
  --type EXPRESS \
  --logging-configuration level=ALL,includeExecutionData=true
```

2. Create the API Gateway integration with StartSyncExecution.

3. Deploy and verify the API.

The workflow is ready for synchronous invocation from API Gateway.
