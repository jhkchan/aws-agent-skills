# Baseline (no-skill) — coffee-order-dialog-codehook

> This is the response a model produces **without** the skill
> definition. It creates the bot but misses the slot priority ordering
> (declares slots without explicit priorities), wires only
> FULFILLMENT_CODE_HOOK (missing DIALOG_CODE_HOOK dialog management),
> does not grant the Lambda resource-based permission to
> lexv2.amazonaws.com, and skips the build/version/alias blue-green
> steps. Does not emit a READY_TO_DEPLOY checklist. Generated for
> with-skill-vs-baseline comparison.

---

Sure, here's how to create the bot:

```bash
aws lexv2-models create-bot --bot-name OrderCoffeeBot
aws lexv2-models create-intent --intent-name OrderCoffee
```

Then add slots and wire the Lambda fulfillment hook.
