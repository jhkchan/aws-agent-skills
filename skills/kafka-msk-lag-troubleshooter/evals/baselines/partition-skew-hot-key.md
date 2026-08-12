# Baseline (no-skill) response: partition-skew-hot-key

This file captures what a generic assistant produces WITHOUT the
kafka-msk-lag-troubleshooter skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, layer identification,
evidence-backed root cause, symptom-to-layer triage).

---

Your Kafka consumer is lagging behind. The RecordsLagMax metric is at
8 million, which means the consumer group can't keep up with the
producer rate. You should add more consumers to the consumer group to
increase parallelism. If you already have one consumer per partition,
try increasing the number of partitions on the topic.

Also check that the consumers are not CPU-bound — if they are, you
may need to scale up the consumer instances. You can also tune
fetch.min.bytes to batch more data per fetch for better throughput.
