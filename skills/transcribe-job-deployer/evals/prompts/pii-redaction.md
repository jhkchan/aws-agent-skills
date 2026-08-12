# Eval: pii-redaction

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — standard batch with PII content redaction enabled at job creation, entity types NAME/SSN/CREDIT_CARD_NUMBER/BANK_ACCOUNT_NUMBER/PHONE, redacted-only output

## Prompt

Configure Amazon Transcribe to transcribe a financial services
call from s3://fin-input/calls/customer-call.wav. Language:
en-US. Enable PII content redaction — mask NAME, SSN,
CREDIT_CARD_NUMBER, BANK_ACCOUNT_NUMBER, and PHONE. Output only
the redacted transcript to s3://fin-output. Region us-east-1.
Tags: Environment=production, UseCase=compliance,
Regulation=PCI-DSS.
