# Worked Examples (load on demand) — Compute Optimizer Findings Auditor

Secondary worked example (LOW-confidence inferred-memory finding), moved verbatim from SKILL.md. The primary high-confidence example stays in SKILL.md.


---

## Worked example — EC2 Overprovisioned, LOW confidence (inferred memory) (moved from SKILL.md)

```text
RESOURCE: arn:aws:ec2:us-east-1:111111111111:instance/i-0def456
VERDICT: NOT_OPTIMIZED
REASON: Finding is Overprovisioned but confidence is LOW — Memory metric is
absent (CloudWatch Agent not installed; memory inferred). performanceRisk 4
on recommended option. Cannot safely recommend right-sizing.
RISK: MEDIUM
FINDINGS:
  - [MEDIUM] Overprovisioned finding is low-confidence: CPU-only data (12%
    max). Memory utilization is inferred, not measured (Step 3, condition 1).
  - [MEDIUM] performanceRisk 4 on recommended option — right-sizing may
    cause performance regression (Step 3, condition 2).
REMEDIATION:
  1. Install the CloudWatch Agent on the instance to report actual Memory
     utilization: see AWS docs for CWAgent installation and Memory metric
     configuration.
  2. Wait 30 days for Compute Optimizer to analyse with real Memory data.
  3. Re-evaluate the finding once Memory metrics are present.
  4. Do NOT right-size based on this finding — it may be a false positive.
```
