---
description: Audit a CloudFront distribution for insecure TLS minimum protocol, missing Origin Access Control (OAC), missing WAF, disabled logging, absent geo restrictions, and default-cache-behavior misconfigurations.
nl_triggers:
  - "audit this CloudFront distribution"
  - "check CloudFront TLS"
  - "is OAC configured on my S3 origin"
  - "does my distribution have a WAF"
  - "CloudFront logging disabled"
  - "geo restriction CloudFront"
  - "ViewerProtocolPolicy allow-all"
  - "OriginProtocolPolicy http-only"
  - "hardening CloudFront before production"
  - "CloudFront edge security"
  - "TLSv1 CloudFront"
  - "minimum protocol version"
  - "S3 website endpoint origin"
  - "CloudFront OAC vs OAI"
  - "CloudFront access logging"
routes_to: cloudfront-distribution-auditor
---

# /aws:audit-cloudfront-distribution

Activate the `cloudfront-distribution-auditor` skill and audit one or more
CloudFront distribution configurations for security exposure.

## What it does

Reads a CloudFront distribution config and applies the ordered classification
logic:

1. Viewer protocol policy — `allow-all` on default cache behavior is
   INSECURE_TLS (HTTP served to viewers).
2. TLS minimum protocol version — anything below `TLSv1.2_2021` is
   INSECURE_TLS (weak cipher suites; CBC-mode ciphers).
3. Origin protocol policy — `http-only` or `match-viewer` on custom origins
   is INSECURE_TLS (unencrypted origin traffic).
4. S3 website endpoint origin — forces public bucket; INSECURE_TLS.
5. Origin Access Control — S3 REST origin with no OAC and no OAI is NO_OAC
   (bucket must be public; direct origin bypass).
6. WAF Web ACL — no association is CONFIG_GAP.
7. Access logging — disabled is CONFIG_GAP.
8. Geographic restrictions — `RestrictionType: none` is CONFIG_GAP.
9. Default root object — empty on S3 origin is CONFIG_GAP (XML listing leak).
10. Aggregation — worst finding wins (INSECURE_TLS > NO_OAC > CONFIG_GAP > OK).

Emits a deterministic VERDICT per distribution:

```text
DISTRIBUTION: <distribution-id>
VERDICT: INSECURE_TLS | NO_OAC | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and step number>
FINDINGS:
  - [INSECURE_TLS] <finding description (Step N)>
  - [CONFIG_GAP] <finding description (Step N)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste a CloudFront distribution config and ask any of:

- "audit this CloudFront distribution"
- "is my CloudFront TLS secure?"
- "is OAC configured on my S3 origin?"
- "does my distribution have a WAF?"
- "is CloudFront logging enabled?"
- "are geo restrictions set on my distribution?"

A bare distribution id + any audit verb ("audit this distribution", "check
distribution config") also routes here via the orchestrator.

## Inputs

- A CloudFront distribution config (JSON or YAML), pasted inline or
  referenced by file path.
- Key fields: `ViewerCertificate.MinimumProtocolVersion`,
  `DefaultCacheBehavior.ViewerProtocolPolicy`,
  `Origins.Items[].OriginAccessControlId`,
  `Origins.Items[].S3OriginConfig.OriginAccessIdentity`,
  `Origins.Items[].CustomOriginConfig.OriginProtocolPolicy`,
  `Origins.Items[].DomainName`, `WebACLId`, `Logging.Enabled`,
  `Restrictions.GeoRestriction.RestrictionType`, `DefaultRootObject`.
- For multi-origin distributions: each origin is audited independently.

## Outputs

- One VERDICT block per distribution (multiple findings aggregate to the
  worst severity).
- Enumerated FINDINGS list with per-finding severity and step citation.
- Specific remediation: update TLS minimum, configure OAC, associate WAF,
  enable logging, set geo restrictions, set default root object.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for CloudFront edge security).
- `/aws:audit-wafv2-web-acl` for WAF rule-level analysis when a Web ACL is
  associated but rule quality is in question.
