# Eval prompt: origin-tls-protocol-mismatch-https-only

Diagnose the CloudFront 502 failure for the following distribution. Walk
the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: `d111111abcdef8.cloudfront.net` returns HTTP 502 to 100% of
viewers on `/api/*` since 14:10 UTC. The distribution config was edited
1 hour ago to set `OriginProtocolPolicy: https-only` on the api.alb
origin.

```text
DistributionId: E1Q2W3R4Y5Z6A7
DomainName: d111111abcdef8.cloudfront.net
Origin: api-tls-protocol-mismatch-https-only.alb.example.com (ALB)
OriginProtocolPolicy: https-only
ViewerProtocolPolicy: redirect-to-https
Status: Deployed

curl https://d111111abcdef8.cloudfront.net/api/users
  HTTP/2 502
  x-cache: Error from origin
  x-amz-cf-pop: IAD89-C1

aws elbv2 describe-load-balancers output:
  - DNSName: api-tls-protocol-mismatch-https-only.alb.example.com
  - Listeners: HTTP:80 only (no HTTPS:443 listener)
  - State: active

openssl s_client -connect \
  api-tls-protocol-mismatch-https-only.alb.example.com:443
  connect: Connection refused

Origin access logs in the last 30 minutes: zero matching
  requests on /api/users (TLS handshake never completes).
```

The error appeared immediately after the OriginProtocolPolicy change.
The viewer-side TLS (ViewerCertificate) is healthy; the failure is
between CloudFront and the origin.
