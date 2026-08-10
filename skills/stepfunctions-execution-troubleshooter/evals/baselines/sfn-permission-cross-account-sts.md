# Baseline (no-skill) response: sfn-permission-cross-account-sts

This file captures what a generic assistant produces WITHOUT the
stepfunctions-execution-troubleshooter skill loaded — the contrast
that proves the skill adds structure (deterministic VERDICT,
category-aware walk, specific remediation).

---

You're getting a States.Permission error because your Step Functions
role can't assume the cross-account role. The error says it's not
authorized to perform `sts:AssumeRole` on the foreign role.

You need to add a policy to your Step Functions role that allows
`sts:AssumeRole` on the target role ARN. Also make sure the trust
policy on the target role in account 222222222222 allows your Step
Functions role to assume it.

Cross-account setups are tricky — both sides need to allow the action.
