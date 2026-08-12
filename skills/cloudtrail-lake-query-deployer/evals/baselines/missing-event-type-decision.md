# Baseline (no-skill) — missing-event-type-decision

> This is the response a model produces **without** the skill
> definition. It creates the EDS without flagging the missing event
> type decision as a prerequisite failure. The EDS type would be
> immutable. Does not emit a PREREQUISITES_MISSING verdict. Generated
> for with-skill-vs-baseline comparison.

---

Sure, here's the EDS:

```bash
aws cloudtrail create-event-data-store --name "undecided-eds"
```

You can decide event types later.
