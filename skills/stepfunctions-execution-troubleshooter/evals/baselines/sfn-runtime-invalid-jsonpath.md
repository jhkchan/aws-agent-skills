# Baseline (no-skill) response: sfn-runtime-invalid-jsonpath

This file captures what a generic assistant produces WITHOUT the
stepfunctions-execution-troubleshooter skill loaded — the contrast
that proves the skill adds structure (deterministic VERDICT,
category-aware walk, specific remediation).

---

Your Step Functions workflow has a runtime error on the EnrichOrder
state. The error says "States.Runtime" which usually means a JSONPath
problem.

Looking at the state definition, the Parameters uses
`$.order.orderId` but the input only has `orderId` at the top level.
You should change it to `$.orderId`.

Also check that all the other JSONPath references in your workflow are
correct. Step Functions JSONPath can be tricky.
