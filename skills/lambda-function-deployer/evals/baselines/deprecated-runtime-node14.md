# Baseline (no-skill) — deprecated-runtime-node14

> This is the response a model produces **without** the skill definition.
> It proceeds with the deployment without flagging that nodejs14.x is a
> deprecated runtime that AWS will block or force-upgrade. It misses the
> PREREQUISITES_MISSING verdict and does not recommend a migration target.

---

Here's the command to deploy your Lambda function:

```bash
aws lambda create-function \
  --function-name legacy-processor \
  --runtime nodejs14.x \
  --handler index.handler \
  --role arn:aws:iam::123456789012:role/legacy-processor-role \
  --zip-file fileb://function.zip \
  --memory-size 256 \
  --timeout 10
```

This should create the function successfully. Make sure the zip file
exists at ./function.zip and contains index.js with a handler function.

You may also want to add CloudWatch logging permissions to the
execution role if they're not already there.
