# Baseline (no-skill) — journey-event-conditional-branch

> This is the response a model produces **without** the skill
> definition. It lists journey CLI commands but misses the
> CONDITIONAL_SPLIT WaitTime requirement (without it, endpoints wait
> forever for an event that may never come), does not validate the
> DAG (every path must reach END), and does not emit the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Create the journey:

```bash
aws pinpoint create-journey \
  --application-id app-abc123 \
  --write-journey-request '{"Name":"onboarding-7d"}'
```

Use the console to drag-and-drop the activities.
