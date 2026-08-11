# Baseline (no-skill) — vpc-connection-private-rds

> This is the response a model produces **without** the skill
> definition. It connects to RDS but misses the VPC connection
> requirement for private instances, the IAM role for ENI management,
> the Enterprise edition prerequisite, and the READY_TO_DEPLOY
> checklist format. Generated for with-skill-vs-baseline comparison.

---

To connect QuickSight to RDS PostgreSQL:

1. Add PostgreSQL as a data source in QuickSight.
2. Enter the host, port, and database name.
3. Provide credentials.
4. Create your dataset and dashboard.

```bash
aws quicksight create-data-source --type POSTGRESQL --name "RDS"
```

If the database is private you might need a VPC connection.
