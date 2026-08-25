# Worked examples — lambda-function-url-deployer

> Content moved verbatim from SKILL.md during progressive-disclosure
> restructuring. Load on demand.

## Worked example — RESPONSE_STREAM with NONE auth and CloudFront

```text
LAMBDA_FUNCTION_URL: https://xyz789abc012.lambda-url.us-east-1.on.aws/
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Lambda function: my-streaming-handler (exists, runtime: nodejs20.x)
  [✓] Auth mode: NONE (public endpoint — WAF + app-level auth)
  [✓] Invoke mode: RESPONSE_STREAM
  [✓] CORS: AllowOrigins=["*"], AllowMethods=["GET","POST"], AllowHeaders=["content-type"], MaxAgeSeconds=3600
  [✓] Timeout check: function timeout 15s (at function URL cap)
  [✓] Dual-stack: IPv4 + IPv6 (automatic)
  [✓] Qualifier: prod
  [✓] CloudFront custom domain: stream.example.com → https://xyz789abc012.lambda-url.us-east-1.on.aws/
  [✓] CloudWatch metrics: UrlRequests, Url4xx, Url5xx, UrlLatency (automatic)
  [✓] Tags: Environment=production, Service=streaming-api
VERIFICATION_COMMANDS:
  aws lambda get-function-url-config --function-name my-streaming-handler --qualifier prod --region us-east-1
  aws cloudfront get-distribution-config --id <distribution-id> --region us-east-1
  aws cloudwatch get-metric-statistics --namespace AWS/Lambda --metric-name UrlLatency --dimensions Name=FunctionName,Value=my-streaming-handler --start-time 2026-08-11T00:00:00Z --end-time 2026-08-11T01:00:00Z --period 300 --statistics Average --region us-east-1
```

