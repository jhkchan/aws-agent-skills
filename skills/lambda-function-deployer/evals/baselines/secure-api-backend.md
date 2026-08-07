# Baseline (no-skill) — secure-api-backend

> This is the response a model produces **without** the skill definition.
> It provides a basic create-function command but misses the VPC NAT
> Gateway requirement for Stripe API access, the KMS decrypt permission
> on the execution role, the pre-created CloudWatch log group with
> retention, the on-failure destination, and the structured checklist.

---

Here's how to deploy your Lambda function:

```bash
# Create the function
aws lambda create-function \
  --function-name order-api-prod \
  --runtime python3.12 \
  --handler app.handler \
  --role arn:aws:iam::123456789012:role/lambda-exec-role \
  --zip-file fileb://function.zip \
  --memory-size 512 \
  --timeout 15 \
  --vpc-config SubnetIds=subnet-aaa,subnet-bbb,SecurityGroupIds=sg-orders-api \
  --environment "Variables={DB_HOST=orders-db.cluster.example.rds.amazonaws.com}"
```

Make sure the execution role has the VPC permissions and access to the
RDS instance. You'll also want to add DynamoDB or S3 permissions
depending on what else the function does.

For the Stripe API calls, the function is in a VPC so it might not have
internet access. You should check if the VPC has a NAT Gateway.

For X-Ray, you can enable it in the console or add `--tracing-config
Mode=Active`.

I'd recommend setting up a DLQ too.
