# Baseline (no-skill) response: cfn-drift-modified-bucket-policy

This file captures what a generic assistant produces WITHOUT the
cloudformation-drift-troubleshooter skill loaded — the contrast
that proves the skill adds structure (deterministic VERDICT,
type-aware walk, specific remediation).

---

Your `logging-stack` is drifted because someone changed the bucket
policy on `LogsBucket`. The bucket policy now grants access to
account `111122223333` instead of the original logging principal.

To fix this, you should update your CloudFormation template to match
the new policy and run `aws cloudformation update-stack`. Or you can
manually revert the policy back to the original if the change was a
mistake.

You might also want to check who made the change in CloudTrail.
