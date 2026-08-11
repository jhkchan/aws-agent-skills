# Eval prompt: s3-bpa-failed-true-positive

Diagnose the Security Hub finding below. Walk the standard-driven
decision tree and emit the standard diagnostic block (FINDING, VERDICT,
REASON, LAYER, SEVERITY, STANDARD, EVIDENCE, SUPPRESSION, REMEDIATION).
The FINDING line must reference the test-case id
`s3-bpa-failed-true-positive`.

Symptom: Security Hub finding
`arn:aws:securityhub:us-east-1:111111111111:finding/abc123def` in
account 111111111111 (us-east-1). Control S3.1, severity HIGH,
Compliance.Status=FAILED.

```text
aws securityhub get-findings:
  GeneratorId: "...standards/aws-foundational-security-best-practices/v/1.0.0/S3.1"
  Resources[0].Id: arn:aws:s3:::customer-data-prod
  Resources[0].Type: AwsS3Bucket
  Severity.Label: HIGH
  Compliance.Status: FAILED
  Workflow.Status: NEW

aws s3control get-public-access-block --account-id 111111111111:
  BlockPublicAcls: true
  IgnorePublicAcls: false
  BlockPublicPolicy: true
  RestrictPublicBuckets: false

aws s3api get-bucket-acl --bucket customer-data-prod:
  Grants: [{ Grantee: { Type: Group, URI: AllUsers },
             Permission: READ }]

aws s3api get-bucket-policy customer-data-prod (parsed):
  no Principal: "*" grant

CloudFront distributions in account 111111111111:
  (none — customer-data-prod is not a CloudFront origin)

S3 access logs for customer-data-prod (last 7 days):
  all source IPs are corporate CIDR 198.18.0.0/15 — no public
  consumer pattern

Application code review: bucket is referenced by the internal
reporting tool only; no signed-URL distribution pattern.
```

Emit the standard diagnostic block.
