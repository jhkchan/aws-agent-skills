# Baseline (no-skill) — event-based-cart-recovery

> This is the response a model produces **without** the skill
> definition. It creates the journey but confuses the conditional
> split with a random branch (does not evaluate the event attribute
> during the journey), assumes quiet time cancels messages instead of
> holding them, and omits the Lambda resource-based permission for
> any custom channel. Does not emit a READY_TO_DEPLOY checklist.
> Generated for with-skill-vs-baseline comparison.

---

Sure, here's the journey:

```bash
aws pinpoint create-journey --application-id app-xyz789 \
  --write-journey-request '{"Name":"AbandonedCartRecovery"}'
```

Add activities and set quiet time to drop messages at night.
