# Baseline (no-skill) — missing-email-channel

> This is the response a model produces **without** the skill
> definition. It creates the journey with email send activities
> without flagging that the email channel is not configured on the
> project. The send email activities will fail silently per
> participant at runtime. Does not emit a PREREQUISITES_MISSING
> verdict. Generated for with-skill-vs-baseline comparison.

---

Sure, here's the newsletter journey:

```bash
aws pinpoint create-journey --application-id app-broken456 \
  --write-journey-request '{"Name":"NewsletterJourney"}'
```

Add the send email activities and schedule.
