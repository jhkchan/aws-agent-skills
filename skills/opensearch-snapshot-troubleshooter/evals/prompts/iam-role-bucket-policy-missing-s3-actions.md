# Eval prompt: iam-role-bucket-policy-missing-s3-actions

Diagnose the OpenSearch snapshot failure for the following domain.
Walk the symptom-driven diagnostic tree and emit the standard
diagnostic block (TARGET, VERDICT, REASON, LAYER, EVIDENCE,
REMEDIATION).

Symptom: `prod-logs-cluster` fails every manual snapshot attempt
with `repository_verification_exception`. The repository
`s3-backups` is registered, the IAM role trust policy is correct,
but the bucket policy is keyed to the OpenSearch service principal
instead of the snapshot role ARN.

```text
DomainName: prod-logs-cluster
EngineVersion: OpenSearch_2.13
Repository: s3-backups
Bucket: prod-os-snapshots-us-east-1
BucketRegion: us-east-1
SnapshotRoleArn: arn:aws:iam::111111111111:role/opensearch-snapshot-role
SnapshotRoleTrustPolicy: lists
  "Service": "opensearchservice.amazonaws.com"
  with aws:SourceAccount condition — CORRECT
SnapshotRoleIdentityPolicy: grants s3:PutObject, s3:GetObject,
  s3:DeleteObject, s3:ListBucket on the bucket ARN — CORRECT
BucketPolicy:
  {
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {"Service": "opensearchservice.amazonaws.com"},
        "Action": ["s3:PutObject", "s3:GetObject", "s3:ListBucket"],
        "Resource": ["arn:aws:s3:::prod-os-snapshots-us-east-1",
          "arn:aws:s3:::prod-os-snapshots-us-east-1/*"]
      }
    ]
  }
Note: Bucket policy principal is the SERVICE PRINCIPAL, not the
  snapshot role ARN. The role's session ARN does not match the
  service principal.

Last log line: "repository_verification_exception:
  [[s3-backups]] verification failed"

Verification-file check:
  s3 ls s3://prod-os-snapshots-us-east-1/s3-backups/verification-file-*
  returns one object (write succeeded), but the read-back by the
  OpenSearch S3 client fails with AccessDenied.
```

The repository registration succeeded (PUT _snapshot returned 200)
and the first snapshot failed verification. Identify the root-cause
layer and recommend the fix.
