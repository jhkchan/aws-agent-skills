# Provisioning CLI Commands Reference

Supplementary reference for the S3 Object Lambda Deployer skill.
Copy-pasteable AWS CLI v2 commands organized by provisioning step.

## Pre-flight: verify bucket and IAM state

```bash
# Bucket baseline (BPA, SSE, versioning)
aws s3api get-public-access-block --bucket <BUCKET>
aws s3api get-bucket-encryption --bucket <BUCKET>
aws s3api get-bucket-versioning --bucket <BUCKET>

# Account ID
aws sts get-caller-identity --query Account --output text

# Region
aws configure get region

# Standard AP exists (if pre-existing)
aws s3control get-access-point --account-id <ACCOUNT> --name <STANDARD_AP_NAME>
```

## Step 2: supporting standard Access Point

```bash
# Create standard AP
aws s3control create-access-point \
  --account-id <ACCOUNT> --name <STANDARD_AP_NAME> --bucket <BUCKET>

# Attach AP policy allowing the Lambda's role
aws s3control put-access-point-policy \
  --account-id <ACCOUNT> --name <STANDARD_AP_NAME> \
  --policy file://ap-policy.json
```

`ap-policy.json`:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"AWS": "arn:aws:iam::<ACCOUNT>:role/<LAMBDA_ROLE>"},
    "Action": ["s3:GetObject", "s3:GetObjectVersion"],
    "Resource": "arn:aws:s3:<REGION>:<ACCOUNT>:accesspoint/<STANDARD_AP_NAME>/*"
  }]
}
```

## Step 3: IAM execution role

```bash
aws iam create-role \
  --role-name <LAMBDA_ROLE> \
  --assume-role-policy-document file://trust-policy.json

aws iam put-role-policy \
  --role-name <LAMBDA_ROLE> \
  --policy-name ObjectLambdaExec \
  --policy-document file://exec-policy.json
```

`trust-policy.json`:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "s3-object-lambda.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

`exec-policy.json`:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect": "Allow", "Action": "s3-object-lambda:WriteGetObjectResponse", "Resource": "*"},
    {"Effect": "Allow", "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"], "Resource": "arn:aws:logs:<REGION>:<ACCOUNT>:*"},
    {"Effect": "Allow", "Action": ["s3:GetObject", "s3:GetObjectVersion"], "Resource": "arn:aws:s3:<REGION>:<ACCOUNT>:accesspoint/<STANDARD_AP_NAME>/*"}
  ]
}
```

## Step 4: transform Lambda function

```bash
# Zip the handler
zip transform.zip index.py

aws lambda create-function \
  --function-name <FUNC_NAME> \
  --runtime python3.12 \
  --role arn:aws:iam::<ACCOUNT>:role/<LAMBDA_ROLE> \
  --handler index.handler \
  --zip-file fileb://transform.zip \
  --timeout 30 --memory-size 512
```

## Step 5: reserved concurrency

```bash
aws lambda put-function-concurrency \
  --function-name <FUNC_NAME> \
  --reserved-concurrent-executions 50
```

## Step 6: Object Lambda Access Point

```bash
aws s3control create-access-point-for-object-lambda \
  --account-id <ACCOUNT> --name <OLAP_NAME> \
  --configuration SupportingAccessPoint=arn:aws:s3:<REGION>:<ACCOUNT>:accesspoint/<STANDARD_AP_NAME>
```

## Step 7: TransformationConfiguration

```bash
aws s3control put-access-point-configuration-for-object-lambda \
  --account-id <ACCOUNT> --name <OLAP_NAME> \
  --configuration '{
    "SupportingAccessPoint": "arn:aws:s3:<REGION>:<ACCOUNT>:accesspoint/<STANDARD_AP_NAME>",
    "TransformationConfigurations": [{
      "Actions": ["GetObject"],
      "ContentTransformation": {"AwsLambda": {"FunctionArn": "arn:aws:lambda:<REGION>:<ACCOUNT>:function:<FUNC_NAME>"}}
    }]
  }'
```

Multi-operation variant (GetObject + HeadObject + ListObjects):
```bash
aws s3control put-access-point-configuration-for-object-lambda \
  --account-id <ACCOUNT> --name <OLAP_NAME> \
  --configuration '{
    "SupportingAccessPoint": "arn:aws:s3:<REGION>:<ACCOUNT>:accesspoint/<STANDARD_AP_NAME>",
    "TransformationConfigurations": [
      {"Actions": ["GetObject"], "ContentTransformation": {"AwsLambda": {"FunctionArn": "arn:aws:lambda:<REGION>:<ACCOUNT>:function:<FUNC_GET>"}}},
      {"Actions": ["HeadObject"], "ContentTransformation": {"AwsLambda": {"FunctionArn": "arn:aws:lambda:<REGION>:<ACCOUNT>:function:<FUNC_HEAD>"}}}
    ]
  }'
```

## Step 8: optional features

### Multi-region Object Lambda

```bash
for REGION in us-east-1 eu-west-1 ap-southeast-2; do
  aws s3control create-access-point-for-object-lambda \
    --account-id <ACCOUNT> --name <OLAP_NAME> --region $REGION \
    --configuration SupportingAccessPoint=arn:aws:s3:$REGION:<ACCOUNT>:accesspoint/<STANDARD_AP_NAME>
done
```

### Object Lambda with GetObjectACL

```json
{"Actions": ["GetObjectACL"], "ContentTransformation": {"AwsLambda": {"FunctionArn": "arn:aws:lambda:<REGION>:<ACCOUNT>:function:<FUNC_ACL>"}}}
```

## Step 9: verification

```bash
aws s3control get-access-point --account-id <ACCOUNT> --name <STANDARD_AP_NAME>
aws s3control get-access-point-policy --account-id <ACCOUNT> --name <STANDARD_AP_NAME>
aws s3control get-access-point-for-object-lambda --account-id <ACCOUNT> --name <OLAP_NAME>
aws s3control get-access-point-configuration-for-object-lambda --account-id <ACCOUNT> --name <OLAP_NAME>
aws lambda get-function --function-name <FUNC_NAME>
aws lambda get-function-concurrency --function-name <FUNC_NAME>

# Invoke a real GET against the OLAP hostname
aws s3api get-object \
  --bucket arn:aws:s3-object-lambda:<REGION>:<ACCOUNT>:accesspoint/<OLAP_NAME> \
  --key sample.txt output.txt

# CloudWatch Lambda invocations (transform fired)
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda --metric-name Invocations \
  --dimensions Name=FunctionName,Value=<FUNC_NAME> \
  --start-time $(date -u -v1H +%Y-%m-%dT%H:%M:%SZ) --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 --statistics Sum

# CloudWatch Lambda throttles (concurrency exhausted)
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda --metric-name Throttles \
  --dimensions Name=FunctionName,Value=<FUNC_NAME> \
  --start-time $(date -u -v1H +%Y-%m-%dT%H:%M:%SZ) --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 --statistics Sum
```

## Rollback

```bash
# Delete the Object Lambda AP
aws s3control delete-access-point-for-object-lambda \
  --account-id <ACCOUNT> --name <OLAP_NAME>

# Remove the TransformationConfiguration (replace with empty)
aws s3control put-access-point-configuration-for-object-lambda \
  --account-id <ACCOUNT> --name <OLAP_NAME> \
  --configuration '{"SupportingAccessPoint":"arn:aws:s3:<REGION>:<ACCOUNT>:accesspoint/<STANDARD_AP_NAME>","TransformationConfigurations":[]}'

# Delete the Lambda function
aws lambda delete-function --function-name <FUNC_NAME>

# Delete the standard AP (if it was created for the OLAP)
aws s3control delete-access-point --account-id <ACCOUNT> --name <STANDARD_AP_NAME>

# Remove reserved concurrency
aws lambda delete-function-concurrency --function-name <FUNC_NAME>
```
