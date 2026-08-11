# Baseline (no-skill) — segment-zero-endpoints-prereq

> This is the response a model produces **without** the skill
> definition. It creates the campaign against a segment that resolves
> to 0 endpoints without flagging the prerequisite failure (the
> campaign would reach no one). Does not emit a PREREQUISITES_MISSING
> verdict. Generated for with-skill-vs-baseline comparison.

---

Sure, here's the campaign:

```bash
aws pinpoint create-campaign \
  --application-id app-abc123 \
  --write-campaign-request '{"Name":"empty-campaign","SegmentId":"empty-segment-001"}'
```

Schedule it for immediate send.
