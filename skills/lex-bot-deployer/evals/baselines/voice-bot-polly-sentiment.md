# Baseline (no-skill) — voice-bot-polly-sentiment

> This is the response a model produces **without** the skill
> definition. It creates the bot but misses the Polly neural engine
> selection (uses standard by default), does not wire the Lambda
> resource-based permission for the code hook, and inlines Twilio
> credentials instead of referencing Secrets Manager. Does not emit
> a READY_TO_DEPLOY checklist. Generated for with-skill-vs-baseline
> comparison.

---

Create the bot:

```bash
aws lexv2-models create-bot --bot-name CustomerSupportBot
```

Then add intents and wire the Lambda. For Twilio, put the SID and
token in your Lambda environment variables.
