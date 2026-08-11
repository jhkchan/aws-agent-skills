# Eval prompt: cfn-drift-modified-bucket-policy

Diagnose the following CloudFormation drift report. Walk the
diagnostic decision tree and emit the standard VERDICT block
(INCIDENT, VERDICT, ROOT_CAUSE, EVIDENCE, ROOT_CAUSE_CATALOG,
RESOLUTION, REMEDIATION).

## Scenario

A CloudFormation stack `logging-stack` in `us-east-1` reports
`StackDriftStatus: DRIFTED`. `LastDriftDetectionDateTime` is
`2026-08-05T09:14:22Z`.

## Known facts

- `describe-stacks` shows `StackStatus: CREATE_COMPLETE`,
  `StackDriftStatus: DRIFTED`.
- `describe-stack-resource-drifts` shows the `LogsBucket` resource
  (`AWS::S3::Bucket`, physical id `logging-stack-logsbucket-abc`)
  with:
  - `ResourceDriftStatus: MODIFIED`
  - one `PropertyDifference` on `PropertyPath:
    /BucketPolicy/Document/Statement/0/Principal`
  - `ExpectedValue: {"Service": "logging.us-east-1.amazonaws.com"}`
  - `ActualValue: {"AWS": "arn:aws:iam::111122223333:root"}`
  - `DifferenceType: NOT_EQUAL`
- CloudTrail lookup shows a `PutBucketPolicy` event at
  `2026-08-04T22:11:48Z` by
  `arn:aws:iam::111122223333:user/dev-alice` from source IP
  `10.42.1.5`.
- `BucketPolicy` is a mutable property on `AWS::S3::Bucket` — a
  ChangeSet probe reports `Action: Modify`, `Replacement: False`.
- The cross-account grant is intentional: the dev account
  (`111122223333`) needs to write logs to this bucket.

## Symptom

The operator wants to clear the drift without breaking the
intentional cross-account grant.
