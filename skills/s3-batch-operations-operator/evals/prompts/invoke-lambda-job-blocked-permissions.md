# Eval prompt: invoke-lambda-job-blocked-permissions

Plan the following S3 Batch Operations Lambda invoke job and emit the
standard VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, NOTES).

Operation: create-job
Operation type: Invoke Lambda (MyObjectProcessor)
Manifest: s3://prod-manifests/objects.csv (CSV, unversioned)
Report bucket: prod-batch-reports (us-east-1)
Role: arn:aws:iam::111111111111:role/S3BatchOpsRole
RequestsPerSecond: 100

```json
{
  "Lambda": {
    "FunctionName": "MyObjectProcessor",
    "FunctionArn": "arn:aws:lambda:us-east-1:111111111111:function:MyObjectProcessor",
    "State": "Active",
    "Timeout": 60,
    "Runtime": "python3.12",
    "ReservedConcurrentExecutions": 100
  },
  "LambdaResourcePolicy": {
    "Statements": [
      {
        "Effect": "Allow",
        "Principal": {"Service": "s3.amazonaws.com"},
        "Action": "lambda:InvokeFunction"
      }
    ],
    "MissingPrincipal": "batchoperations.amazonaws.com"
  },
  "CallerPermissions": {
    "s3control:CreateJob": true,
    "iam:PassRole": "arn:aws:iam::111111111111:role/S3BatchOpsRole"
  },
  "RolePolicies": [
    "s3:GetObject on prod-data/*",
    "s3:PutObject on prod-batch-reports/*"
  ],
  "Manifest": {
    "Format": "CSV",
    "ObjectArn": "arn:aws:s3:::prod-manifests/objects.csv",
    "ETag": "present"
  },
  "ReportBucket": {"Name": "prod-batch-reports", "Region": "us-east-1"}
}
```
