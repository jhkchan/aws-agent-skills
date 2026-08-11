# Baseline (no-skill) — standard-repo-with-kms

> This is the response a model produces **without** the skill
> definition. It creates the repository but misses the KMS key policy
> requirement (the key policy must grant codecommit.amazonaws.com),
> the approval rule template association step (template alone does
> nothing without association), the branch protection IAM policy
> requirement, and the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Create the repository:

```bash
aws codecommit create-repository \
  --repository-name my-app-repo \
  --repository-description "Microservice repository for my-app"
```

Then set up the KMS key and approval rules.
