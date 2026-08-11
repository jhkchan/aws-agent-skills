# Eval prompt: enable-acceleration-standard-bucket-ready

Plan the following S3 Transfer Acceleration enable operation and emit
the standard VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS,
STEPS, POST_VERIFY, COST, NOTES).

Operation: enable-acceleration
BucketName: prod-data-lake
Region: us-east-1

```json
{
  "Bucket": "prod-data-lake",
  "HeadBucket": {"Status": 200},
  "BucketLocation": {"LocationConstraint": "us-east-1"},
  "AccelerateConfiguration": {"Status": "Suspended"},
  "InFlightMultipartUploads": {"Uploads": []},
  "CallingIdentity": "arn:aws:iam::111111111111:role/S3Admin",
  "IAMPermissions": ["s3:PutAccelerateConfiguration", "s3:GetAccelerateConfiguration"],
  "Uploaders": ["Tokyo", "Singapore", "Sydney", "Sao Paulo"]
}
```
