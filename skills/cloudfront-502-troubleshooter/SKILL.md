---
name: cloudfront-502-troubleshooter
description: >-
  Diagnoses CloudFront 502 and 504 errors via a fourteen-layer decision
  tree covering origin connection timeouts to ALB/NLB/S3 custom origins,
  SSL/TLS protocol and cipher mismatch between CloudFront and the origin,
  origin response too large, custom origin header validation failure,
  Lambda@Edge function runtime errors, S3 origin access control (OAC)
  misconfiguration, multi-origin failover, geographic restriction
  blocking, field-level encryption errors, response timeout (504),
  origin shield routing, distribution deployment state, and cached error
  responses where a Custom Error Response with high TTL hides a
  transient origin failure. Walks x-edge-result-type and x-cache headers,
  origin probe results, and distribution config to a verified root cause.
  Emits ROOT_CAUSE_IDENTIFIED or INSUFFICIENT_DATA with the specific
  failure layer and the probe output that confirms it.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). Offline diagnosis works from pasted CloudFront
  access-log excerpts, response headers, and distribution config JSON.
  Live-account diagnosis uses aws cloudfront get-distribution-config /
  get-distribution / list-origin-access-controls, aws logs
  filter-log-events on the us-east-1 CloudFront and Lambda@Edge log
  groups, aws s3api get-bucket-policy / head-object, aws elbv2
  describe-load-balancers / describe-target-health, and curl with
  --resolve against both the distribution domain and the origin host
  (AWS CLI v2, SSO or key-based credentials).
keywords:
  - CloudFront
  - 502
  - 504
  - Bad Gateway
  - Gateway Timeout
  - origin connection timeout
  - TLS negotiation failure
  - SSL protocol mismatch
  - cipher suite mismatch
  - Lambda@Edge
  - Origin Access Control
  - OAC
  - multi-origin failover
  - geographic restriction
  - field-level encryption
  - origin shield
  - cached error response
  - troubleshoot CloudFront
tags:
  - cloudfront
  - networking
  - cdn
  - troubleshooting
  - 502
  - tls
  - lambda-at-edge
  - oac
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Networking
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
  when_to_use: >-
    Diagnosing a CloudFront distribution returning 502 Bad Gateway or
    504 Gateway Timeout — including origin connection failures, TLS
    handshake errors, Lambda@Edge runtime exceptions, S3 OAC
    misconfiguration, failover routing, geographic blocks, field-level
    encryption failures, origin-shield errors, deployment-state
    artefacts, or stale error-cache entries hiding a now-recovered
    origin.
  when_not_to_use: >-
    Cache hit ratio / stale content without 502/504 (use
    cloudfront-cache-troubleshooter), cost analysis (use
    cloudfront-cost-optimizer), distribution creation (use
    cloudfront-distribution-deployer), or WAF 403 blocks (use
    wafv2-web-acl-deployer). This skill is scoped to 502/504-class
    origin and edge failures.
  activation_triggers:
    - CloudFront 502
    - CloudFront 504
    - CloudFront Bad Gateway
    - CloudFront origin connection failed
    - CloudFront TLS handshake failure
    - CloudFront Lambda@Edge error
    - CloudFront OAC 502
    - CloudFront failover 502
    - CloudFront geographic block
    - CloudFront origin shield 502
    - CloudFront cached 502
    - troubleshoot CloudFront 502
  invocation_schema: >-
    Input: either (a) a symptom description (502/504 status, the
    x-edge-result-type and x-cache values from access logs, viewer
    error message) optionally paired with the distribution
    configuration and curl reproduction, OR (b) a DistributionId plus
    viewer context for live-account diagnosis. Output: a deterministic
    TARGET / VERDICT / REASON / LAYER / EVIDENCE / REMEDIATION block
    where VERDICT ∈ {ROOT_CAUSE_IDENTIFIED, INSUFFICIENT_DATA} and
    LAYER ∈ {ORIGIN_CONNECTION_TIMEOUT,
    ORIGIN_TLS_PROTOCOL_MISMATCH, ORIGIN_TLS_CIPHER_MISMATCH,
    ORIGIN_RESPONSE_TOO_LARGE, CUSTOM_HEADER_VALIDATION,
    LAMBDA_AT_EDGE_ERROR, OAC_MISCONFIGURATION, FAILOVER_MISCONFIGURATION,
    GEO_RESTRICTION_BLOCKING, FIELD_LEVEL_ENCRYPTION_ERROR,
    ORIGIN_RESPONSE_TIMEOUT, ORIGIN_SHIELD_MISCONFIGURATION,
    DISTRIBUTION_NOT_DEPLOYED, CACHED_ERROR_RESPONSE, UNKNOWN}.
  invocation_example: |
    # Minimal valid input (offline symptom classification):
    Symptom: "CloudFront distribution d111111abcdef8.cloudfront.net
    returns HTTP 502 to all viewers on /api/* since 14:10 UTC.
    Origin is an ALB in us-east-1."
    DistributionId: E1Q2W3R4Y5Z6A7
    DomainName: d111111abcdef8.cloudfront.net
    Origin: api.alb.example.com (ALB, HTTPS-only)
    OriginProtocolPolicy: https-only
    x-edge-result-type from logs: Error
    x-cache from logs: Error from origin
    Last deployment: 1 hour ago (added OriginProtocolPolicy: https-only)
---

# CloudFront 502 Troubleshooter

## Quick start

- **Symptom -> layer map (first plausible match drives the first probe):**
  a fresh `502` after a config deploy -> LAMBDA_AT_EDGE_ERROR /
  CUSTOM_HEADER_VALIDATION / ORIGIN_TLS_PROTOCOL_MISMATCH; `502` only
  from one edge POP -> ORIGIN_SHIELD_MISCONFIGURATION; `504` after N
  seconds -> ORIGIN_RESPONSE_TIMEOUT or ORIGIN_CONNECTION_TIMEOUT;
  `502` from S3 origin only -> OAC_MISCONFIGURATION; `502` from one
  country -> GEO_RESTRICTION_BLOCKING; intermittent 502 lingering after
  origin recovery -> CACHED_ERROR_RESPONSE.
- **Read `x-cache` and `x-edge-result-type` before guessing.**
  `x-cache: Error from cloudfront` = edge produced the 502 (Lambda@Edge,
  FLE, geo, error cache); `x-cache: Error from origin` = origin
  returned 5xx to CF. The tree forks at this single field.
- **Reproduce from outside the cache first.** A `curl -H
  'Cache-Control: no-cache'` forces a fresh origin fetch. If the 502
  disappears, the cause is CACHED_ERROR_RESPONSE, not the live origin.
- **Probe the origin directly with the exact viewer request.** `curl
  --resolve <origin>:443:<ip>` with the same Host, protocol, path. A
  502 here proves origin-side fault; a 200 here proves the failure is
  between CF and the origin.
- **A new 502 that appears immediately after a distribution deploy is
  almost always the deploy, not the origin.** Check `Status: InProgress`
  first; mixed POP results during propagation are expected.

## Mindset

A CloudFront 502 is a transport- or transaction-layer failure between
the edge POP and the origin (or between the viewer and the edge when
Lambda@Edge fails). The body of the 502 page is generic; the
load-bearing evidence lives in `x-edge-result-type`, `x-cache`, and
`x-amz-cf-pop` of the access log and in the origin's own response
when probed directly. Senior CDN engineers start with the access log
row for a failing request, not the distribution config. The config
narrows the search; the log row identifies the layer.

## Philosophy

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

## Pre-flight: distribution state and gather-info gate

```bash
# 1. Distribution config (origins, behaviours, certificates, restrictions)
aws cloudfront get-distribution-config --id <id> --output json

# 2. Status and last-modified time
aws cloudfront get-distribution --id <id> --output json | \
  jq '.Distribution | {Status, DomainName, LastModifiedTime}'

# 3. CloudFront access logs (always us-east-1 log group)
aws logs filter-log-events \
  --log-group-name <cloudfront-log-group-arn> \
  --start-time $(date -d '-30 minutes' +%s)000 \
  --filter-pattern '"502" OR "504" OR "Error"' --output json

# 4. Reproduce from a viewer-like client (force fresh fetch)
curl -sv -H 'Cache-Control: no-cache' \
  https://<distribution-domain>/<failing-path> 2>&1 | \
  grep -E 'HTTP/|x-cache|x-amz-cf|x-edge'

# 5. Probe the origin directly, bypassing CloudFront
curl -sv --resolve <origin-host>:443:<origin-ip> \
  https://<origin-host>/<path> -H 'Host: <origin-host>' 2>&1
```

| `Status` | Effect on diagnosis |
|---|---|
| `Deployed` | Proceed with symptom-driven diagnosis. |
| `InProgress` | Config update is propagating (5-15 min). Mixed POP behaviour is expected. Wait before drawing conclusions. |
| `InProgress` > 30 minutes | Stuck deploy; open a Support case. |

The load-bearing access-log fields for 502 diagnosis: `x-edge-result-type`
(`Error` vs `FunctionExecutionError` vs `LimitExceeded`),
`x-edge-response-result-type`, `x-cache` (`Error from cloudfront` vs
`Error from origin`), `ssl-protocol` / `ssl-cipher` (viewer-side only),
`fle-status`, `time-taken`.

If the input is malformed (missing DistributionId, no symptom
description, no curl reproduction or access-log row), emit:

```text
TARGET: <distribution-id or unknown>
VERDICT: INSUFFICIENT_DATA
REASON: Input is missing required context — at minimum a symptom
  description (HTTP 502/504 status) and the DistributionId. Access-log
  excerpts or a curl reproduction are required for high-confidence
  layer identification.
LAYER: UNKNOWN
EVIDENCE:
  - Missing: <list specific missing fields>
REMEDIATION: Re-prompt the operator for: (1) DistributionId and failing
  path; (2) curl reproduction with response headers; (3) at least one
  access-log row showing the 502/504; (4) recent deployment timestamps.
```

## Quick reference — symptom triage table

| Symptom / log signal | Most likely layer | First probe |
|---|---|---|
| `x-cache: Error from origin` + origin unreachable | ORIGIN_CONNECTION_TIMEOUT | `elbv2 describe-target-health` (ALB) or `s3api head-object` (S3) |
| `x-cache: Error from origin` + handshake errors | ORIGIN_TLS_PROTOCOL_MISMATCH / ORIGIN_TLS_CIPHER_MISMATCH | `openssl s_client -connect origin:443` from edge-like client |
| 502 only on responses > 10 MB | ORIGIN_RESPONSE_TOO_LARGE | Origin `Content-Length` vs CF payload cap |
| 502 begins after adding `OriginCustomHeader` | CUSTOM_HEADER_VALIDATION | Compare header value at origin vs config |
| `x-edge-result-type: FunctionExecutionError` | LAMBDA_AT_EDGE_ERROR | `logs filter-log-events` on `/aws/lambda/us-east-1.<fn>` in us-east-1 |
| 502 only on S3 origin, ALB origin fine | OAC_MISCONFIGURATION | `s3api get-bucket-policy` + verify `cloudfront:GetResource` principal |
| 502 when primary fails; secondary never reached | FAILOVER_MISCONFIGURATION | `get-distribution-config` OriginGroups + behaviour `TargetOriginId` |
| 502 only from one country; `x-edge-result-type: LimitExceeded` | GEO_RESTRICTION_BLOCKING | `get-distribution-config` Restrictions.GeoRestriction |
| 502 with field-level encryption recently enabled | FIELD_LEVEL_ENCRYPTION_ERROR | Verify public key, query profile, content-type |
| `504` consistently after N seconds of TTFB | ORIGIN_RESPONSE_TIMEOUT | Origin app logs; curl TTFB measurement |
| 502 only when OriginShield enabled | ORIGIN_SHIELD_MISCONFIGURATION | `get-distribution-config` OriginShield config |
| `Status: InProgress`; mixed results across POPs | DISTRIBUTION_NOT_DEPLOYED | `get-distribution` Status, LastModifiedTime |
| Origin recovered but 502 persists for minutes | CACHED_ERROR_RESPONSE | `Cache-Control` / `age` header; Custom Error Response TTL |

## Process — Diagnostic decision tree

Symptom-driven. Each layer ends with a positive root-cause confirmation
(a failing probe that matches the symptom) or a pass that moves to the
next layer. **Never emit ROOT_CAUSE_IDENTIFIED without a failing probe
that matches the symptom.**

### Step 0: Non-obvious behaviours that change diagnosis

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

### Step 1: Symptom entry — pick the diagnostic branch

| Symptom | Branch |
|---|---|
| `x-edge-result-type: FunctionExecutionError` | Step 4 — Lambda@Edge |
| `x-edge-result-type: LimitExceeded` | Step 9 (geo) or WAF (out of scope) |
| `x-cache: Error from cloudfront` + fresh deploy | Step 5 (custom header) or Step 7 (OAC) |
| `x-cache: Error from origin` + ALB/NLB origin | Step 2 (connection) |
| `x-cache: Error from origin` + S3 origin | Step 7 (OAC) |
| `x-cache: Error from origin` + TLS handshake errors | Step 3 (TLS) |
| `504` consistently after N seconds | Step 11 (response timeout) |
| 502 only from specific country | Step 9 (geo restriction) |
| 502 lingers after origin recovered | Step 14 (cached error) |
| 502 with FLE recently enabled | Step 10 (FLE) |
| None of the above | Step 15 (escalate) |

### Step 2: ORIGIN_CONNECTION_TIMEOUT — origin unreachable

Symptom: `x-cache: Error from origin`, origin's own access log shows no
matching request (connection never established).

```bash
aws cloudfront get-distribution-config --id <id> --output json | \
  jq '.DistributionConfig.Origins.Items[].DomainName'

aws elbv2 describe-target-health --target-group-arn <arn> --output json
```

If `target-health` returns no healthy targets, **ROOT_CAUSE_IDENTIFIED**
with `LAYER: ORIGIN_CONNECTION_TIMEOUT`. For S3 origins, a 502 usually
means OAC (Step 7), not connection failure — S3 is highly available.

### Step 3: ORIGIN_TLS_PROTOCOL_MISMATCH / ORIGIN_TLS_CIPHER_MISMATCH

Symptom: `x-cache: Error from origin`, origin's access log shows zero
matching requests (handshake never completed). Often after a config
change to `OriginProtocolPolicy: https-only`.

```bash
aws cloudfront get-distribution-config --id <id> --output json | \
  jq '.DistributionConfig.Origins.Items[] |
      {DomainName, OriginProtocolPolicy, OriginSslProtocols}'

openssl s_client -connect <origin>:443 -servername <origin> -tls1_2 2>&1 | head -40
openssl s_client -connect <origin>:443 -servername <origin> -tls1_3 2>&1 | head -40
```

| Probe result | Layer |
|---|---|
| `OriginProtocolPolicy: https-only`, origin listens HTTP only | ORIGIN_TLS_PROTOCOL_MISMATCH |
| `OriginSslProtocols: [TLSv1.2]`, origin supports TLSv1.0 / TLSv1.1 only | ORIGIN_TLS_PROTOCOL_MISMATCH |
| Cipher suite negotiation fails (`no shared cipher`) | ORIGIN_TLS_CIPHER_MISMATCH |
| Origin certificate expired or untrusted chain | ORIGIN_TLS_PROTOCOL_MISMATCH (cert validation) |

Fix: align `OriginProtocolPolicy` with what the origin serves, and
ensure `OriginSslProtocols` includes at least one protocol the origin
supports.

### Step 4: LAMBDA_AT_EDGE_ERROR — function runtime failure

Symptom: `x-edge-result-type: FunctionExecutionError`. The function
(viewer-request / origin-request / origin-response / viewer-response)
threw an unhandled exception or exceeded its timeout cap.

```bash
aws cloudfront get-distribution-config --id <id> --output json | \
  jq '.DistributionConfig.CacheBehaviors.Items[].LambdaFunctionAssociations'

# Logs in us-east-1 ONLY for Lambda@Edge
aws logs filter-log-events \
  --log-group-name /aws/lambda/us-east-1.<function-name> \
  --start-time $(date -d '-30 minutes' +%s)000 \
  --filter-pattern '"ERROR" OR "Task timed out" OR "Unhandled"' \
  --region us-east-1 --output json
```

| Pattern | Cause |
|---|---|
| Function throws on specific request shape | Bad header parsing, undefined field, large payload |
| `Task timed out` | Function exceeds 5s (viewer) or 30s (origin) cap |
| Function size > 1 MB (viewer) / 50 MB (origin) | Exceeds Lambda@Edge size cap; deploy fails |
| 502 only on /specific-path | Function logic branches on URI; one branch throws |
| Function references `process.env.X` | Lambda@Edge does NOT support env vars; always undefined |

Fix: fix the function code, redeploy, and publish a new version ARN.

### Step 5: CUSTOM_HEADER_VALIDATION — origin rejects custom header

Symptom: `x-cache: Error from origin`, recent edit to
`OriginCustomHeader`. Origin's WAF / auth layer returns 4xx/5xx because
of header value mismatch.

```bash
aws cloudfront get-distribution-config --id <id> --output json | \
  jq '.DistributionConfig.Origins.Items[].CustomHeaders'
```

If the origin expects a different value or header name,
**ROOT_CAUSE_IDENTIFIED** with `LAYER: CUSTOM_HEADER_VALIDATION`. Align
the value in the distribution config OR update the origin's auth module.

### Step 6: ORIGIN_RESPONSE_TOO_LARGE — payload cap exceeded

Symptom: 502 only on large responses.

```bash
curl -sv --resolve <origin>:443:<ip> https://<origin>/<large-path> \
  -o /dev/null -w '%{size_download} %{http_code}\n'
```

If `size_download` consistently hits a cap and CF truncates with 502,
**ROOT_CAUSE_IDENTIFIED** with `LAYER: ORIGIN_RESPONSE_TOO_LARGE`. Fix:
paginate, use range requests, or move to S3 with byte-range serving.

### Step 7: OAC_MISCONFIGURATION — S3 origin access control

Symptom: `x-cache: Error from origin` for S3 origin; bucket policy
recently edited or migrated OAI -> OAC.

```bash
aws cloudfront get-distribution-config --id <id> --output json | \
  jq '.DistributionConfig.Origins.Items[] |
      {DomainName, S3OriginConfig, OriginAccessControlId}'

aws cloudfront list-origin-access-controls --output json
aws s3api get-bucket-policy --bucket <bucket> --output json
```

| Pattern | Cause |
|---|---|
| Bucket policy grants legacy OAI (`CanonicalUser`), CF uses OAC | Principal mismatch; S3 returns 403 to CF |
| OAC `SigningBehavior: always`, bucket policy lacks `cloudfront:GetResource` | S3 rejects the signed request |
| Bucket policy restricts by `aws:SourceIp`; CF IPs not allowed | S3 denies |
| Migrated OAI -> OAC, bucket policy not updated | Policy still references the OAI principal |

Fix: update the bucket policy to grant the OAC principal
(`Service: cloudfront.amazonaws.com`) with `AWS:SourceArn` equal to the
distribution ARN.

### Step 8: FAILOVER_MISCONFIGURATION — multi-origin routing

Symptom: 502 when primary fails; secondary never receives traffic.

```bash
aws cloudfront get-distribution-config --id <id> --output json | \
  jq '.DistributionConfig.OriginGroups.Items[] |
      {Id, FailoverCriteria, Members}'
# Verify the behaviour points at the group, not the single origin
jq '.DistributionConfig.CacheBehaviors.Items[].TargetOriginId'
```

| Pattern | Cause |
|---|---|
| Behaviour `TargetOriginId` is the primary origin, not the group | Failover never triggers |
| `FailoverCriteria.StatusCodes` excludes the 5xx primary returns | Group considers primary healthy |
| Secondary origin unreachable | Failover triggers but secondary also fails |

### Step 9: GEO_RESTRICTION_BLOCKING — geographic block

Symptom: 502 / 403 only from one country. `x-edge-result-type: LimitExceeded`.

```bash
aws cloudfront get-distribution-config --id <id> --output json | \
  jq '.DistributionConfig.Restrictions.GeoRestriction'
```

If the failing viewer's country is on the wrong side of a `whitelist` or
`blacklist`, **ROOT_CAUSE_IDENTIFIED** with
`LAYER: GEO_RESTRICTION_BLOCKING`. Note: CF returns 403 for geo blocks,
but a Custom Error Response can map this to 502 if misconfigured.

### Step 10: FIELD_LEVEL_ENCRYPTION_ERROR — FLE failure

Symptom: 502 with FLE recently enabled. Access log shows
`fle-status: error` or empty `fle-encrypted-fields`.

| Pattern | Cause |
|---|---|
| FLE on HTTP behaviour | FLE requires HTTPS-only viewer requests |
| Public key expired or rotated without updating profile | Encryption fails; CF returns 502 |
| Query profile missing from the behaviour | FLE has no profile to apply |
| Content-Type not in the FLE content-type list | FLE skips; downstream may reject |

Fix: HTTPS-only, valid public key, content-type match.

### Step 11: ORIGIN_RESPONSE_TIMEOUT — 504

Symptom: `504` consistently after N seconds. Origin TTFB exceeds CF's
30-second response timeout.

```bash
curl -sv --resolve <origin>:443:<ip> https://<origin>/<slow-path> \
  -o /dev/null -w '%{time_starttransfer}s %{time_total}s\n'
```

If TTFB consistently exceeds 30s, **ROOT_CAUSE_IDENTIFIED** with
`LAYER: ORIGIN_RESPONSE_TIMEOUT`. Fix: optimise the origin (DB query,
cache), or move the long-running operation to async.

### Step 12: ORIGIN_SHIELD_MISCONFIGURATION

Symptom: 502 only when OriginShield enabled; disabling it makes the 502
disappear.

```bash
aws cloudfront get-distribution-config --id <id> --output json | \
  jq '.DistributionConfig.Origins.Items[].OriginShield'
```

OriginShield changes the source IP range (shield POP, not edge POPs).
Origin firewalls that whitelisted edge-POP IPs will block shield traffic.
**ROOT_CAUSE_IDENTIFIED** with `LAYER: ORIGIN_SHIELD_MISCONFIGURATION`.

### Step 13: DISTRIBUTION_NOT_DEPLOYED

Symptom: 502 begins immediately after a config edit; behaviour is
inconsistent across POPs.

```bash
aws cloudfront get-distribution --id <id> --output json | \
  jq '.Distribution | {Status, LastModifiedTime}'
```

If `Status: InProgress`, the new config is still propagating; mixed
results are normal. **ROOT_CAUSE_IDENTIFIED** with
`LAYER: DISTRIBUTION_NOT_DEPLOYED`. Fix: wait for `Deployed`; do not
roll back unless the new config is genuinely broken.

### Step 14: CACHED_ERROR_RESPONSE — stale error cache

Symptom: Origin recovered (direct probe returns 200), but CloudFront
continues to serve 502. Access log shows
`x-cache: Error from cloudfront`.

```bash
aws cloudfront get-distribution-config --id <id> --output json | \
  jq '.DistributionConfig.CustomErrorResponses'

curl -sv -H 'Cache-Control: no-cache' \
  https://<distribution>/<path> 2>&1 | grep -E 'HTTP/|x-cache|age:'
```

If a no-cache request succeeds but the cached request still returns
502, a Custom Error Response with non-zero `ErrorCachingMinTTL` is the
cause. **ROOT_CAUSE_IDENTIFIED** with `LAYER: CACHED_ERROR_RESPONSE`.
Fix: invalidate the error path.

```bash
aws cloudfront create-invalidation --distribution-id <id> \
  --paths '/<path>/*' --profile <p>
```

### Step 15: Escalate or INSUFFICIENT_DATA

If none of the above produced a positive root-cause match, OR the
symptom indicates an AWS-side incident (regional CloudFront event, S3
outage), emit INSUFFICIENT_DATA with `LAYER: UNKNOWN` (or escalate via
INSUFFICIENT_DATA noting the AWS Health event ARN).

## Output format

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
  - <observed symptom — status code, x-edge-result-type, x-cache>
  - <failing probe — command and its output that confirms the cause>
  - <passing probes — layers ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
CONFIRM: Before executing any state-changing CLI, emit and await
  operator approval: "CONFIRM: About to <action> on <distribution-id>.
  Proceed? (yes/no)"
```

## Anti-Patterns — NEVER

- NEVER declare ROOT_CAUSE_IDENTIFIED without a failing probe that
  matches the symptom. A "process of elimination" diagnosis erodes
  operator trust.

- NEVER conflate viewer-to-edge TLS with edge-to-origin TLS. The
  distribution's ViewerCertificate and OriginSslProtocols are
  independent. A green viewer-side padlock does NOT mean the origin
  handshake is healthy.

- NEVER debug an S3 origin's 502 as a "connection issue." S3 is highly
  available; the cause is almost always OAC/bucket policy. Probe OAC
  before connection-layer tools.

- NEVER tail Lambda@Edge logs in the distribution's region. Lambda@Edge
  function logs are in us-east-1 only. The log group is
  `/aws/lambda/us-east-1.<function-name>`.

- NEVER assume a Custom Error Response is harmless. A high TTL on
  error responses hides recovered origins for minutes. Always check
  CustomErrorResponses before declaring a CF-side bug.

- NEVER add OriginShield without confirming the origin's firewall
  accepts traffic from CloudFront's shield POP IPs. OriginShield changes
  the source IP range.

- NEVER define an OriginGroup without attaching a CacheBehavior to it.
  Failover does not trigger unless the behaviour's `TargetOriginId` is
  the group, not the primary origin.

- NEVER treat a 502 during `Status: InProgress` as an origin failure.
  Mixed POP results during propagation are normal. Wait for `Deployed`.

- NEVER migrate OAI to OAC without updating the bucket policy. The OAC
  principal (`Service: cloudfront.amazonaws.com` with SourceArn) differs
  from the OAI canonical user. Leaving the old policy breaks every
  S3-origin request.

- NEVER enable FLE on an HTTP-allowed behaviour. FLE requires HTTPS-only
  viewer requests; enabling FLE on a behaviour that allows HTTP produces
  502s on all HTTP requests.

- NEVER assume the `x-edge-result-type` field is optional. It is the
  single most disambiguating field. A 502 with `FunctionExecutionError`
  is a Lambda@Edge problem; a 502 with `Error` is an origin problem.

- NEVER recommend `match-viewer` for OriginProtocolPolicy without
  flagging the security implication: if any viewer uses HTTP, the origin
  fetch is also HTTP (cleartext). Prefer `https-only`.

## Pre-flight safety checks

- **MANDATORY CONFIRMATION GATE.** Before `update-distribution`,
  `create-invalidation`, or `delete-distribution`, emit and await
  operator approval.

- **Read-only first.** Every probe is read-only (`get-distribution`,
  `get-distribution-config`, `filter-log-events`, `describe-target-health`,
  `head-object`, `get-bucket-policy`, `openssl s_client`). Do not run
  state-changing operations as diagnostic probes.

- **`update-distribution`** moves Status to `InProgress` for 5-15 min;
  mixed POP behaviour during this window is expected.

- **`create-invalidation`** is billable after 1,000 paths/month. Use
  `/*` sparingly; target specific failing paths.

- **Lambda@Edge versioning.** A new function version does not affect the
  distribution until you update the
  `LambdaFunctionAssociations[].LambdaFunctionARN` to the new version.

- **Bucket policy edits** affect every consumer of the bucket. Tighten
  gradually; never deny-by-default without confirming no other CF
  distribution depends on the bucket.

## Configuration dependency graph

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

## Expert heuristic

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

## Domain

AWS CloudOps / CloudFront CDN Edge Networking, Origin Integration,
Lambda@Edge Runtime, and S3 Origin Access Control.

## AWS documentation

- **CloudFront HTTP 502 status code** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/http-502-bad-gateway.html
- **CloudFront HTTP 504 status code** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/http-504-gateway-timeout.html
- **Origin access control** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html
- **Lambda@Edge** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/lambda-at-the-edge.html
- **Origin Shield** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/origin-shield.html
- **Custom Error Responses** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/GeneratingCustomErrors.html
- **CloudFront access logs** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/AccessLogs.html
