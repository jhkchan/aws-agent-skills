# Baseline (no-skill) response: update-rollback-failed-needs-continue

---

Your CloudFormation stack is stuck because the IAM role can't be
deleted. The role is still attached to an instance profile. You need
to detach the role from the instance profile first.

Try removing the role from the instance profile in the IAM console,
then retry the CloudFormation rollback. If that doesn't work, you may
need to delete the role manually.
