# CloudFront 502/504 Layer Reference Guide

Supplementary reference for the CloudFront 502 Troubleshooter skill.
Loaded on-demand when a diagnostic needs TLS negotiation details,
Origin Access Control signing behaviour, Lambda@Edge runtime caps,
or Custom Error Response TTL guidance.

## x-edge-result-type values for 502/504 diagnosis

| Value | Meaning | Routes to layer |
|---|---|---|
| `Error` | Generic edge or origin error | Check `x-cache` to disambiguate |
| `FunctionExecutionError` | Lambda@Edge function threw or timed out | LAMBDA_AT_EDGE_ERROR |
| `LimitExceeded` | WAF, geo restriction, or CF quota | GEO_RESTRICTION_BLOCKING or WAF |
| `Aborted` | Client disconnected; not a server bug | N/A (client-side) |
| `ClientGeoBlocked` | Viewer's country is geo-restricted | GEO_RESTRICTION_BLOCKING |
| `InvalidRequest` | Malformed request rejected at edge | Distribute-side config issue |

## x-cache values for 502/504 diagnosis

| Value | Meaning |
|---|---|
| `Error from cloudfront` | Edge produced the response (Lambda@Edge, FLE, geo, error cache) |
| `Error from origin` | Origin returned 5xx to CF and CF passed it through |
| `Miss from cloudfront` (with 502) | Fresh origin fetch failed; not a cached error |
| `RefreshHit` (with 502) | Stale cache served during revalidation; rare for 502 |

## TLS protocol and cipher matrix (origin side)

| OriginProtocolPolicy | Behaviour |
|---|---|
| `http-only` | CF connects to origin over HTTP (port 80). Cleartext. |
| `https-only` | CF connects to origin over HTTPS (port 443). Origin must serve TLS. |
| `match-viewer` | CF uses the same protocol the viewer used. Security risk if HTTP allowed. |

`OriginSslProtocols` (only when OriginProtocolPolicy is `https-only` or
`match-viewer`):

| Allowed value | Origin must support | Common in 2026? |
|---|---|---|
| `TLSv1` | No | Rarely; deprecated |
| `TLSv1.1` | No | Rarely; deprecated |
| `TLSv1.2` | Yes | Modern default |
| `TLSv1.3` | Optional | Modern preferred |

Cipher suites: CloudFront negotiates from a curated list. If the origin
only supports deprecated ciphers (RC4, 3DES, CBC-only), negotiation
fails with `no shared cipher`. Modern best practice: TLSv1.2+ with AEAD
ciphers (AES-GCM, ChaCha20-Poly1305).

## OAC vs OAI signing comparison

| Aspect | OAI (legacy) | OAC (current) |
|---|---|---|
| Principal in bucket policy | `CanonicalUser` (OAI's canonical ID) | `Service: cloudfront.amazonaws.com` |
| Authentication | Static OAI user; CF identifies itself implicitly | SigV4 signed requests with CloudFront service principal |
| Supports KMS | No | Yes (SSE-KMS via CloudFront) |
| Supports streaming | Limited | Yes |
| Signing behavior | Implicit; S3 recognises the OAI | Explicit; `SigningBehavior: always` or `nodisplay` |
| Migration path | Migrate to OAC; update bucket policy | N/A |

Required bucket policy statement for OAC:

```json
{
  "Sid": "AllowCloudFrontOAC",
  "Effect": "Allow",
  "Principal": {"Service": "cloudfront.amazonaws.com"},
  "Action": ["s3:GetObject", "s3:GetObjectVersion"],
  "Resource": "arn:aws:s3:::<bucket>/*",
  "Condition": {
    "StringEquals": {
      "AWS:SourceArn": "arn:aws:cloudfront::<account-id>:distribution/<distribution-id>"
    }
  }
}
```

For SSE-KMS buckets, also grant KMS decrypt:

```json
{
  "Sid": "AllowCloudFrontOACKMS",
  "Effect": "Allow",
  "Principal": {"Service": "cloudfront.amazonaws.com"},
  "Action": "kms:Decrypt",
  "Resource": "<kms-key-arn>",
  "Condition": {
    "StringEquals": {
      "AWS:SourceArn": "arn:aws:cloudfront::<account-id>:distribution/<distribution-id>"
    }
  }
}
```

## Lambda@Edge runtime caps

| Trigger | Memory | Timeout | Function size (compressed) | Logs location |
|---|---|---|---|---|
| Viewer request | 128 MB - 10240 MB | 5 seconds | 1 MB | us-east-1 only, `/aws/lambda/us-east-1.<fn>` |
| Origin request | 128 MB - 10240 MB | 30 seconds | 50 MB | us-east-1 only |
| Origin response | 128 MB - 10240 MB | 30 seconds | 50 MB | us-east-1 only |
| Viewer response | 128 MB - 10240 MB | 5 seconds | 1 MB | us-east-1 only |

Lambda@Edge functions DO NOT support:
- Environment variables
- Layers (Lambda Layers)
- Provisioned concurrency
- EFS mounts
- Container images

A function that references `process.env.X` will always see `undefined`.
A function that uses a Layer will fail at deploy time.

## Custom Error Response TTL behaviour

| Field | Effect |
|---|---|
| `ErrorCode` | The HTTP status from origin that triggers the custom response |
| `ResponseCode` | The HTTP status CF returns to the viewer (can differ from ErrorCode) |
| `ResponsePagePath` | Path to a custom error page object in S3 |
| `ErrorCachingMinTTL` | Minimum seconds to cache the error response at the edge |
| `TTL (computed)` | `max(ErrorCachingMinTTL, Cache-Control: max-age on error response)` |

Operators who set `ErrorCachingMinTTL: 300` for 502 will serve a stale
502 page for at least 5 minutes after the origin recovers. Best
practice during incidents: temporarily set `ErrorCachingMinTTL: 0` so
transient failures do not poison the cache.

## CloudFront response timeout matrix

| Origin type | Default timeout | Tunable? |
|---|---|---|
| Custom HTTP / ALB / NLB | 30 seconds | `ConnectionTimeout` (3-10s for connect; response timeout fixed) |
| S3 | 30 seconds | Not tunable |
| OriginShield hop | Adds its own 30s timeout | Not tunable |

A 504 (Gateway Timeout) means the origin did not return a complete
response within the timeout. CloudFront does NOT extend the timeout
for streaming origins.

## OriginShield routing changes

When OriginShield is enabled:
1. All edge POPs forward cache misses to the shield POP (in the
   configured shield region).
2. The shield POP consolidates concurrent requests (request
   coalescing).
3. The shield POP fetches from the origin.

Origin-side SG / firewall rules must allow traffic from the shield
POP's IP range, NOT just from individual edge POPs. The CloudFront
IP ranges are published at
`https://d7uri8nf7uskq.cloudfront.net/tools/list-cloudfront-ips`;
shield POPs use a subset of these ranges.

## Failover trigger criteria

An OriginGroup triggers failover when the primary origin returns any
status code in `FailoverCriteria.StatusCodes.Items`. Common sets:

- 5xx only: `[500, 502, 503, 504]`
- 4xx + 5xx: `[403, 404, 500, 502, 503, 504]` (also fail over on
  403/404 from origin)

A 502 from the primary origin triggers failover ONLY IF 502 is in the
list AND the CacheBehavior's TargetOriginId points at the group (not
the primary origin).

## Field-Level Encryption requirements

| Requirement | Detail |
|---|---|
| Viewer protocol | HTTPS-only (`ViewerProtocolPolicy: https-only` or `redirect-to-https`) |
| Public key | Uploaded to CloudFront key group; valid (not expired) |
| Query profile | Defined in `FieldLevelEncryptionConfig`; attached to behaviour |
| Content-Type | Must be in the profile's content-type list |
| Field count | Per-request field limit applies (max fields per profile) |

Common FLE failure patterns:
- HTTP request to FLE-enabled behaviour -> 502 (FLE requires HTTPS)
- Public key rotated but profile not updated -> 502 on every request
- Content-Type mismatch -> FLE skips; downstream may reject

## Distribution deployment lifecycle

| Status | Meaning |
|---|---|
| `Deployed` | Config is fully propagated; all POPs serving the latest version |
| `InProgress` | Config change is propagating; mixed POP behaviour expected for 5-15 minutes |
| (no `InProgressInvalidationBatches`) | No pending invalidation batches |

A 502 during `InProgress` is often the new revision rolling out
unevenly. Do NOT roll back unless the new config is genuinely broken.
Wait for `Deployed` before declaring an incident.

## AWS Health event categories that affect CloudFront

| Category | Likely impact |
|---|---|
| `AWS_CLOUDFRONT_SERVICE` | Region-wide or global CF degradation |
| `AWS_CLOUDFRONT_ORIGIN` | Issue with CF origin infrastructure |
| `AWS_S3_SERVICE` | S3-origin distributions affected |
| `AWS_LAMBDA_SERVICE` | Lambda@Edge functions affected |
| `AWS_REGIONAL_EVENT` | Broad customer impact |

Always probe `aws health describe-events` for regional issues before
declaring a customer-side root cause during a wide-impact incident.
