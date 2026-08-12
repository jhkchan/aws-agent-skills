# Eval: credential-helper-sts-exchange

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — credential-process command with client-cert.pem, client-key.pem, trust anchor ta-aaa111222, profile p-bbb222333, role RolesAnywhereCIRunner; AWS CLI profile configuration shown

## Prompt

Configure the aws_signing_helper credential helper in us-east-1
account 123456789012. Client certificate client-cert.pem and
private key client-key.pem. Trust anchor ID ta-aaa111222.
Profile ID p-bbb222333. Role ARN
arn:aws:iam::123456789012:role/RolesAnywhereCIRunner. Region
us-east-1. Show the credential-process command and the AWS CLI
profile configuration.
