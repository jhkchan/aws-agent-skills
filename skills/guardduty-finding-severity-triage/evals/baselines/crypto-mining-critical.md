# Baseline (no-skill) response: crypto-mining-critical

This file captures what a generic assistant produces WITHOUT the
guardduty-finding-severity-triage skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, context-aware escalation,
specific IR remediation).

---

This finding shows that GuardDuty detected an EC2 instance communicating
with a known cryptocurrency mining pool. This is a HIGH severity finding
(8.0 out of 10).

This likely means your EC2 instance has been compromised and someone is
using it to mine cryptocurrency. You should investigate the instance and
consider removing the mining software or terminating the instance.

You might want to check CloudTrail logs to see what other actions were
taken from this instance. Consider isolating the instance and rotating
any credentials associated with it.
