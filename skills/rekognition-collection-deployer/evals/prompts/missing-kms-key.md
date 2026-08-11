# Eval: missing-kms-key

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — operator wants KMS encryption but has no key ARN; KMS cannot be added after creation

## Prompt

Create a Rekognition collection "secure-faces" in us-east-1 with
KMS encryption. I need compliance-grade encryption but I don't
have a KMS key ARN yet. Index 10000 faces. Tags:
Environment=production, Compliance=GDPR.
