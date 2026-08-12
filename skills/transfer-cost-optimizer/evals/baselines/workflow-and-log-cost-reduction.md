# Baseline (no-skill) response: workflow-and-log-cost-reduction

This file captures what a generic assistant produces WITHOUT the
transfer-cost-optimizer skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, per-file workflow cost
math, log-tier analysis, CONFIRM gate).

---

Your Transfer Family server has a 7-step managed workflow running on
5 million files per month. That's a lot of Step Functions executions!
Each step costs $0.025 per 1,000 executions, so 7 steps × 5M files =
35M state transitions, which is about $875/month in workflow charges.

You can reduce this by:
1. Combining the archival and audit-logging steps into one step (6 steps
   instead of 7).
2. Running the virus-scan and validation steps in parallel (but Step
   Functions parallel branches still count as separate transitions).

That would save you roughly $125/month on workflow costs.

Your CloudWatch Logs volume is also very high at 500 GB/month, which
costs about $250/month in ingest fees. Reducing to WARNING level would
cut that by about 80%, saving $200/month.

```
aws transfer update-server --server-id s-workflow-and-log-cost-reduction --logging-role arn:aws:iam::<acct>:role/TransferLogging
```

You'd need to update the logging configuration to reduce verbosity.
