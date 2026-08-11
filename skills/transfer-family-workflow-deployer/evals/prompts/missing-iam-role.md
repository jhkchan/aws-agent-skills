# Eval: missing-iam-role

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — IAM role does not exist; users cannot access S3

## Prompt

Create a Transfer Family SFTP server in us-east-1. Protocol: SFTP.
Endpoint type: PUBLIC. Identity provider: service-managed. S3 bucket:
file-exchange. The IAM role TransferFamilyS3Access does not exist
yet. Users: partner-a with home directory
/file-exchange/home/partner-a.
