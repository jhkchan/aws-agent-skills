# Baseline (no-skill) response: opensearch-circuit-breaker

This file captures what a generic assistant produces WITHOUT the
kinesis-firehose-troubleshooter skill loaded - the contrast that
proves the skill adds structure (5-layer health check,
deterministic VERDICT, fix CLI, verification step).

---

Firehose can't deliver to OpenSearch because the cluster is in
RED health. The circuit breaker has engaged after sustained 429
responses. Two data nodes are below the disk watermark.

You need to fix the OpenSearch cluster - free up disk space,
add storage, or clean up old indices. Once the cluster is back
to GREEN, Firehose should resume automatically.
