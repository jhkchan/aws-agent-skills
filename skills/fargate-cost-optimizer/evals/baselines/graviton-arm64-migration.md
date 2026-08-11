# Baseline (no-skill) response: graviton-arm64-migration

This file captures what a generic assistant produces WITHOUT the
fargate-cost-optimizer skill loaded.

---

Your Java application could run on ARM64 (Graviton) which is about 20%
cheaper. Since you're using Java 21, it should be compatible. You'll
need to rebuild your Docker image for the arm64 architecture and update
your task definition to use ARM64.

There might also be some savings from Spot pricing if your workload
can tolerate interruptions. The CPU and memory usage looks fine so
you probably don't need to change those.
