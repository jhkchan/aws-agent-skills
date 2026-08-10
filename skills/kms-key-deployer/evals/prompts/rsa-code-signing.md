# Eval: rsa-code-signing

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — RSA_4096 SIGN_VERIFY, no auto-rotation

## Prompt

Provision a customer-managed KMS key for code signing in
us-east-1. Alias: alias/code-signing-cmk. The key will be used
by AWS Signer to sign Lambda deployment packages. Key spec:
RSA_4096. Key usage: SIGN_VERIFY. Key administrators: kms-admin
role. Key users: the signer-service IAM role. Deletion window:
30 days. Tags: Environment=production, Application=code-signing.
Account: 123456789012.
