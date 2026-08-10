# Baseline (no-skill) response: invoke-lambda-job-blocked-permissions

This file captures what a generic assistant produces WITHOUT the
s3-batch-operations-operator skill loaded.

---

To create a Batch Operations job that invokes a Lambda function:

```bash
aws s3control create-job \
  --account-id 111111111111 \
  --region us-east-1 \
  --priority 50 \
  --role-arn arn:aws:iam::111111111111:role/S3BatchOpsRole \
  --operation '{"LambdaInvoke": {"FunctionArn": "arn:aws:lambda:us-east-1:111111111111:function:MyObjectProcessor"}}' \
  --manifest '{"Spec":{"Format":"CSV"},"Location":{"ObjectArn":"arn:aws:s3:::prod-manifests/objects.csv"}}' \
  --report '{"Bucket":"arn:aws:s3:::prod-batch-reports","Format":"Report_CSV_20180820"}'
```

Make sure the Lambda has permissions for Batch Operations to invoke
it. You can check the Lambda's resource policy with
`aws lambda get-policy`.
