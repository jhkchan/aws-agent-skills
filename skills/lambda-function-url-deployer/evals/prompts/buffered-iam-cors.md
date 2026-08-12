# Eval: buffered-iam-cors

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — BUFFERED + AWS_IAM auth, full CORS (allowOrigins, allowMethods, allowHeaders, exposeHeaders, maxAgeSeconds), resource-based policy for caller, CloudWatch metrics

## Prompt

Create a Lambda function URL for function my-api-handler
(runtime nodejs20.x) in us-east-1. Use AWS_IAM auth and
BUFFERED invoke mode. Configure CORS to allow origins
https://app.example.com, methods GET and POST, headers
content-type and authorization, expose headers x-request-id,
max age 86400. The function timeout is 10 seconds. Allow
user alice (arn:aws:iam::111122223333:user/alice) to invoke.
Tags: Environment=production, Service=api.
