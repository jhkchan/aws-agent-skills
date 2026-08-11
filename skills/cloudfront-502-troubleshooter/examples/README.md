# Example usage: cloudfront-502-troubleshooter

A walkthrough showing the skill diagnosing a CloudFront 502 that
appeared immediately after a config deploy, demonstrating the
`x-cache` header routing, the viewer-vs-origin TLS separation, and
the evidence-backed ROOT_CAUSE_IDENTIFIED verdict pointing at the
origin TLS protocol mismatch.

## Input (user prompt)

> Our CloudFront distribution `d111111abcdef8.cloudfront.net` started
> returning HTTP 502 to all viewers on `/api/*` at 14:10 UTC. We
> deployed a config change an hour earlier switching the origin to
> HTTPS-only. The ALB origin has been healthy throughout. Direct
> probes of the origin succeed over HTTP but fail over HTTPS.

```text
DistributionId: E1Q2W3R4Y5Z6A7
DomainName: d111111abcdef8.cloudfront.net
Origin: api-prod.alb.example.com (ALB)
OriginProtocolPolicy: https-only
ViewerProtocolPolicy: redirect-to-https
Status: Deployed

curl https://d111111abcdef8.cloudfront.net/api/users
  HTTP/2 502
  x-cache: Error from origin
  x-amz-cf-pop: IAD89-C1

aws elbv2 describe-load-balancers output:
  - DNSName: api-prod.alb.example.com
  - Listeners: HTTP:80 only (no HTTPS:443 listener)
  - State: active

openssl s_client -connect api-prod.alb.example.com:443
  connect: Connection refused

Origin access logs in the last 30 minutes: zero matching
  requests on /api/users.
```

## Skill output

```text
TARGET: E1Q2W3R4Y5Z6A7 (domain: d111111abcdef8.cloudfront.net)
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: Distribution OriginProtocolPolicy was changed to https-only
  in the last deploy, but the ALB origin listens only on HTTP port 80.
  Every origin fetch fails the TLS handshake before any bytes are
  exchanged (Step 3). The origin access log shows zero matching
  requests, confirming the connection never completed.
LAYER: ORIGIN_TLS_PROTOCOL_MISMATCH
EVIDENCE:
  - Symptom: 100% of requests to /api/* return 502 since 14:10 UTC;
    curl shows x-cache: Error from origin.
  - Probe: aws cloudfront get-distribution-config returns
    Origins.Items[0].OriginProtocolPolicy = "https-only".
  - Probe: aws elbv2 describe-load-balancers shows the ALB
    listeners are HTTP:80 only (no HTTPS:443 listener).
  - Probe: openssl s_client -connect api-prod.alb.example.com:443
    returns "Connection refused" — no TLS endpoint at the origin.
  - Passing: no Lambda@Edge on this behaviour
    (LambdaFunctionAssociations empty); Custom Error Responses for
    502 has TTL 10s (too short to explain persistent 502);
    distribution Status: Deployed (not mid-rollout).
REMEDIATION:
  1. Either add an HTTPS listener on the ALB with a valid certificate
     and keep OriginProtocolPolicy: https-only (preferred), OR set
     OriginProtocolPolicy to http-only (only if the origin accepts
     plaintext):
     aws cloudfront update-distribution --id E1Q2W3R4Y5Z6A7 \
       --if-match <etag> --distribution-config <updated-config-json>
  2. Wait for Status: Deployed, then verify:
     curl -sv -H 'Cache-Control: no-cache' \
       https://d111111abcdef8.cloudfront.net/api/users
     Expect HTTP/2 200 and x-cache: Miss from cloudfront.
CONFIRM: Before updating the distribution, emit and await:
  "CONFIRM: About to update OriginProtocolPolicy on E1Q2W3R4Y5Z6A7.
   Proceed? (yes/no)"
```

## What the skill caught that a generic assistant misses

1. **Read `x-cache` first.** The `Error from origin` value immediately
   routed the diagnosis to the origin / origin-TLS layers, skipping
   Lambda@Edge and geo-restriction. A generic assistant would probe
   the origin's HTTP path (which works), conclude "the origin is
   healthy," and stall.

2. **Separated viewer TLS from origin TLS.** The viewer-side TLS
   (green padlock on the curl output) is irrelevant; the failure is
   the edge-to-origin TLS handshake. The `openssl s_client` probe
   proves the origin has no TLS endpoint at all.

3. **Cross-referenced the deployment timeline.** The 14:10 UTC onset
   matched the deploy that changed OriginProtocolPolicy. The skill
   treats a 502 that appears immediately after a config edit as the
   config edit until proven otherwise.

4. **Ruled out the error cache.** The Custom Error Response TTL is
   10s, far shorter than the 30-minute persistent 502 — so the cached
   error layer is ruled out with positive evidence.

5. **Recommended the two real fixes (not a workaround).** Either add
   an HTTPS listener (preferred) or revert OriginProtocolPolicy. A
   generic assistant might suggest "wait for CloudFront to propagate"
   or "purge the cache" — neither addresses the root cause.

## Slash-command invocation

```
/aws:troubleshoot-cloudfront-502
```

Or via the orchestrator:

```
/aws:pipeline
You: "diagnose why d111111abcdef8.cloudfront.net returns 502"
```

The orchestrator emits
`[Phase: Troubleshoot | Skills routed: cloudfront-502-troubleshooter]`
and hands off to this skill for the diagnostic block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the fix:

```bash
# Confirm the distribution is Deployed
aws cloudfront get-distribution --id E1Q2W3R4Y5Z6A7 --profile default \
  --query 'Distribution.Status'

# Verify origin fetch succeeds with no-cache
curl -sv -H 'Cache-Control: no-cache' \
  https://d111111abcdef8.cloudfront.net/api/users 2>&1 | \
  grep -E 'HTTP/|x-cache'

# Watch the 5xx rate metric for 15 minutes
aws cloudwatch get-metric-statistics --namespace AWS/CloudFront \
  --metric-name 5xxErrorRate \
  --dimensions Name=DistributionId,Value=E1Q2W3R4Y5Z6A7 \
  --start-time $(date -d '-15 minutes' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 60 --statistics Average --profile default --output json
```

Then monitor the CloudFront 5xx rate for 30 minutes to confirm it
returns to baseline.
