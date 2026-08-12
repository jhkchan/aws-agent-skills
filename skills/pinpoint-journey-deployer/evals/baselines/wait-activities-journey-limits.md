# Baseline (no-skill) — wait-activities-journey-limits

> This is the response a model produces **without** the skill
> definition. It creates the journey but uses only duration-based
> waits (missing the absolute-time option for precise cadence), does
> not account for quiet time interaction with waits, and omits the
> totalParticipantCap. Does not emit a READY_TO_DEPLOY checklist.
> Generated for with-skill-vs-baseline comparison.

---

Create the reengagement journey:

```bash
aws pinpoint create-journey --application-id app-xyz789 \
  --write-journey-request '{"Name":"ReengagementCampaign"}'
```

Add wait activities and set a daily cap.
