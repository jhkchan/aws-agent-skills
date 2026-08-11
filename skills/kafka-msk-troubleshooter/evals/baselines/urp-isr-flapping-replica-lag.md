# Baseline (no-skill) response: urp-isr-flapping-replica-lag

This file captures what a generic assistant produces WITHOUT the
kafka-msk-troubleshooter skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, category-aware walk,
specific remediation).

---

Your Kafka cluster has under-replicated partitions during high traffic
periods. This means some follower brokers can't keep up with the leader
during bursts. The ISR is shrinking and recovering.

You should check if the brokers are healthy and consider increasing the
number of brokers or upgrading the instance type. You can also look at
network connectivity between brokers.

If the problem persists, you might want to tune Kafka configuration
parameters like replica lag settings or increase network throughput.
