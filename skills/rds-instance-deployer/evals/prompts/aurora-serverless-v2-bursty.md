# Eval: aurora-serverless-v2-bursty

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — Serverless v2 with MinCapacity=2 (no cold-start), MaxCapacity=32

## Prompt

Provision an Aurora PostgreSQL Serverless v2 cluster for a multi-tenant
SaaS workload in us-east-1. Cluster name "saas-tenant-db". Engine
aurora-postgresql 16.3. Traffic is bursty — quiet at night, spikes
during business hours. MinCapacity 2 (avoid cold-start latency for
production), MaxCapacity 32. Use KMS customer-managed CMK
alias/saas-rds-key. 7-day backup retention. Enhanced Monitoring 30s.
Performance Insights on. Force SSL via cluster parameter group.
Deletion protection on. DB subnet group "prod-db-subnet-group" spans
3 AZs. App SG "sg-saas-app" inbound on 5432.
Tags: Environment=production, Workload=saas-multitenant.
Account ID: 123456789012.
