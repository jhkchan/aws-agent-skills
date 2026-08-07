# Eval: aurora-postgres-production

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — all checklist items verified, Aurora cluster spanning 3 AZs with reader failover

## Prompt

Provision an Aurora PostgreSQL production cluster in us-east-1 for
an OLTP orders workload. Cluster name: "prod-orders-pg". Engine
aurora-postgresql 16.3. Instance class db.r7g.large. Use KMS
customer-managed CMK alias/prod-rds-key. Need a writer + 2 readers
across us-east-1a/b/c for read-scaling and failover. 14-day backup
retention. Enhanced Monitoring at 30s interval. Performance Insights
on. Force SSL via parameter group. Add pgaudit option. Deletion
protection on. Master credentials via Secrets Manager.
DB subnet group "prod-db-subnet-group" spans 3 AZs. App SG
"sg-prod-app" should be the only inbound on port 5432.
Tags: Environment=production, Workload=orders.
Account ID: 123456789012.
