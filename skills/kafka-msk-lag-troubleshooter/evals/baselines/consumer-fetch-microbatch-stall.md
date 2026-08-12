# Baseline (no-skill) response: consumer-fetch-microbatch-stall

This file captures what a generic assistant produces WITHOUT the
kafka-msk-lag-troubleshooter skill loaded.

---

Your consumer lag is growing on the user-events topic. Since the
consumer is not CPU-bound and the downstream is fast, this might be a
network issue or the broker is slow. Try increasing the number of
consumers or partitions.

You could also check the consumer config — make sure max.poll.records
is high enough and that the consumer is polling frequently enough. If
the topic volume is low, the consumer might just be idle most of the
time, which is normal. Consider whether you really need 6 consumers
for such a low-volume topic.
