# Eval prompt: trail-stopped-inadvertently

Diagnose the following CloudTrail gap. Walk the TRAIL_NOT_LOGGING
diagnostic tree and emit the standard VERDICT block (INCIDENT, VERDICT,
ROOT_CAUSE, EVIDENCE, ROOT_CAUSE_CATALOG, REMEDIATION).

## Scenario

A CloudTrail trail named `corp-trail` is producing no log files. The
operator does not remember stopping it. The account is
`111111111111`, region `us-east-1`.

## Known facts

- `aws cloudtrail get-trail-status --name corp-trail` returns:
  - `IsLogging: false`
  - `StopLoggingTime: 2026-08-09T14:00:00Z`
  - `LatestDeliveryTime: 2026-08-09T13:58:00Z`
  - `LatestDeliveryAttemptSucceeded: 2026-08-09T13:58:12Z`
- `aws cloudtrail describe-trails --trail-name-list corp-trail` shows:
  - `IsMultiRegionTrail: true`
  - `IncludeGlobalServiceEvents: true`
  - `LogFileValidationEnabled: true`
  - `S3BucketName: corp-trail-logs` (in us-east-1)
  - `KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/abc123`
- The S3 bucket policy has the canonical CloudTrail Allow statements
  (GetBucketAcl + PutObject with `bucket-owner-full-control`).
- The KMS key policy allows `cloudtrail.amazonaws.com` to
  `kms:GenerateDataKey*` on the key ARN.
- CloudTrail event history shows a `StopLogging` event at
  `2026-08-09T14:00:00Z` from IAM user `security-auditor` (an
  automated compliance script).

## Symptom

The trail configuration is correct. The trail was explicitly stopped
by an automated script yesterday. No log files have been delivered
since.
