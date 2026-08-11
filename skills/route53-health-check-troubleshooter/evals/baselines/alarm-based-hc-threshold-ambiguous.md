# Baseline (no-skill) response: alarm-based-hc-threshold-ambiguous

---

Your alarm-based health check isn't triggering failover. Check that
the CloudWatch alarm is in ALARM state — Route 53 only fails over
when the alarm is ALARM, not INSUFFICIENT_DATA or OK. You should
verify the alarm configuration and check the alarm history.

Also make sure the alarm metric is actually monitoring the right
thing. If the endpoint is unhealthy but the alarm metric doesn't
reflect that, the alarm won't fire.
