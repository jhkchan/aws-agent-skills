# Baseline (no-skill) — proactive-rules-lambda-processor

> This is the response a model produces **without** the skill definition.
> It creates a Config rule without the Proactive flag, misses the Lambda
> resource policy granting config.amazonaws.com invoke permission, and
> does not configure the organization config rule for cross-account
> application. It also lacks the structured checklist format.

---

Create your Config rules like this:

```bash
aws configservice put-config-rule \
  --config-rule '{"ConfigRuleName":"s3-bucket-versioning-proactive","Source":{"Owner":"AWS","SourceIdentifier":"S3_BUCKET_VERSIONING_ENABLED"}}' \
  --region us-east-1
```

For the Lambda rule, create a Lambda function and point a Config rule
at it:
```bash
aws lambda create-function --function-name config-encryption-evaluator --runtime python3.12 ...
aws configservice put-config-rule --config-rule '{"ConfigRuleName":"custom-encryption-check","Source":{"Owner":"CUSTOM_LAMBDA","SourceIdentifier":"arn:aws:lambda:us-east-1:123456789012:function:config-encryption-evaluator"}}'
```
