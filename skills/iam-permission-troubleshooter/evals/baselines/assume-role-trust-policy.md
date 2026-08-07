# Baseline (no-skill) response: assume-role-trust-policy

This file captures what a generic assistant produces WITHOUT the
iam-permission-troubleshooter skill loaded.

---

The error says the cicd-runner role is not authorized to assume
deploy-target. You should check the deploy-target role's trust policy
and make sure the cicd-runner is allowed.

The trust policy currently only lists
`arn:aws:iam::222222222222:role/internal-deploy`. You need to add the
cicd-runner ARN to the Principal. Also check that the cicd-runner has
`sts:AssumeRole` permission on the target role in its own identity
policy — both sides need to allow it for cross-account.

Make sure MFA is configured if the trust policy requires it.
