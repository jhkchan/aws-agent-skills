# Advanced Patterns (load on demand) — CloudFront 502 Troubleshooter

Expert knowledge and deep dives moved verbatim from SKILL.md: philosophy, Step 0 non-obvious behaviours, the configuration dependency graph, and the triage heuristics.


---

## Philosophy — four separating behaviours (moved from SKILL.md)

Four behaviours separate a senior CloudFront engineer from a generalist:

- **502 from CloudFront is not the same as 502 from origin.** The
  `x-cache` field separates edge-produced errors from origin-produced
  errors. Misreading it leads to hours of probing a healthy origin.
- **TLS mismatch is the most common 502 after a config change.** Setting
  `OriginProtocolPolicy: https-only` against an HTTP-only origin, or
  pointing at a TLSv1.0-only origin, produces a deterministic 502 on
  every request. The error is invisible to the origin's access log
  because the handshake never completes.
- **OAC failures are silent on the origin side.** When CloudFront uses
  OAC for an S3 origin, S3 receives a SigV4-signed request with the
  CloudFront service principal. If the bucket policy still references
  the legacy OAI CanonicalUser, S3 returns 403; the viewer sees 502.
  Probing S3 directly with the same path may succeed (anonymous read),
  which is misleading.
- **The error cache TTL hides transient failures.** A Custom Error
  Response with `ErrorCachingMinTTL: 300` serves a stale 502 page for
  five minutes after the origin recovers. Always purge
  (`CreateInvalidation`) before declaring a CloudFront-side bug.


---

## Step 0: Non-obvious behaviours that change diagnosis (moved from SKILL.md)

- **Viewer-to-edge TLS can succeed while edge-to-origin TLS fails.**
  ViewerCertificate and OriginProtocolPolicy / OriginSslProtocols are
  independent. A green viewer-side padlock does NOT prove the origin
  handshake is healthy.
- **Lambda@Edge logs are in us-east-1 only.** Even for ap-southeast-1
  viewers, function logs land in us-east-1 under
  `/aws/lambda/us-east-1.<function-name>`. Tailing the regional log
  group yields nothing.
- **OriginShield doubles the failure surface.** With OriginShield
  enabled, traffic flows viewer -> shield POP -> origin. Origin
  firewalls that whitelisted edge-POP IPs will block shield-POP IPs.
- **Multi-origin failover needs both OriginGroups AND a behaviour
  attached.** Defining a group is not enough; the CacheBehavior must
  route to the group, not the primary origin directly.
- **OAC signs requests with the CloudFront service principal, not a
  static access key.** Migrating OAI -> OAC silently breaks S3 origins
  that hard-coded the OAI CanonicalUser principal.
- **Custom Error Responses cache errors.** High TTL on error responses
  hides recovered origins for minutes. Always check
  `CustomErrorResponses` before declaring a CF-side bug.
- **Field-level encryption requires HTTPS-only viewer requests.**
  Enabling FLE on a behaviour that allows HTTP produces 502s on every
  HTTP request.
- **`Status: InProgress` produces inconsistent POP results.** A 502
  during a deploy is often the new revision rolling out unevenly, not
  an origin failure.


---

## Configuration dependency graph (moved from SKILL.md)

```
Viewer request
    |
    v
+----------------------------------------------+
| CloudFront edge POP                          |
|   - ViewerCertificate (TLS)                  |  viewer-side TLS
|   - Restrictions.GeoRestriction              |  Step 9: geo
|   - WAF web ACL (if attached)                |
|   - LambdaFunctionAssociations (viewer req)  |  Step 4: Lambda@Edge
|   - FieldLevelEncryptionConfig               |  Step 10: FLE
+----------------------------------------------+
    |
    v (after cache miss)
+----------------------------------------------+
| Origin Shield (optional, dedicated POP)      |  Step 12: shield
+----------------------------------------------+
    |
    v
+----------------------------------------------+
| Origin                                       |
|   - DomainName + OriginProtocolPolicy        |  Step 3: TLS
|   - OriginSslProtocols                       |  Step 3: TLS
|   - CustomHeaders                            |  Step 5: header
|   - OriginAccessControlId (S3 only)          |  Step 7: OAC
|   - ConnectionTimeout                        |  Step 11: timeout
|   - OriginGroups (if multi-origin)           |  Step 8: failover
|   - S3 / ALB / NLB / Custom HTTP             |  Step 2: connection
|   - LambdaFunctionAssociations (origin req)  |  Step 4: Lambda@Edge
+----------------------------------------------+
    |
    v (response back to viewer, cached if cacheable)
+----------------------------------------------+
| Edge response handling                       |
|   - Cache TTL                                |
|   - CustomErrorResponses + ErrorCachingMinTTL|  Step 14: cached error
|   - LambdaFunctionAssociations (viewer resp) |  Step 4: Lambda@Edge
+----------------------------------------------+
```


---

## Expert heuristic (moved from SKILL.md)

The single highest-signal heuristic: **viewer-to-edge TLS can succeed
while edge-to-origin TLS fails.** Operators see a green padlock and
assume "TLS is fine." But the distribution's `OriginProtocolPolicy` and
`OriginSslProtocols` are completely independent of the viewer-facing
`ViewerCertificate`. A 502 that appears immediately after changing
`OriginProtocolPolicy` to `https-only` is almost always an origin-side
TLS protocol or cipher mismatch. Second highest-signal heuristic: **a
Custom Error Response with a non-zero `ErrorCachingMinTTL` will serve a
stale 502 page for minutes after the origin recovers.** Always
invalidate the error path (or set `ErrorCachingMinTTL: 0` during
incidents) before declaring a CloudFront-side bug.
