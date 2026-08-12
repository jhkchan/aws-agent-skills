---
description: Provision an AWS Lambda Function URL with production-grade defaults (AWS_IAM vs NONE auth, CORS configuration, BUFFERED vs RESPONSE_STREAM invoke mode, 15-second timeout awareness, CloudFront custom domain, CloudWatch metrics). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create lambda function url"
  - "deploy lambda function url"
  - "configure cors on function url"
  - "enable response streaming lambda"
  - "lambda function url iam auth"
  - "lambda url cloudfront custom domain"
  - "lambda function url buffered"
  - "lambda function url response_stream"
  - "update function url config"
  - "lambda function url"
routes_to: lambda-function-url-deployer
---

# /aws:deploy-lambda-function-url

Activate the `lambda-function-url-deployer` skill and provision an
AWS Lambda Function URL with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Function URL creation (create-function-url-config)
2. Auth mode (AWS_IAM vs NONE)
3. CORS configuration (allowOrigins, allowMethods, allowHeaders,
   exposeHeaders, maxAgeSeconds)
4. Invoke mode (BUFFERED vs RESPONSE_STREAM)
5. Timeout limit (15 seconds for function URL invocations)
6. Dual-stack IPv4/IPv6 (automatic)
7. $LATEST alias constraint (qualifier update for custom alias)
8. CloudWatch metrics (UrlRequests, Url4xx, Url5xx, UrlLatency)
9. Cold start impact (provisioned concurrency)
10. Custom domain via CloudFront + Lambda URL
11. Pricing (same as standard Lambda invocation)

## When to use

- You need to create a Lambda Function URL.
- You need to configure CORS on an existing function URL.
- You need to switch invoke mode (BUFFERED to RESPONSE_STREAM).
- You need IAM-authenticated function URLs.
- You need a custom domain (CloudFront) in front of a function URL.
- You need to monitor function URL CloudWatch metrics.

## When NOT to use

- **API Gateway HTTP/REST APIs** — use apigateway skills for usage
  plans, API keys, request validation, throttling.
- **Lambda@Edge** — function URLs do not support Lambda@Edge.
- **Application Load Balancer targets** — use alb skills.
- **WebSocket APIs** — use the apigateway-websocket-deployer skill.

## How to invoke

### Slash command

```
/aws:deploy-lambda-function-url
```

Then provide: function name, auth mode (AWS_IAM or NONE), invoke
mode (BUFFERED or RESPONSE_STREAM), CORS origins/methods/headers,
qualifier (if custom alias), CloudFront domain (if custom domain),
tags.

### Natural language

Any of these routes to the same skill:

- "create a lambda function url for my-function"
- "configure cors on my lambda function url"
- "enable response streaming on my lambda url"
- "set up iam auth on my lambda function url"
- "put a cloudfront custom domain on my lambda url"

### CLI routing

```bash
node cli/bin/cli.js route "create a lambda function url"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps
pipeline. The orchestrator routes to it when the user wants to
create or configure Lambda Function URLs. The output checklist
feeds into verification pipelines and downstream monitoring skills.

## Example

```
You: /aws:deploy-lambda-function-url

     Create a function URL for my-api-handler with IAM auth,
     BUFFERED mode, CORS for app.example.com.

Skill:
  LAMBDA_FUNCTION_URL: https://abc123def456.lambda-url.us-east-1.on.aws/
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Auth mode: AWS_IAM
    [✓] Invoke mode: BUFFERED
    [✓] CORS: AllowOrigins=["https://app.example.com"]
    [✓] Timeout check: 10s (within 15s cap)
  VERIFICATION_COMMANDS:
    aws lambda get-function-url-config --function-name my-api-handler --region us-east-1
```

## References

- Skill definition: `skills/lambda-function-url-deployer/SKILL.md`
- CORS and auth guide: `skills/lambda-function-url-deployer/references/cors-and-auth.md`
- Streaming and CloudFront guide: `skills/lambda-function-url-deployer/references/streaming-and-cloudfront.md`
- Eval suite: `skills/lambda-function-url-deployer/evals/evals.json`
