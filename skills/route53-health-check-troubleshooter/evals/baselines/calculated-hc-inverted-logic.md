# Baseline (no-skill) response: calculated-hc-inverted-logic

---

Your calculated health check is reporting unhealthy even though both
child checks are healthy. This is unusual. Check the health check
configuration — there might be a logic error in how the calculated
check is set up.

Make sure both child health check IDs are correct and that they're
actually the checks you think they are. You should also verify the
routing policy is correctly configured for failover. If the primary
endpoint is working, the health check shouldn't be reporting
unhealthy.
