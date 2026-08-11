# Baseline (no-skill) response: cfn-drift-deleted-iam-role

This file captures what a generic assistant produces WITHOUT the
cloudformation-drift-troubleshooter skill loaded.

---

Your `app-platform` stack is drifted because the `TaskRole` IAM role
was deleted. CloudTrail shows it was deleted by `cleanup-bot` on
August 3rd.

You can either recreate the role by updating the stack, or remove the
role from your template if it's no longer needed. To recreate, just
run `aws cloudformation update-stack` and CloudFormation will
provision a new role.

Make sure nothing else depends on the role first.
