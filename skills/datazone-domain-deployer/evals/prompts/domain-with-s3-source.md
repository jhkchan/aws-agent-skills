# Eval: domain-with-s3-source

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — domain with S3 source, cross-account IAM role chaining verified, glossary terms with subscription policies, request-approve model

## Prompt

Create an Amazon DataZone domain called analytics-domain in
us-east-1, account 111111111111. Domain execution role
arn:aws:iam::111111111111:role/service-role/AmazonDataZoneDomainExecution.
Create a project customer-analytics. Add an S3 data source
my-customer-events in source account 222222222222, region
us-east-1. The source account IAM role is DataZoneS3AccessRole.
Create glossary terms PII (requires data steward approval) and
Public (auto-approve). KMS CMK alias/datazone-cmk for
encryption. Tags: Environment=production, Domain=analytics.
