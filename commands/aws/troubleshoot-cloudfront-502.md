---
description: Diagnose CloudFront 502 (and 504) errors through a fourteen-layer decision tree — origin connection timeout, TLS protocol/cipher mismatch, OAC misconfiguration, Lambda@Edge runtime error, failover routing, geo restriction, field-level encryption, origin shield, deployment state, cached error responses — and emit ROOT_CAUSE_IDENTIFIED with the specific failure layer.
nl_triggers:
  - "CloudFront 502"
  - "CloudFront 504"
  - "CloudFront Bad Gateway"
  - "CloudFront Gateway Timeout"
  - "x-amz-cf-id 502"
  - "CloudFront origin connection failed"
  - "CloudFront TLS handshake failure"
  - "CloudFront origin SSL error"
  - "CloudFront Lambda@Edge error"
  - "CloudFront OAC 502"
  - "CloudFront failover 502"
  - "CloudFront geographic block"
  - "CloudFront origin shield 502"
  - "CloudFront distribution InProgress 502"
  - "CloudFront cached 502"
  - "troubleshoot CloudFront 502"
  - "diagnose CloudFront 502"
  - "CloudFront edge 502"
routes_to: cloudfront-502-troubleshooter
---

# /aws:troubleshoot-cloudfront-502

Activate the `cloudfront-502-troubleshooter` skill and diagnose a
CloudFront distribution returning 502 Bad Gateway or 504 Gateway Timeout
to viewers through the fourteen-layer diagnostic tree.

## What it does

Reads a symptom description (HTTP 502/504 status, `x-edge-result-type`,
`x-cache` from access logs) plus the distribution configuration, then
walks the symptom-driven diagnostic tree to a root cause with positive
evidence:

1. **Pre-flight** — distribution Status (Deployed vs InProgress),
   `get-distribution-config`, recent CloudFront access logs in
   us-east-1, AWS Health (regional incidents). Short-circuits on
   InProgress status, geo restriction, or AWS-side CloudFront events.
2. **Symptom entry** — map the access-log row to one of: origin
   connection timeout, TLS protocol/cipher mismatch, origin response
   too large, custom header validation failure, Lambda@Edge runtime
   error, OAC misconfiguration, failover misconfiguration, geographic
   restriction, field-level encryption, response timeout (504), origin
   shield, cached error response.
3. **Layer-specific probes** —
   - Origin connection: `elbv2 describe-target-health` for ALB/NLB;
     `s3api head-object` for S3; `openssl s_client` for TLS.
   - TLS mismatch: distribution's OriginProtocolPolicy /
     OriginSslProtocols vs origin's actual listener config; cipher
     negotiation probe.
   - Lambda@Edge: `logs filter-log-events` on
     `/aws/lambda/us-east-1.<fn>` in us-east-1 only; `x-edge-result-type:
     FunctionExecutionError` confirms.
   - OAC: `list-origin-access-controls` vs `s3api get-bucket-policy`
     principal mismatch (legacy OAI CanonicalUser vs OAC
     cloudfront.amazonaws.com service principal with SourceArn).
   - Failover: `get-distribution-config` OriginGroups vs CacheBehavior
     TargetOriginId (must point at the group, not the primary).
   - Geo restriction: `Restrictions.GeoRestriction` whitelist /
     blacklist.
   - FLE: `FieldLevelEncryptionConfig`, public key validity,
     Content-Type match.
   - Response timeout: `time-taken` in access log vs CF 30s cap;
     origin TTFB via curl.
   - Origin shield: `OriginShield.OriginShieldEnabled` + region;
     origin firewall whitelist for shield POP IPs.
   - Cached error: `CustomErrorResponses` with high TTL; `age` header
     in viewer response; no-cache probe succeeds.
4. **Verdict** — ROOT_CAUSE_IDENTIFIED (with failing probe that matches
   the symptom) or INSUFFICIENT_DATA (a probe requires operator input).

Emits a deterministic diagnostic block per target:

```text
TARGET: <distribution-id> (domain: <distribution-domain-name>)
VERDICT: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
REASON: <1-2 sentences naming the failed layer and the failing probe>
LAYER: <ORIGIN_CONNECTION_TIMEOUT | ORIGIN_TLS_PROTOCOL_MISMATCH |
        ORIGIN_TLS_CIPHER_MISMATCH | ORIGIN_RESPONSE_TOO_LARGE |
        CUSTOM_HEADER_VALIDATION | LAMBDA_AT_EDGE_ERROR |
        OAC_MISCONFIGURATION | FAILOVER_MISCONFIGURATION |
        GEO_RESTRICTION_BLOCKING | FIELD_LEVEL_ENCRYPTION_ERROR |
        ORIGIN_RESPONSE_TIMEOUT | ORIGIN_SHIELD_MISCONFIGURATION |
        DISTRIBUTION_NOT_DEPLOYED | CACHED_ERROR_RESPONSE | UNKNOWN>
EVIDENCE:
  - <observed symptom — status, x-edge-result-type, x-cache>
  - <failing probe — command and its output that confirms the cause>
  - <passing probes — layers ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
```

## When to invoke

Paste a symptom description and ask any of:

- "CloudFront returns 502 to viewers"
- "CloudFront 504 Gateway Timeout"
- "x-edge-result-type: FunctionExecutionError"
- "CloudFront can't reach origin (502)"
- "CloudFront TLS handshake failure"
- "CloudFront Lambda@Edge function error"
- "CloudFront OAC bucket policy 502"
- "CloudFront failover not working"
- "CloudFront cached 502 after origin recovered"

A bare distribution ID + any error verb ("distribution failing", "edge
returning 5xx", "origin unreachable") also routes here via the
orchestrator.

## Inputs

- Symptom description: HTTP status (502 / 504), `x-edge-result-type`
  from access logs, `x-cache` value, viewer geography, intermittent vs
  persistent pattern.
- Distribution configuration: DistributionId, DomainName, Origins
  (domain, protocol policy, SSL protocols, custom headers, OAC id),
  OriginGroups, CacheBehaviors, LambdaFunctionAssociations,
  CustomErrorResponses, Restrictions, OriginShield.
- For live-account diagnosis: curl reproduction against the distribution
  domain, origin probe (curl --resolve), `aws logs filter-log-events`
  on the CloudFront log group in us-east-1, `aws logs filter-log-events`
  on Lambda@Edge function logs in us-east-1.

## Outputs

- One diagnostic block per target distribution.
- Layer-specific LAYER value from the enumerated set.
- Evidence section with the failing probe AND passing probes (layers
  ruled out) — never a verdict without positive evidence.
- Specific remediation: protocol policy alignment, OAC bucket policy
  update, Lambda@Edge function code fix, failover behaviour re-route,
  geo restriction edit, invalidation for cached error, distribution
  update for shield / FLE / TLS, or AWS Support escalation.

## Related

- `/aws:troubleshoot-cloudfront-cache` for cache hit ratio, stale
  content, or 403/404-from-cache issues that are NOT 502/504.
- `/aws:troubleshoot-alb-5xx` for ALB-origin 5xx that may be the
  upstream cause of CloudFront 502 (CF returns 502 when ALB returns 5xx
  to CF).
- `/aws:troubleshoot-vpc-connectivity` for private-origin connectivity
  issues (SG, NACL, route table) that may cause CF origin fetch failures.
- `/aws:audit-cloudfront-distribution` for configuration posture audits
  on the same distribution (TLS version, certificate, OAC posture).
