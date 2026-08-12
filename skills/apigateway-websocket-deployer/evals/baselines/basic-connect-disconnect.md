# Baseline (no-skill) — basic-connect-disconnect

> This is the response a model produces **without** the skill
> definition. It creates the WebSocket API and routes but misses
> the DynamoDB ConnectionId storage requirement (the application
> must store ConnectionIds on $connect for PostToConnection), the
> ApiGatewayManagementApi SDK requirement (not ApiGatewayV2), the
> Lambda resource-based policy for apigateway invoke, and the
> READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Create the WebSocket API:

```bash
aws apigatewayv2 create-api \
  --name my-chat-api \
  --protocol-type WEBSOCKET
```

Then add $connect and $disconnect routes with Lambda integrations.
