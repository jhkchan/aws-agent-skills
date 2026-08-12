# Baseline (no-skill) — custom-slotype-confirmation-closing

> This is the response a model produces **without** the skill
> definition. It creates the bot with custom slot types but misses
> the confirmation/closing/failure prompt configuration, does not set
> explicit slot priorities, and wires only the fulfillment hook.
> Does not emit a READY_TO_DEPLOY checklist. Generated for
> with-skill-vs-baseline comparison.

---

Create the bot and slot types:

```bash
aws lexv2-models create-bot --bot-name PizzaOrderBot
aws lexv2-models create-slot-type --slot-type-name PizzaSize
```

Then add the intent and wire the Lambda.
