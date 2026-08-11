# Eval prompt: cached-error-response-stale-502-after-recovery

Diagnose the CloudFront 502 failure for the following distribution. Walk
the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: `d555555efghij2.cloudfront.net` serves 502 on `/checkout/*`
even though the origin has been healthy for 6 minutes (per direct probe
and per origin access log showing 200 responses). Operators believe
CloudFront is broken.

```text
DistributionId: E5QW3R4Y5Z6A7E
DomainName: d555555efghij2.cloudfront.net
Origin: checkout.cached-error-response-stale-502-after-recovery.example.com

curl -sv --resolve \
  checkout.cached-error-response-stale-502-after-recovery.example.com:443:<ip> \
  https://checkout.cached-error-response-stale-502-after-recovery.example.com/checkout/cart
  → HTTP/1.1 200 OK (origin healthy; content returned)

curl https://d555555efghij2.cloudfront.net/checkout/cart
  HTTP/2 502
  x-cache: Error from cloudfront
  age: 312

curl -H 'Cache-Control: no-cache' \
  https://d555555efghij2.cloudfront.net/checkout/cart
  → HTTP/2 200, x-cache: Miss from cloudfront

aws cloudfront get-distribution-config output (excerpt):
  CustomErrorResponses:
    Items:
      - ErrorCode: 502
        ErrorCachingMinTTL: 300
        ResponseCode: '502'
        ResponsePagePath: /errors/502.html

Origin timeline:
  - 12:00 UTC: origin app deployed a broken version; returned
    502 for 90 seconds
  - 12:01:30 UTC: rollback completed; origin returns 200
  - 12:07 UTC (now): CloudFront still serving 502
```

The origin recovered, but the Custom Error Response with
`ErrorCachingMinTTL: 300` is serving the cached 502 page for 5 minutes.
The `age: 312` header and the successful no-cache probe confirm the
error cache is the source of the persistent 502.
