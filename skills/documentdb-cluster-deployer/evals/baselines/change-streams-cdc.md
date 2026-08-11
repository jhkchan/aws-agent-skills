# Baseline (no-skill) — change-streams-cdc

> This is the response a model produces **without** the skill
> definition. It creates the cluster but does not enable change streams
> (missing the parameter group configuration), does not note the 3-day
> retention value (259200 seconds), does not mention that change streams
> require a reboot to take effect, and omits the READY_TO_DEPLOY
> checklist format. Generated for with-skill-vs-baseline comparison.

---

Create the cluster for CDC:

```bash
aws docdb create-db-cluster \
  --db-cluster-identifier events-cdc \
  --engine docdb \
  --engine-version 5.0.0 \
  --master-username admin \
  --master-user-password 'Password123!' \
  --db-subnet-group-name docdb-events-sg \
  --vpc-security-group-ids sg-events-001 \
  --backup-retention-period 14
```

Then create instances and connect. Change streams should work
automatically since it's MongoDB compatible.
