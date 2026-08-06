# Eval prompt: unused-role-legacy-etl

Triage the following IAM Access Analyzer finding.
Emit the standard VERDICT block (FINDING, RESOURCE, RESOURCE_TYPE, FINDING_TYPE, VERDICT, RISK, REASON, REMEDIATION).

Finding ID: unused-role-legacy-etl
Finding type: UnusedIAMRole
Resource: arn:aws:iam::123456789012:role/legacy-etl-role
Resource type: AWS::IAM::Role
Principal: arn:aws:iam::123456789012:role/legacy-etl-role
Last accessed: 2024-10-15T00:00:00Z
Analysis period: 90 days
Status: ACTIVE
Analyzed at: 2025-01-20T08:00:00Z

Context: This role has s3:GetObject and s3:PutObject on production data buckets attached via an inline policy.
