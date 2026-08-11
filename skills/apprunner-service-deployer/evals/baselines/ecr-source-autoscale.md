# Baseline (no-skill) — ecr-source-autoscale

> This is the response a model produces **without** the skill definition.
> It produces a basic create-service command but misses the separate
> access role vs instance role distinction (often conflated), the VPC
> connector requirement for RDS access, the pre-created CloudWatch log
> group with retention, the X-Ray tracing configuration, the health
> check policy, the custom auto-scaling configuration, and the structured
> checklist.

---

Here's how to deploy your App Runner service:

```bash
aws apprunner create-service \
  --service-name checkout-api-prod \
  --source-configuration '{
    "ImageRepository": {
      "ImageIdentifier": "123456789012.dkr.ecr.us-east-1.amazonaws.com/checkout-api:2.1.0",
      "ImageRepositoryType": "ECR",
      "ImageConfiguration": {"Port": "8080"}
    }
  }'
```

Make sure your instance has enough CPU and memory. Use 2 vCPU and
4 GB for this API.

For the DB password, you can set it as an environment variable.

If you want auto-scaling, you can configure it after the service is
created.

You'll also want to set up a custom domain in the console.
