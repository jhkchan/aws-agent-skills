# Eval: dev-single-shard

**Difficulty:** easy
**Branch:** READY_TO_DEPLOY — dev cluster with single shard; explicit 'NO failover' notation; named ACL; TLS on

## Prompt

Provision a dev MemoryDB for Redis cluster named "dev-memorydb" in
us-east-1. Just a single shard with no replicas for functional
testing — no Multi-AZ, no failover needed. Use db.r6g.large. Engine
version 7.0. TLS on (default). Create a simple ACL "dev-acl" with
user dev-user (read-write). Snapshots 1 day. Subnet group
dev-memorydb-subnet. Security group sg-dev-memorydb inbound 6379
from sg-dev-app. Tags: Environment=dev, Workload=dev-db.
Account ID: 123456789012.
