# Baseline (no-skill) — manual-deployment-observability

> This is the response a model produces **without** the skill definition.
> It produces a basic create-service command but misses the ARM64
> architecture specification, the manual deployment flag
> (AutoDeploymentsEnabled=false), the X-Ray tracing configuration,
> the pre-created CloudWatch log group with 90-day retention, the
> concurrency tuning (50 for CPU-heavy), the custom domain, and the
> structured checklist.

---

Here's how to deploy:

```bash
aws apprunner create-service \
  --service-name ml-tagger-prod \
  --source-configuration '{
    "ImageRepository": {
      "ImageIdentifier": "123456789012.dkr.ecr.us-east-1.amazonaws.com/ml-tagger:3.0-arm64",
      "ImageRepositoryType": "ECR",
      "ImageConfiguration": {"Port": "8500"}
    }
  }' \
  --instance-configuration Cpu=4096,Memory=16384
```

Your ML service will be deployed. You can set up X-Ray and custom
domains later in the console if needed.
