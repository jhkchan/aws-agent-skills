# Baseline (no-skill) response: lcu-peak-dimension-new-connections

This file captures what a generic assistant produces WITHOUT the
elb-cost-optimizer skill loaded.

---

Your ALB is consuming 18 LCUs on average which is costing you about
$122/month in LCU charges. The high new connection rate of 500 per
second is the main driver. Since you have keep-alive disabled, every
request opens a new connection.

You should enable HTTP keep-alive on your nginx servers to reduce the
number of new connections. This should bring your LCU usage down
significantly.
