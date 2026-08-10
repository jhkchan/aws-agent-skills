# Eval: hmac-jwt-signing

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — HMAC_256 GENERATE_VERIFY_MAC, manual rotation

## Prompt

Provision a customer-managed KMS key for JWT signing in
us-east-1. Alias: alias/jwt-signing-cmk. Workload: sign and
verify JWTs issued by the auth service. Key spec: HMAC_256.
Key usage: GENERATE_VERIFY_MAC. Key administrators: kms-admin
role. Key users: the auth-svc IAM role. Deletion window: 30
days. Tags: Environment=production, Application=auth. Account:
123456789012.
