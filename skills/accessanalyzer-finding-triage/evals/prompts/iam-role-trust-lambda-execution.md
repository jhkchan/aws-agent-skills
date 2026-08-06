# Eval prompt: iam-role-trust-lambda-execution

Triage the following IAM Access Analyzer finding.
Emit the standard VERDICT block (FINDING, RESOURCE, RESOURCE_TYPE, FINDING_TYPE, VERDICT, RISK, REASON, REMEDIATION).

Finding ID: iam-role-trust-lambda-execution
Finding type: ExternalAccess
Resource: arn:aws:iam::123456789012:role/lambda-report-generator
Resource type: AWS::IAM::Role
Resource owner account: 123456789012
Principal: {"Service": "lambda.amazonaws.com"}
isPublic: false
Actions: ["sts:AssumeRole"]
Condition: {}
Status: ACTIVE
Created at: 2024-06-01T10:00:00Z
Analyzed at: 2025-01-20T08:00:00Z
