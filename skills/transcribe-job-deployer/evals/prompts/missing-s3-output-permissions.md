# Eval: missing-s3-output-permissions

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — output bucket does not grant Transcribe s3:PutObject; job would fail

## Prompt

Configure Amazon Transcribe to transcribe audio from
s3://input-bucket/audio.wav. Language: en-US. Output to
s3://output-bucket. The output bucket does not have a bucket
policy granting Transcribe write access. Region us-east-1.
