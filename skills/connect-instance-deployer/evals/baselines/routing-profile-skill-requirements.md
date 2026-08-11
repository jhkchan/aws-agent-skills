# Baseline (no-skill) — routing-profile-skill-requirements

> This is the response a model produces **without** the skill
> definition. It creates the routing profile with queue associations
> but misses the skill requirements (without skills, routing silently
> degrades to queue-priority routing) and the proficiency-level model
> (skill on instance + proficiency on agent + required proficiency on
> contact). Does not emit the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

Create the routing profile:

```bash
aws connect create-routing-profile \
  --instance-id inst-abc123 \
  --name "tier-1-sales-support" \
  --queue-configs '[{"QueueReference":{"QueueId":"sales-queue","Channel":"VOICE"},"Priority":1,"Delay":0}]'
```

Agents will be assigned via the console.
