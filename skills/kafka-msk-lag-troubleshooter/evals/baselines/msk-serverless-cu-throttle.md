# Baseline (no-skill) response: msk-serverless-cu-throttle

This file captures what a generic assistant produces WITHOUT the
kafka-msk-lag-troubleshooter skill loaded.

---

Your MSK Serverless cluster is experiencing consumer lag. The lag is
concentrated on partition 2. Since this is Serverless, the cluster
should auto-scale, so the issue is likely that your consumer can't
process fast enough. Try adding more consumers or increasing the
partition count.

The throttle metric suggests you're hitting a throughput limit. You
may need to contact AWS support to increase the capacity on your
Serverless cluster. Alternatively, reduce the producer rate to stay
within the limits.
