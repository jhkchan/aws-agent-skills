# Eval prompt: bucket-policy-missing-acl-condition

Diagnose the following CloudTrail gap. Walk the BUCKET_POLICY_BLOCKING
diagnostic tree and emit the standard VERDICT block (INCIDENT, VERDICT,
ROOT_CAUSE, EVIDENCE, ROOT_CAUSE_CATALOG, REMEDIATION).

## Scenario

A CloudTrail trail named `audit-trail` claims `IsLogging: true`, but
no log files have landed in the S3 bucket for 6 hours. The account is
`111111111111`, region `us-east-1`.

## Known facts

- `aws cloudtrail get-trail-status --name audit-trail` returns:
  - `IsLogging: true`
  - `LatestDeliveryTime: empty` (no successful delivery on record)
  - `LatestDeliveryAttemptSucceeded: empty`
- `aws cloudtrail describe-trails --trail-name-list audit-trail` shows:
  - `S3BucketName: audit-logs`
  - `HomeRegion: us-east-1`
  - `KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/xyz456`
- `aws s3api get-bucket-location --bucket audit-logs` returns
  `us-east-1` (same region as the trail).
- `aws s3api get-bucket-policy --bucket audit-logs --query Policy
  --output text` returns a policy whose only CloudTrail statement is:
  ```json
  {
    "Effect": "Allow",
    "Principal": {"Service": "cloudtrail.amazonaws.com"},
    "Action": "s3:PutObject",
    "Resource": "arn:aws:s3:::audit-logs/AWSLogs/111111111111/CloudTrail/*"
  }
  ```
  There is **no** `Condition` requiring `s3:x-amz-acl:
  bucket-owner-full-control`. The `s3:GetBucketAcl` Allow statement
  is also missing from the policy.
- `aws kms get-key-policy --key-id xyz456 --policy-name default
  --query Policy --output text` shows a statement allowing
  `cloudtrail.amazonaws.com` to `kms:GenerateDataKey*` and
  `kms:DescribeKey` (KMS is fine).
- The bucket has S3 Object Ownership set to `BucketOwnerEnforced`,
  which rejects ACLs and requires the canonical CloudTrail bucket
  policy with the `bucket-owner-full-control` condition for
  CloudTrail to deliver.

## Symptom

The trail reports `IsLogging: true` but no log files appear in S3.
CloudTrail silently fails to deliver because the bucket policy is
missing the required ACL condition and the GetBucketAcl Allow.
