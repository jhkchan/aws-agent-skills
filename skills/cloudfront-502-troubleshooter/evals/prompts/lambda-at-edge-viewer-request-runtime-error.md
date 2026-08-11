# Eval prompt: lambda-at-edge-viewer-request-runtime-error

Diagnose the CloudFront 502 failure for the following distribution. Walk
the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: `d222222bcdefg9.cloudfront.net` returns HTTP 502 to ~5% of
viewers on `/search/*` since 09:00 UTC. A new Lambda@Edge viewer-request
function was deployed 1 hour ago with a rewritten query-string parser.

```text
DistributionId: E2QW3R4Y5Z6A7B
DomainName: d222222bcdefg9.cloudfront.net
Origin: api.app.example.com (ALB, healthy)

curl https://d222222bcdefg9.cloudfront.net/search?q=shoes
  HTTP/2 502
  x-cache: Error from cloudfront
  x-edge-result-type: FunctionExecutionError
  x-amz-cf-pop: SFO53-C2

Lambda@Edge function config:
  FunctionName: lambda-at-edge-viewer-request-runtime-error
  Region: us-east-1 (Lambda@Edge functions always in us-east-1)
  Runtime: nodejs20.x
  Handler: index.handler

aws logs filter-log-events --region us-east-1 \
  --log-group-name /aws/lambda/us-east-1.lambda-at-edge-viewer-request-runtime-error:
  ERROR  Cannot read properties of undefined (reading 'split')
    at handler (/var/task/index.js:42)
  Task timed out after 5s (1 occurrence)

The error reproduces only when the query string is missing the
expected "q" parameter; the function does
event.Records[0].cf.request.querystring.split('&') without a null
check.

Origin direct probe:
  curl -sv --resolve api.app.example.com:443:<ip> \
    https://api.app.example.com/search?q=shoes
  → HTTP/1.1 200 OK (origin healthy)
```

The `x-edge-result-type: FunctionExecutionError` field identifies the
fault as a Lambda@Edge runtime exception, not an origin failure.
