# Baseline (no-skill) response: single-az-dev

---

This PostgreSQL instance looks well-configured — it is private, encrypted, has
deletion protection on, and backups are enabled. The only thing to note is
that `MultiAZ: false`, so there is no standby in another AZ. If this is a dev
instance that may be acceptable, but for production you would want Multi-AZ
enabled for failover.
