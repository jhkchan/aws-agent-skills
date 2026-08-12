# Baseline (no-skill) response: read-only-filter

---

You're missing read-only events from CloudTrail. Check the event
selector's `ReadWriteType` setting — if it's set to `WriteOnly`,
read events are excluded. Change it to `All` to capture both read
and write events.
