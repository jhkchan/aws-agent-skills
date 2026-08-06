# Eval prompt: sqs-external-write-public

Triage the following IAM Access Analyzer finding.
Emit the standard VERDICT block (FINDING, RESOURCE, RESOURCE_TYPE, FINDING_TYPE, VERDICT, RISK, REASON, REMEDIATION).

Finding ID: sqs-external-write-public
Finding type: ExternalAccess
Resource: arn:aws:sqs:us-east-1:123456789012:ingestion-queue
Resource type: AWS::SQS::Queue
Resource owner account: 123456789012
Principal: "*"
isPublic: true
Actions: ["sqs:SendMessage", "sqs:ReceiveMessage"]
Condition: {}
Status: ACTIVE
Created at: 2024-08-10T10:00:00Z
Analyzed at: 2025-01-20T08:00:00Z
