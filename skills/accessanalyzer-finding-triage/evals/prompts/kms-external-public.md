# Eval prompt: kms-external-public

Triage the following IAM Access Analyzer finding.
Emit the standard VERDICT block (FINDING, RESOURCE, RESOURCE_TYPE, FINDING_TYPE, VERDICT, RISK, REASON, REMEDIATION).

Finding ID: kms-external-public
Finding type: ExternalAccess
Resource: arn:aws:kms:us-east-1:123456789012:key/abc123def456
Resource type: AWS::KMS::Key
Resource owner account: 123456789012
Principal: "*"
isPublic: true
Actions: ["kms:Decrypt", "kms:Encrypt", "kms:ReEncrypt*", "kms:GenerateDataKey*"]
Condition: {}
Status: ACTIVE
Created at: 2024-06-15T10:00:00Z
Analyzed at: 2025-01-20T08:00:00Z
