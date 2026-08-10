# Baseline (no-skill) response: cp-cross-account-role-trust-expired

This file captures what a generic assistant produces WITHOUT the
codepipeline-failure-troubleshooter skill loaded — the contrast
that proves the skill adds structure (deterministic VERDICT,
category-aware walk, specific remediation).

---

Your cross-account deploy is failing because the pipeline can't
assume the role in the target account. The error says
`sts:AssumeRole` was denied.

You need to update the trust policy on the `cross-acct-deploy` role
in account 222222222222 to allow your pipeline's service role to
assume it. Looks like the trust policy still has the old role name
from before the rename — change it to the new pipeline service role
ARN and it should work.

After updating the trust policy, retry the pipeline.
