# Eval: sftp-custom-lambda-vpc

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — VPC_ENDPOINT, custom Lambda IDP, PrivateLink, session policy, structured logging

## Prompt

Create a Transfer Family SFTP server in us-east-1 for internal file
transfers. Protocol: SFTP. Endpoint type: VPC_ENDPOINT. VPC
vpc-aaa11122, subnets subnet-aaa, subnet-bbb, security group
sg-sftp-internal. Identity provider: custom Lambda function
transfer-idp-auth. S3 bucket: file-landing-zone. Users provisioned
dynamically by Lambda with LOGICAL home directory mapping. IAM role:
TransferFamilyS3Access. Session policy: per-user scoped to
/file-landing-zone/home/<user>/*. Structured JSON logging to
CloudWatch Logs /aws/transfer/sftp. Tags: Environment=production,
App=file-landing-zone.
