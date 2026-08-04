# Eval prompt: s3-source-arn-bounded

Triage the following IAM Access Analyzer finding.
Emit the standard VERDICT block (FINDING, RESOURCE, RESOURCE_TYPE, FINDING_TYPE, VERDICT, RISK, REASON, REMEDIATION).

Finding ID: s3-source-arn-bounded
Finding type: ExternalAccess
Resource: arn:aws:s3:::org-cloudtrail-logs
Resource type: AWS::S3::Bucket
Resource owner account: 123456789012
Principal: arn:aws:iam::999999999999:root
isPublic: false
Actions: ["s3:GetBucketAcl", "s3:PutObject"]
Condition: {"aws:SourceArn": "arn:aws:cloudtrail:us-east-1:999999999999:trail/organization-trail"}
Status: ACTIVE
Created at: 2024-06-01T10:00:00Z
Analyzed at: 2025-01-20T08:00:00Z
