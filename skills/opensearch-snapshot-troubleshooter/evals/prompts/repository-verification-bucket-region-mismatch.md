# Eval prompt: repository-verification-bucket-region-mismatch

Diagnose the OpenSearch snapshot repository registration failure for
the following domain. Walk the symptom-driven diagnostic tree and
emit the standard diagnostic block (TARGET, VERDICT, REASON, LAYER,
EVIDENCE, REMEDIATION).

Symptom: cross-region snapshot repository `cross-region-dr-repo`
registration returns 200 on `PUT _snapshot` but the first
verification call returns `repository_verification_exception`. The
S3 bucket is in us-west-2; the OpenSearch domain is in us-east-1.

```text
DomainName: prod-logs-cluster
EngineVersion: OpenSearch_2.13
DomainRegion: us-east-1
Repository: cross-region-dr-repo
Bucket: prod-os-snapshots-us-west-2
BucketRegion: us-west-2 (verified via s3 get-bucket-location)
SnapshotRoleArn: arn:aws:iam::111111111111:role/opensearch-snapshot-role

PUT _snapshot body used:
  {
    "type": "s3",
    "settings": {
      "bucket": "prod-os-snapshots-us-west-2",
      "base_path": "dr-repo",
      "iam_role_arn": "arn:aws:iam::111111111111:role/opensearch-snapshot-role",
      "compress": true
    }
  }
Note: the "region" field is OMITTED. The OpenSearch S3 client
  defaults to the domain's Region (us-east-1) and tries to resolve
  prod-os-snapshots-us-west-2 in us-east-1, which fails.

Snapshot role trust policy: CORRECT (lists
  opensearchservice.amazonaws.com with aws:SourceAccount).
Snapshot role identity policy: CORRECT (full S3 access on bucket).
Bucket policy: CORRECT (grants the snapshot role ARN full S3).

Last log line: "repository_verification_exception:
  [[cross-region-dr-repo]] verification failed
  (S3Exception: Forbidden / bucket region does not match
  endpoint region)"
```

IAM (role trust, role identity policy, bucket policy) is all
correct. Identify the registration-level root cause and the fix.
