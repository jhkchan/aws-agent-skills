# Baseline (no-skill) response: ecr-rescan-ready

This file captures what a generic assistant produces WITHOUT the
inspector2-coverage-operator skill loaded.

---

To enable rescan-on-push on the ECR repository:

```bash
aws ecr put-image-scanning-configuration \
  --repository-name prod-app \
  --image-scanning-configuration scanOnPush=true \
  --region us-east-1
```

Inspector will pick up the new setting automatically.
