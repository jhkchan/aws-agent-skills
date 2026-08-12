# Eval prompt: s3-bucket-policy-missing

Diagnose the CloudTrail missing-events incident for the following
trail. Walk the symptom-driven diagnostic tree and emit the standard
diagnostic block (TARGET, VERDICT, ROOT_CAUSE, LAYER, EVIDENCE,
REMEDIATION).

Symptom: CloudTrail trail `prod-audit-trail` shows `IsLogging: true`
but no new S3 objects in the trail bucket for 4 hours. The S3 bucket
policy was updated 5 hours ago and accidentally removed the
`cloudtrail.amazonaws.com` service principal.

```text
TrailName: prod-audit-trail
S3BucketName: prod-cloudtrail-logs-bucket
IsMultiRegionTrail: true
KmsKeyId: null (no SSE-KMS)

get-trail-status --name prod-audit-trail:
  isLogging: true
  latestDeliveryTime: 2026-08-11T15:22:08Z
  (Wall clock: 2026-08-11T19:35:00Z — 4h 13min stale)

s3api get-bucket-policy --bucket prod-cloudtrail-logs-bucket:
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Sid": "AdminAccess",
        "Effect": "Allow",
        "Principal": { "AWS": "arn:aws:iam::111111111111:root" },
        "Action": "s3:*",
        "Resource": [
          "arn:aws:s3:::prod-cloudtrail-logs-bucket",
          "arn:aws:s3:::prod-cloudtrail-logs-bucket/*"
        ]
      }
    ]
  }
  NOTE: NO statement with Principal: { "Service":
  "cloudtrail.amazonaws.com" }.

s3 ls s3://prod-cloudtrail-logs-bucket/AWSLogs/111111111111/CloudTrail/:
  Last object: 2026-08-11 15:22:08
  (No objects after 15:22 UTC — when the bucket policy was updated.)
```

CloudTrail reports `IsLogging: true` regardless of whether the S3
bucket accepts PutObject. The managed service retries silently on
bucket-policy rejection.
