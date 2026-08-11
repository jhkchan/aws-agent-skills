# Baseline (no-skill) — device-shadow-named

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the named shadow topic
> structure, the delta state mechanism, and the READY_TO_DEPLOY
> checklist format. Generated for with-skill-vs-baseline comparison.

---

Create the thing:

```bash
aws iot create-thing --thing-name actuator-001
```

Use the shadow:

```bash
aws iot-data update-thing-shadow \
  --thing-name actuator-001 \
  --payload '{"state":{"desired":{"led":"on"}}}'
```
