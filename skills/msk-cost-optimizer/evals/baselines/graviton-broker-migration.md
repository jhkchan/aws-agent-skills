# Baseline (no-skill) response: graviton-broker-migration

This file captures what a generic assistant produces WITHOUT the
msk-cost-optimizer skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, Graviton pricing math, Kafka
version prerequisite check, blue/green migration plan with
MirrorMaker2/Cluster Linking).

---

Your MSK cluster is running on kafka.m5.large brokers. AWS has Graviton-
based brokers (m7g) that are about 20% cheaper. Since you're on Kafka
3.5.1, you should be able to migrate. You'll need to create a new cluster
and move your data over.
