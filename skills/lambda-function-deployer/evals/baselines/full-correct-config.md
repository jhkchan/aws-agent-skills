# Baseline (no-skill) — full-correct-config

> This is the response a model produces **without** the skill definition.
> It provides a basic create-function command but misses the KMS
> encryption for environment variables, the pre-created CloudWatch log
> group with retention, the Powertools layer ARN, the on-failure
> destination configuration, and the structured checklist with
> verification commands.

---

Here's the deployment for your report generator:

```bash
# Create the execution role policy with DynamoDB + S3
# (attach AWSLambdaBasicExecutionRole + add inline policy)

# Deploy the function
aws lambda create-function \
  --function-name report-generator-prod \
  --runtime python3.12 \
  --handler generate.handler \
  --role arn:aws:iam::123456789012:role/report-generator-exec \
  --zip-file fileb://function.zip \
  --memory-size 1024 \
  --timeout 60 \
  --environment "Variables={REPORTS_TABLE=reports-table,OUTPUT_BUCKET=reports-output-prod}" \
  --tracing-config Mode=Active

# Add layers
aws lambda update-function-configuration \
  --function-name report-generator-prod \
  --layers "arn:aws:lambda:us-east-1:017000801446:layer:AWSLambdaPowertoolsPythonV3-python312-x86_64:1"

# Tags
aws lambda tag-resource \
  --resource arn:aws:lambda:us-east-1:123456789012:function:report-generator-prod \
  --tags Environment=production,Workload=report-generator
```

Make sure the execution role has DynamoDB and S3 permissions scoped to
the specific resources. You should also set up a DLQ for failed
invocations.
