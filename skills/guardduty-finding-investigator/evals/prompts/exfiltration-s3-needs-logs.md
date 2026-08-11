# Eval prompt: exfiltration-s3-needs-logs

Diagnose the GuardDuty finding below. Walk the finding-type-driven
diagnostic tree and emit the standard diagnostic block (FINDING, VERDICT,
REASON, LAYER, SEVERITY, EVIDENCE, SUPPRESSION, REMEDIATION). The FINDING
line must reference the test-case id `exfiltration-s3-needs-logs`.

Symptom: GuardDuty finding q7r8s9t0 in detector 12ab34cd (us-east-1).
Type `Exfiltration:S3/AnomalousBehavior.S3`, severity 7.5 (High).
Resource: S3 bucket `customer-data-prod`.

```text
aws guardduty get-findings:
  service.action.awsApiCallAction.api: "GetObject"
  service.action.awsApiCallAction.callCount: 12480
  service.action.awsApiCallImage.firstSeen: "2026-08-09T03:14:00Z"
  service.action.awsApiCallImage.lastSeen: "2026-08-09T03:58:00Z"
  resource.s3BucketDetails.name: "customer-data-prod"
  resource.accessKeyDetails.principalId: "AROA-DataWarehouseLoadRole"

CloudTrail lookup-events (GetObject in finding window):
  (no results — data events NOT enabled on customer-data-prod)

aws s3api get-bucket-logging customer-data-prod:
  (no logging configured — S3 access logs off)

aws s3api get-bucket-versioning customer-data-prod:
  Versioning: Enabled, MFA Delete: Disabled

aws cloudtrail describe-trails:
  Trail "mgmt-only": IncludeGlobalServiceEvents=true, IsLogging=true,
    but eventSelectors targetOnly management events (no data events
    for s3).

Known about the principal: DataWarehouseLoadRole is an application
role used by the analytics team for nightly ETL — but the operator
cannot confirm whether this burst is the normal nightly load or an
anomaly.
```

Emit the standard diagnostic block.
