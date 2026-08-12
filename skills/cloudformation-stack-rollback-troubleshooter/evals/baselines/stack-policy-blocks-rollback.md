# Baseline (no-skill) response: stack-policy-blocks-rollback

---

Your stack rollback is failing because of a stack policy. The policy
blocks updates to RDS resources. You should remove the stack policy
or modify it to allow the rollback.

Try deleting the stack policy temporarily and then retry the rollback.
After the rollback completes, you can re-add the policy.
