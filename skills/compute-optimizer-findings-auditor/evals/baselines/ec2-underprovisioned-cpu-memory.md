# Baseline (no-skill) response: ec2-underprovisioned-cpu-memory

---

This EC2 instance (t3.small) has a Compute Optimizer finding of
Underprovisioned. The CPU utilization is 97% and memory is 92%, which
means the instance is too small for its workload.

The recommendation is to up-size to a t3.large. This will cost more per
month but should resolve the performance issues. You should check if the
application is experiencing latency or errors due to the high resource
utilization.
