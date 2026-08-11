# Eval: sftp-service-managed-public

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — SFTP, service-managed IDP, PUBLIC endpoint, per-user session policy, custom host key

## Prompt

Create a Transfer Family SFTP server in us-east-1 for B2B partner
file exchange. Protocol: SFTP. Endpoint type: PUBLIC. Identity
provider: service-managed. S3 bucket: partner-exchange. Users:
partner-a and partner-b, each with LOGICAL home directory mapping
to /partner-exchange/home/<user>. IAM role: TransferFamilyS3Access
with trust policy for transfer.amazonaws.com. Session policy per
user scoped to /partner-exchange/home/<user>/*. Server host key:
custom RSA. Tags: Environment=production, App=partner-exchange.
