# Eval: saml-federation-cross-account

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — SAML provider, cross-account role in different account

## Prompt

Create a Cognito Identity Pool federating from SAML provider
arn:aws:iam::123456789012:saml-provider/CorpIdP. Pool name:
corp-saml-pool. The authenticated role is in account
999999999999: arn:aws:iam::999999999999:role/SAMLAuthRole.
No guest access. Identity pool is in account 123456789012.
Region us-east-1. Tags: Environment=enterprise.
