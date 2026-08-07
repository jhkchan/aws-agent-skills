# Baseline (no-skill) response: too-many-connections-aurora-derived

---

You're hitting the maximum connections limit on the Aurora MySQL writer.
Since the parameter-group override didn't work, Aurora is using the
derived limit based on the instance class. You should either upgrade to
a larger instance class (like db.r6i.2xlarge) or use RDS Proxy to pool
connections.

Existing connections still work, so this isn't urgent — but new
connections will keep failing until you take action.
