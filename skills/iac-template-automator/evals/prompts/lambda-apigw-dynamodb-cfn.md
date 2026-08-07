# Eval prompt: lambda-apigw-dynamodb-cfn

Generate an IaC template. Emit the standard VERDICT block (PATTERN, TOOL,
VERDICT, TEMPLATE, VALIDATION, SECURITY, FINDINGS, REMEDIATION).

Pattern: serverless-lambda-apigw
Tool: cloudformation (SAM accepted)

Requirements:
- Environment: prod
- Lambda runtime: python3.12
- DynamoDB table: PAY_PER_REQUEST, partition key pk (S), sort key sk (S)
- DynamoDB SSESpecification: SSEEnabled=true
- DynamoDB PointInTimeRecoverySpecification: PointInTimeRecoveryEnabled=true
- IAM: use SAM policy templates DynamoDBReadPolicy and DynamoDBWritePolicy
  scoped to !Ref Table (no Action:*, no Resource:*)
- Lambda environment variable TABLE_NAME (no secrets in env vars)
- Lambda environment variable SECRET_ARN referencing a Secrets Manager
  secret (the secret is created in the same template)
- Tags: Environment, Owner
- No hardcoded secrets anywhere in the template
- Transform: AWS::Serverless-2016-10-31

Expected: AUTOMATED. All 12 security baseline rules pass. The skill emits
a complete SAM template with DynamoDB SSE + PITR, scoped IAM, secrets via
Secrets Manager, and prod tags.
