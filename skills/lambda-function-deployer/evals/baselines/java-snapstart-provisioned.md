# Baseline (no-skill) — java-snapstart-provisioned

> This is the response a model produces **without** the skill definition.
> It mentions SnapStart and provisioned concurrency but misses the
> ordering constraint (SnapStart requires a published version, provisioned
> concurrency requires an alias), the ECR pull permissions on the
> execution role, and the structured checklist.

---

For your Java Lambda with SnapStart:

```bash
# Create the function from ECR
aws lambda create-function \
  --function-name enterprise-api-prod \
  --package-type Image \
  --code ImageUri=123456789012.dkr.ecr.us-east-1.amazonaws.com/enterprise-api:latest \
  --role arn:aws:iam::123456789012:role/enterprise-api-exec \
  --memory-size 2048 \
  --timeout 30

# Enable SnapStart
aws lambda update-function-configuration \
  --function-name enterprise-api-prod \
  --snap-start ApplyOn=PublishedVersions

# Publish version
aws lambda publish-version --function-name enterprise-api-prod

# Create alias
aws lambda create-alias \
  --function-name enterprise-api-prod \
  --name prod \
  --function-version 1

# Provisioned concurrency
aws lambda put-provisioned-concurrency-config \
  --function-name enterprise-api-prod \
  --qualifier prod \
  --provisioned-concurrent-executions 20
```

For the 90-day CloudWatch retention, set that in the console or via
`aws logs put-retention-policy`.

The execution role needs ECR permissions to pull the image.
