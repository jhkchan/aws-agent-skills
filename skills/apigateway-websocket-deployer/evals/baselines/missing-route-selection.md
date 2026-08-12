# Baseline (no-skill) — missing-route-selection

> This is the response a model produces **without** the skill
> definition. It creates the WebSocket API without flagging the
> missing route selection expression (custom routes will never
> fire without it). Does not emit a PREREQUISITES_MISSING verdict.
> Generated for with-skill-vs-baseline comparison.

---

Sure, here's the command:

```bash
aws apigatewayv2 create-api \
  --name my-incomplete-api \
  --protocol-type WEBSOCKET
```

Then add your routes.
