# Eval: missing-s3-bucket

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — S3 destination bucket does not exist; Firehose cannot deliver

## Prompt

Create a Firehose delivery stream named events-stream in
us-east-1, account 123456789012. Source: Direct PUT. S3
destination bucket my-nonexistent-bucket (this bucket has not
been created yet). No transformation. JSON format. Buffering
hints 5MB / 300s.
