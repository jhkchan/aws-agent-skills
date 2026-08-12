# Eval: vocabulary-and-filter

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — standard batch, custom vocabulary support-terms (boost) + vocabulary filter profanity-filter (mask mode), both applied simultaneously

## Prompt

Configure Amazon Transcribe to transcribe a customer support
call recording from s3://calls-input/recordings/call-001.flac.
Language: en-US. Use custom vocabulary "support-terms" (READY)
for product names. Also use vocabulary filter "profanity-filter"
(READY) in mask mode. No diarization needed. Output to
s3://calls-output. Region us-east-1. Tags:
Environment=production, UseCase=call-analysis.
