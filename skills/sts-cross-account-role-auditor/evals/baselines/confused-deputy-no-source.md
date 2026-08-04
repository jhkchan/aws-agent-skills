# Baseline (no-skill) response: confused-deputy-no-source

This file captures what a generic assistant produces WITHOUT the
sts-cross-account-role-auditor skill loaded. Note: the baseline does NOT
recognize the confused-deputy problem — it treats the Lambda service
principal as a same-account trust and may classify it as safe.

---

This trust policy allows the Lambda service to assume the role. Since
`lambda.amazonaws.com` is an AWS service principal, this is a standard
pattern for Lambda execution roles.

The policy looks fine for a Lambda function that needs to assume this
role. You might want to add conditions if you want to be extra careful,
but this is a common and acceptable configuration.
