# Eval prompt: artifact-s3-permission-denied

Diagnose the CodeBuild build failure for the following project. Walk
the phase-status-driven diagnostic tree and emit the standard
diagnostic block (TARGET, VERDICT, REASON, ROOT_CAUSE, EVIDENCE,
REMEDIATION).

Symptom: project `cb-web-frontend` completes all buildspec phases
successfully but fails at UPLOAD_ARTIFACTS with "Access Denied" when
uploading to the S3 artifacts bucket.

```text
ProjectName: cb-web-frontend
BuildId: cb-web-frontend:ghi78901
Phases:
  INSTALL: SUCCEEDED
  PRE_BUILD: SUCCEEDED
  BUILD: SUCCEEDED
  POST_BUILD: SUCCEEDED
  UPLOAD_ARTIFACTS: FAILED
Artifacts:
  Type: S3
  Location: codebuild-artifacts-prod-us-east-1
  Packaging: ZIP
  EncryptionDisabled: false
ServiceRole: arn:aws:iam::333333333333:role/service-role-cb-web-frontend
ServiceRolePolicies:
  - AWSCodeBuildReadOnlyAccess (managed)
  - inline: { logs: logs:CreateLogStream, logs:PutLogEvents }
ServiceRole S3 permissions on artifacts bucket: NOT PRESENT
EncryptionKey: arn:aws:kms:us-east-1:333333333333:key/prod-key

Phase details:
  phaseType: UPLOAD_ARTIFACTS
  phaseStatus: FAILED
  contexts[0].message: "Access Denied"
```

The build completed all command phases successfully. The failure is
isolated to artifact upload. The service role has no S3 permissions
on the artifacts bucket. Check whether KMS is also a factor or whether
S3 is the sole issue.
