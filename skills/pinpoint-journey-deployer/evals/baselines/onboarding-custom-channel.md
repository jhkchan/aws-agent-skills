# Baseline (no-skill) — onboarding-custom-channel

> This is the response a model produces **without** the skill
> definition. It creates the journey and references the custom Lambda
> channel but does not grant the Lambda resource-based permission to
> pinpoint.amazonaws.com, causing silent invocation failures at
> runtime. Does not emit a READY_TO_DEPLOY checklist. Generated for
> with-skill-vs-baseline comparison.

---

Here's the onboarding journey:

```bash
aws pinpoint create-journey --application-id app-xyz789 \
  --write-journey-request '{"Name":"UserOnboarding"}'
```

Reference the Lambda ARN in the custom activity.
