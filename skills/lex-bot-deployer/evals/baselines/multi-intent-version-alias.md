# Baseline (no-skill) — multi-intent-version-alias

> This is the response a model produces **without** the skill
> definition. It creates the bot and intents but misses the
> build-bot-locale step before versioning, creates only one version
> (no blue-green), and does not explain the alias abstraction for
> rollback. Does not emit a READY_TO_DEPLOY checklist. Generated for
> with-skill-vs-baseline comparison.

---

Create the bot and add intents:

```bash
aws lexv2-models create-bot --bot-name MultiIntentBot
aws lexv2-models create-intent --intent-name BookFlight
```

Then create a version and alias.
