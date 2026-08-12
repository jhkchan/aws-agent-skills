# Baseline (no-skill) response: cross-account-repo-policy-missing

---

Your ECS task can't pull the image because it's in a different account.
Add `ecr:BatchGetImage` and `ecr:GetDownloadUrlForLayer` to the IAM
role of your ECS task. Also make sure the ECR repository policy allows
the other account to pull. You may need to add a resource-based policy
to the repository.

Run `aws ecr set-repository-policy` to add a statement allowing the
caller's account.
