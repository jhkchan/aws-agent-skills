# Baseline (no-skill) — invalid-access-role

> This is the response a model produces **without** the skill definition.
> It does not flag the missing access role — the model does not know
> that App Runner requires an ECR access role for ECR-sourced services.
> It produces a create-service command that will fail at runtime.

---

Here's the deployment command:

```bash
aws apprunner create-service \
  --service-name report-api-prod \
  --source-configuration '{
    "ImageRepository": {
      "ImageIdentifier": "123456789012.dkr.ecr.us-east-1.amazonaws.com/report-api:1.2.0",
      "ImageRepositoryType": "ECR",
      "ImageConfiguration": {"Port": "8080"}
    }
  }'
```

App Runner will pull the image from ECR automatically.
