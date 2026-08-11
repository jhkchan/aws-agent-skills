# Baseline (no-skill) response: memory-pressure-cdc-stall

This file captures what a generic assistant produces WITHOUT the
dms-task-troubleshooter skill loaded.

---

Your DMS replication instance seems to be running low on memory. You
have 3 tasks running on a dms.r5.large instance. The CDC latency is
climbing on all tasks.

You should try upgrading to a larger instance type or reducing the
number of tasks on this instance. An r5.xlarge might help.
