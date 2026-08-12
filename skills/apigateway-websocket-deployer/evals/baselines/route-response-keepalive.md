# Baseline (no-skill) — route-response-keepalive

> This is the response a model produces **without** the skill
> definition. It creates the API but misses the route response
> configuration (needed for bidirectional communication), the
> 2-hour idle disconnect keepalive requirement, and the
> READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Create the WebSocket API with a sendMessage route:

```bash
aws apigatewayv2 create-api \
  --name my-bidirectional-api \
  --protocol-type WEBSOCKET \
  --route-selection-expression '$request.body.action'
```

Then add the routes and deploy.
