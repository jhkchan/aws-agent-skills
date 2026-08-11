# Baseline (no-skill) response: broker-count-overprovisioned

This file captures what a generic assistant produces WITHOUT the
msk-cost-optimizer skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, partition-to-broker ratio check,
minimum-3-broker HA constraint, blue/green migration plan).

---

You have 6 brokers but your total throughput is only 15 MB/s. That seems
like a lot of brokers for that workload. You could probably get by with
3 brokers since Kafka needs at least 3 for high availability. You'll
need to create a new cluster with fewer brokers and migrate your topics.
