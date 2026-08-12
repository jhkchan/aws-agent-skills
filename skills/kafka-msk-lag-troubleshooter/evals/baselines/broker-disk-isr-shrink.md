# Baseline (no-skill) response: broker-disk-isr-shrink

This file captures what a generic assistant produces WITHOUT the
kafka-msk-lag-troubleshooter skill loaded.

---

Your consumer group is lagging. The lag is growing because the
consumers can't process messages fast enough. You should check that
the consumers have enough CPU and memory. If the consumers are slow,
try increasing the number of consumer instances.

The NOT_ENOUGH_REPLICAS error in the producer logs suggests there
might be a Kafka configuration issue. You could try reducing
min.insync.replicas to 1 temporarily, or changing the producer acks
setting to 1 instead of all. Also check if any brokers are down.
