# Baseline (no-skill) response: cfn-create-iam-capability-missing

This file captures what a generic assistant produces WITHOUT the
cloudformation-stack-troubleshooter skill loaded — the contrast
that proves the skill adds structure (deterministic VERDICT,
category-aware walk, specific remediation).

---

Your CloudFormation stack `app-platform` failed because it has an IAM
role in it. CloudFormation needs you to acknowledge IAM capabilities
when a template creates IAM resources.

Try adding `--capabilities CAPABILITY_IAM` to your create-stack
command. Also, since the stack is in ROLLBACK_COMPLETE, you may need
to delete it first before re-creating it.

Double-check your template for any other IAM resources too.
