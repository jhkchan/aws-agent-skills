# Baseline (no-skill) — lambda-authorizer-waf

> This is the response a model produces **without** the skill
> definition. It creates the API but does not address how to attach
> a Lambda custom authorizer to the $connect route, WAF integration
> with the WebSocket stage, the identity source configuration, or
> the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Create the WebSocket API and add an authorizer Lambda:

```bash
aws apigatewayv2 create-api \
  --name my-secure-ws-api \
  --protocol-type WEBSOCKET
```

Set up a Lambda function for auth and attach it.
