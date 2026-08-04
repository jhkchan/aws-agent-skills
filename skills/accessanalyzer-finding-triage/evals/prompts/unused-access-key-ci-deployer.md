# Eval prompt: unused-access-key-ci-deployer

Triage the following IAM Access Analyzer finding.
Emit the standard VERDICT block (FINDING, RESOURCE, RESOURCE_TYPE, FINDING_TYPE, VERDICT, RISK, REASON, REMEDIATION).

Finding ID: unused-access-key-ci-deployer
Finding type: UnusedIAMUserAccessKey
Resource: arn:aws:iam::123456789012:user/ci-deployer
Resource type: AWS::IAM::User
Principal: arn:aws:iam::123456789012:user/ci-deployer
Access key ID: AKIAIOSFODNN7EXAMPLE
Last accessed: 2024-09-20T00:00:00Z
Analysis period: 90 days
Status: ACTIVE
Analyzed at: 2025-01-20T08:00:00Z

Context: The ci-deployer user has been replaced by an OIDC federation role. The access key is no longer needed.
