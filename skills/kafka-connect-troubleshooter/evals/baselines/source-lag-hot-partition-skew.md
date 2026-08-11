# Baseline (no-skill) response: source-lag-hot-partition-skew

This file captures what a generic assistant produces WITHOUT the
kafka-connect-troubleshooter skill loaded.

---

Your connector is running but lag is growing. This usually means the
connector can't keep up with the data. You should increase the
number of tasks or workers to add more parallelism.

Try setting tasks.max to a higher number.
