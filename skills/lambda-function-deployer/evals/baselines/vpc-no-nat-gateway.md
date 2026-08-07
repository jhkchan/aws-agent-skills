# Baseline (no-skill) — vpc-no-nat-gateway

> This is the response a model produces **without** the skill definition.
> It deploys the VPC-attached function without flagging that the private
> subnets have no NAT Gateway, meaning the function will silently fail
> to reach the external webhook endpoint. It misses the
> PREREQUISITES_MISSING verdict.

---

To deploy your Lambda function in a VPC:

```bash
aws lambda create-function \
  --function-name webhook-sender \
  --runtime nodejs20.x \
  --handler index.handler \
  --role arn:aws:iam::123456789012:role/lambda-vpc-role \
  --zip-file fileb://function.zip \
  --memory-size 512 \
  --timeout 10 \
  --vpc-config SubnetIds=subnet-private-a,subnet-private-b,SecurityGroupIds=sg-default
```

The function will be able to access resources in the VPC. Make sure
the security group allows outbound HTTPS (port 443) to the partner
API endpoint.

You might need to update the route tables if there are any issues
reaching external endpoints.
