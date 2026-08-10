# Eval: memcached-simple-cache

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — Memcached dev cache with cross-az node distribution; no Multi-AZ, no snapshots, no encryption (all unsupported on Memcached)

## Prompt

Provision an ElastiCache Memcached cluster named "dev-cache" in
us-east-1. This is a simple, ephemeral key-value cache — data is
disposable, cache-miss is acceptable, no failover needed, no
persistence needed. We want 3 cache.r6g.large nodes distributed
across AZs (cross-az mode) for AZ-spread. Subnet group
dev-cache-subnet spans 3 AZs. Security group sg-dev-cache inbound
11211 from sg-dev-app. Tags: Environment=dev, Workload=cache.
Account ID: 123456789012.
