# Baseline (no-skill) response: session-start-iam-gap

This file captures what a generic assistant produces WITHOUT the
ssm-session-manager-troubleshooter skill loaded - the contrast
that proves the skill adds structure (4-layer health check,
deterministic VERDICT, fix CLI, verification step).

---

The session failed because of an AccessDenied error. Your IAM
role doesn't have permission to start a session. You need to add
`ssm:StartSession` to your role policy.

You might also want to check that the instance has the right
permissions too.
