# Baseline (no-skill) response: parameter-group-mismatch-standby

---

The standby failed health checks during promotion because of a
parameter group mismatch. The primary uses a custom parameter group
but the standby uses the default. You need to update the standby's
parameter group to match the primary's.

After aligning the parameter groups, you should retry the failover.
