# Eval: signing-job-from-s3-source

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — signing job with immutability noted, source/destination S3 buckets cited, UpdateFunctionCode flow

## Prompt

Start a signing job using the existing profile "lambda-signing-prod"
(AWSLambda-SHA384-ECDSA) in us-east-1. Source:
s3://my-unsigned-artifacts/lambda/my-prod-function.zip (version
v1abc). Destination: s3://my-signed-artifacts/lambda/signed/. The
signed artifact must be consumed by a subsequent UpdateFunctionCode
call.
