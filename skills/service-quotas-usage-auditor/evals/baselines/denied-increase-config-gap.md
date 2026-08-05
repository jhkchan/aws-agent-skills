# Baseline (no-skill) response: denied-increase-config-gap

This file captures what a generic assistant produces WITHOUT the
service-quotas-usage-auditor skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, applied-vs-default reasoning).

---

This EC2 On-Demand vCPU quota is at 600 out of 1000, which is 60%
utilization. A previous request to increase to 2000 was denied. You
have a CloudWatch alarm at 80%.

Since the increase was denied, you might want to contact AWS support or
try requesting a smaller increase. You could also reduce your usage by
shutting down unused instances.
