# Baseline (no-skill) response: sfn-retry-exhausted-dynamodb

This file captures what a generic assistant produces WITHOUT the
stepfunctions-execution-troubleshooter skill loaded — the contrast
that proves the skill adds structure (deterministic VERDICT,
category-aware walk, specific remediation).

---

Your execution failed because DynamoDB returned
ProvisionedThroughputExceededException. The retries ran out.

You should either increase the DynamoDB throughput or add more retries.
Also consider adding a catch block so the execution doesn't fail
terminally when this happens.
