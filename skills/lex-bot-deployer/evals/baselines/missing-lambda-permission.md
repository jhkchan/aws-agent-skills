# Baseline (no-skill) — missing-lambda-permission

> This is the response a model produces **without** the skill
> definition. It creates the bot and wires the code hook without
> flagging that the Lambda lacks a resource-based permission granting
> lexv2.amazonaws.com invoke access. The code hook will silently fail
> at runtime. Does not emit a PREREQUISITES_MISSING verdict. Generated
> for with-skill-vs-baseline comparison.

---

Sure, here's the bot:

```bash
aws lexv2-models create-bot --bot-name BrokenHookBot
aws lexv2-models update-intent --dialog-code-hook '{"enabled":true}'
```

Build, version, and alias and you're done.
