# Eval: weighted-canary-with-health-checks

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — weighted with HCs on both records, atomic POST

## Prompt

Provision a weighted routing policy in hosted zone Z2DABCDEFGHIJK
(example.com) for record "api.example.com" type A. Primary target
10.0.0.10 weight 90 with health check on HTTPS /healthz interval
30s threshold 3. Canary target 10.0.0.20 weight 10 with its own
health check on the same path. Atomic change-batch. TTL 60s for
fast canary re-normalization.
