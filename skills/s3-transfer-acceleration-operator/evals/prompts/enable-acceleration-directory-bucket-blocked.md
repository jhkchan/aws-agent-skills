# Eval prompt: enable-acceleration-directory-bucket-blocked

Plan the following S3 Transfer Acceleration enable operation and emit
the standard VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS,
STEPS, POST_VERIFY, COST, NOTES).

Operation: enable-acceleration
BucketName: my-express-bucket--xaz-use1-az1
Region: us-east-1

```json
{
  "Bucket": "my-express-bucket--xaz-use1-az1",
  "HeadBucket": {"Status": 200},
  "BucketLocation": {"LocationConstraint": "us-east-1"},
  "BucketType": "directory (S3 Express One Zone)",
  "AccelerateConfiguration": {"Status": null},
  "CallingIdentity": "arn:aws:iam::111111111111:role/S3Admin",
  "IAMPermissions": ["s3:PutAccelerateConfiguration"]
}
```
