# Baseline (no-skill) response: low-ri-coverage-steady-state

This file captures what a generic assistant produces WITHOUT the
ce-cost-anomaly-auditor skill loaded.

---

This account has $20,000/month spend with only 22% RI coverage and 12% SP
coverage. That is quite low for a steady-state EC2 workload. You are
likely paying a lot in on-demand rates that could be reduced with Reserved
Instances or Savings Plans.

The anomaly detection looks properly configured with an IMMEDIATE monitor
and subscription. CUR is enabled. I would recommend looking into purchasing
more RIs or Savings Plans to improve your coverage. A typical target might
be around 70-80% coverage for steady-state workloads.
