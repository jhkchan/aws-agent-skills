# Eval: mysql-multi-az-commerce

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — non-Aurora Multi-AZ with synchronous standby + tuned parameter group

## Prompt

Provision a MySQL 8.0 RDS instance for a commerce workload in
us-east-1. Instance identifier: "commerce-mysql-prod". Instance
class db.m7g.large. Multi-AZ (synchronous standby). Storage 200 GB
gp3 with 6000 IOPS. Use KMS customer-managed CMK alias/commerce-rds-key.
Backup retention 7 days. Enhanced Monitoring 30s. Performance Insights
on. Parameter group: tune innodb_buffer_pool_size and
max_connections=500. Force secure transport. Auto minor version upgrade
on. Deletion protection on. DB subnet group "prod-db-subnet-group"
spans 2 AZs. App SG "sg-commerce-app" inbound on 3306.
Tags: Environment=production, Workload=commerce.
Account ID: 123456789012.
