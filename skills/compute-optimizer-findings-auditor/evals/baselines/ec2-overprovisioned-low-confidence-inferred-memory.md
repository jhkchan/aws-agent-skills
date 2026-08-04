# Baseline (no-skill) response: ec2-overprovisioned-low-confidence-inferred-memory

---

This EC2 instance (m5.xlarge) has an Overprovisioned finding. The CPU is
at 12% maximum, so the recommendation is to right-size to a t3.medium
which would save about $95 per month.

The performance risk is 4 which is somewhat high, so you may want to test
the change before applying it to production. The memory data is not
available since the CloudWatch Agent is not installed.

You should consider right-sizing this instance and also installing the
CloudWatch Agent for better visibility into memory usage.
