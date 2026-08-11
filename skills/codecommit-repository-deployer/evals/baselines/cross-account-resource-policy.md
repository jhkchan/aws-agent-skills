# Baseline (no-skill) — cross-account-resource-policy

> This is the response a model produces **without** the skill
> definition. It grants cross-account access via the repository resource
> policy but MISSES the KMS key policy cross-account grant (the #1
> cause of cross-account CodeCommit failures), resulting in
> AccessDenied when the cross-account principal tries to push or pull.
> Does not emit the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Grant cross-account access:

```bash
aws codecommit put-repository-triggers \
  --repository-name my-app-repo
```

Add a resource policy granting the other account GitPull and GitPush.
