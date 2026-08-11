# Eval: t3-development-cluster

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — dev cluster, t3.medium single instance, engine 4.0, 1-day backup, no change streams

## Prompt

Create a DocumentDB cluster named dev-docdb in us-east-1 for
development. Engine 4.0. Instance class db.t3.medium with 1
instance only. Backup 1 day. Subnet group docdb-dev-subnet.
Security group sg-dev-docdb (port 27017 from 10.99.0.0/16).
Tags: Environment=development.
