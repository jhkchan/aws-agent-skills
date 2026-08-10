# Baseline (no-skill) response: rds-multiaz-to-aurora-migration

---

Your RDS Multi-AZ setup is costing $50/month in cross-AZ replication
transfer. Aurora's Multi-AZ replication is free because it happens
at the storage layer. You could migrate from RDS PostgreSQL to
Aurora PostgreSQL to eliminate that charge.

The migration would use DMS or a native dump/restore. Aurora has
additional benefits like faster failover and more read replicas.
