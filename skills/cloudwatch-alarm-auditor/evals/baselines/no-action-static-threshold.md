# Baseline (no-skill) response: no-action-static-threshold

This file captures what a generic assistant produces WITHOUT the
cloudwatch-alarm-auditor skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, blind-spot reasoning).

---

This CloudWatch alarm monitors EC2 CPU utilization with a threshold of 80%.
The configuration looks reasonable — it uses a 5-minute period, evaluates 3
periods, and requires 2 breaching datapoints to trigger. TreatMissingData is
set to notBreaching which is appropriate.

The alarm doesn't have any actions configured though. You should add an SNS
topic or Lambda function to AlarmActions so someone gets notified when it
fires.
