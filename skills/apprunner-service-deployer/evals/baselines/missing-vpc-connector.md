# Baseline (no-skill) — missing-vpc-connector

> This is the response a model produces **without** the skill definition.
> It misses the VPC connector requirement entirely — the model does not
> know that App Runner needs a VPC connector to reach private VPC
> resources. It produces a create-service command that will deploy but
> the app will silently fail to connect to the database.

---

Here's the command to deploy your App Runner service:

```bash
aws apprunner create-service \
  --service-name internal-api-prod \
  --source-configuration '{
    "ImageRepository": {
      "ImageIdentifier": "123456789012.dkr.ecr.us-east-1.amazonaws.com/internal-api:1.0.0",
      "ImageRepositoryType": "ECR",
      "ImageConfiguration": {"Port": "8080"}
    }
  }'
```

Your service should be able to connect to the Aurora cluster since
it's in the same region.
