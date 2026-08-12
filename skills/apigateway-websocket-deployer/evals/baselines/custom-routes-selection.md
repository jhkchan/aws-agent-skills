# Baseline (no-skill) — custom-routes-selection

> This is the response a model produces **without** the skill
> definition. It creates routes but misses that the route selection
> expression must match the client message format, the DynamoDB
> connection management requirement, and the READY_TO_DEPLOY
> checklist format. Generated for with-skill-vs-baseline comparison.

---

Create the WebSocket API and add routes:

```bash
aws apigatewayv2 create-api \
  --name my-collab-api \
  --protocol-type WEBSOCKET \
  --route-selection-expression '$request.body.action'

aws apigatewayv2 create-route \
  --api-id <api-id> \
  --route-key sendMessage \
  --target integrations/<id>
```

Then deploy to a stage.
