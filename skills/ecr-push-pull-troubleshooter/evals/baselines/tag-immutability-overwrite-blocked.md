# Baseline (no-skill) response: tag-immutability-overwrite-blocked

---

Your repository has tag immutability enabled, so you can't overwrite
the `latest` tag. You can either use a unique tag for each build
(recommended), or disable immutability:

```
aws ecr put-image-tag-mutability --repository-name tag-immutability-overwrite-blocked --image-tag-mutability MUTABLE
```

Using unique tags like `v1.0.1` or a git SHA is better practice
anyway.
