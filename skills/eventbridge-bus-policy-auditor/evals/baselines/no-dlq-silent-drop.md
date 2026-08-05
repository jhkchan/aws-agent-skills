# Baseline (no-skill) response: no-dlq-silent-drop

This file captures what a generic assistant produces WITHOUT the
eventbridge-bus-policy-auditor skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, per-target DLQ
reasoning, retry-window semantics).

---

The bus policy looks reasonable — access is scoped to same-account
principals. However, the rule targets don't have dead-letter queues
configured. If the Lambda function or SQS queue fails to process after
retries, the events will be lost. You should add a DLQ to each target.

The KMS key and archive are configured which is good.
