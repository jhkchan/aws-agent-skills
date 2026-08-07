# Baseline (no-skill) response: fargate-oom-jvm-heap

This file captures what a generic assistant produces WITHOUT the
ecs-task-troubleshooter skill loaded.

---

Your Java container is running out of memory and getting OOM-killed.
The exit code 137 confirms it. You should increase the memory limit on
the container.

In the task definition, change the `memory` field to a higher value.
You could try 2048 (2 GB) or 3072 (3 GB). For Fargate, you also need
to ensure the CPU/memory combination is valid — 0.5 vCPU supports up
to 2 GB, 1 vCPU supports up to 4 GB, etc.

You may also want to check if your Java application has a memory leak.
The `-Xmx2g` flag suggests you have set a 2 GB heap, which already
exceeds your 1 GB container limit. You should reduce the `-Xmx` to
fit within the container.
