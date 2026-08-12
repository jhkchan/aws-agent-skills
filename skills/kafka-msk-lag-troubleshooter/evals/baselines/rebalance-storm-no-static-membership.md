# Baseline (no-skill) response: rebalance-storm-no-static-membership

This file captures what a generic assistant produces WITHOUT the
kafka-msk-lag-troubleshooter skill loaded.

---

Your consumer group is showing a sawtooth lag pattern. This suggests
the consumers are periodically falling behind and then catching up.
The rolling deployment every 5 minutes is probably causing some
disruption — try spacing out the deployments or reducing the
deployment frequency.

You might also want to check if the consumers are crashing or being
OOM-killed during the deployment. Make sure the consumer pods have
graceful shutdown handling. If the session timeout is too short,
consider increasing session.timeout.ms to give consumers more time
to recover.
