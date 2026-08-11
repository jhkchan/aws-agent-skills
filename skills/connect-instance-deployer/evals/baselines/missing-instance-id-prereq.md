# Baseline (no-skill) — missing-instance-id-prereq

> This is the response a model produces **without** the skill
> definition. It attempts to create the contact flow without flagging
> the missing instance ID (contact flows are children of an instance;
> the create-contact-flow API requires --instance-id). Does not emit a
> PREREQUISITES_MISSING verdict. Generated for with-skill-vs-baseline
> comparison.

---

Here's the contact flow:

```bash
aws connect create-contact-flow \
  --name "inbound-main-flow" \
  --type CONTACT_FLOW \
  --content '{"Actions":[]}'
```

You'll need to fill in the Lambda ARN and queue IDs.
