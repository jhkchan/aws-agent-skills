---
name: cloudfront-distribution-auditor
description: >-
  Audits AWS CloudFront distributions for insecure TLS viewer minimum protocol
  versions and viewer protocol policies, missing Origin Access Control (OAC) on
  S3 origins, missing WAF Web ACL association, disabled access logging, absent
  geographic restrictions, and default-cache-behavior misconfigurations. Emits a
  deterministic verdict (INSECURE_TLS | NO_OAC | CONFIG_GAP | OK) per
  distribution with enumerated findings and CLI remediation. Use when reviewing
  a CloudFront distribution before production deployment, checking TLS posture,
  validating OAC on S3 origins, verifying WAF coverage, auditing logging status,
  or hardening edge security.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline distribution-config classification.
  Live-account audits use aws cloudfront get-distribution-config,
  aws cloudfront get-origin-access-control, and aws cloudfront list-distributions
  (AWS CLI v2, SSO or key-based credentials).
keywords:
  - CloudFront
  - distribution audit
  - TLS minimum protocol
  - TLSv1.2_2021
  - Origin Access Control
  - OAC
  - OAI
  - ViewerProtocolPolicy
  - OriginProtocolPolicy
  - WAF association
  - Web ACL
  - access logging
  - geographic restrictions
  - geo restriction
  - default cache behavior
  - default root object
  - S3 website endpoint
  - edge security
  - HTTPS enforcement
  - distribution hardening
tags: [cloudfront, security, tls, oac, waf, logging, geo-restriction, networking, audit]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Networking
  verdict_shape: "INSECURE_TLS | NO_OAC | CONFIG_GAP | OK"
  when_to_use: >-
    Reviewing a CloudFront distribution before production deployment, checking
    TLS minimum protocol version, validating Origin Access Control on S3
    origins, verifying WAF Web ACL association, auditing access logging,
    inspecting geographic restrictions, or hardening edge security posture
    across distributions.
  activation_triggers:
    - "audit this CloudFront distribution"
    - "is my CloudFront TLS secure"
    - "check CloudFront OAC"
    - "is OAC configured on my S3 origin"
    - "does my distribution have a WAF"
    - "CloudFront logging disabled"
    - "geo restriction CloudFront"
    - "ViewerProtocolPolicy allow-all"
    - "hardening CloudFront before production"
    - "OriginProtocolPolicy http-only"
  invocation_schema: >-
    Input: either (a) a CloudFront distribution config JSON, optionally paired
    with origin-access-control metadata, OR (b) a distribution id for
    live-account audit. Output: deterministic DISTRIBUTION/VERDICT/REASON/
    FINDINGS/REMEDIATION block per distribution, where VERDICT belongs to
    {INSECURE_TLS, NO_OAC, CONFIG_GAP, OK, ERROR}.
---

# CloudFront Distribution Auditor

## Mindset

**One-line takeaway:** the verdict is always the **worst** finding across all
dimensions, and three CloudFront misconfigurations dominate real-world
incidents — weak TLS minimum protocol (cipher-suite downgrade), missing OAC on
S3 origins (direct bucket bypass), and absent WAF at the edge (no L7 filtering).

CloudFront is the public edge of your infrastructure. Every request from every
user touches it before reaching origins.
- **TLS minimum protocol** is the weakest cipher a viewer may negotiate. A
  weak policy silently downgrades connections even when the browser supports
  stronger ciphers — the server picks the floor, not the ceiling.
- **Missing OAC on an S3 origin** means the bucket must be publicly readable
  for CloudFront to serve content. Users can bypass CloudFront entirely and
  hit the bucket directly — WAF, geo restrictions, and signed URLs all
  evaporate.
- **No WAF at the edge** means OWASP attacks (SQLi, XSS, path traversal)
  reach the origin unfiltered. The origin must defend itself, which defeats
  the purpose of an edge security layer.

## Quick reference — verdict thresholds

| Condition | Verdict | Step |
|---|---|---|
| `MinimumProtocolVersion` < `TLSv1.2_2021` | **INSECURE_TLS** | Step 2 |
| `ViewerProtocolPolicy: allow-all` on default cache behavior | **INSECURE_TLS** | Step 1 |
| Custom origin `OriginProtocolPolicy: http-only` or `match-viewer` | **INSECURE_TLS** | Step 3 |
| Origin domain is S3 website endpoint (`s3-website-*`) | **INSECURE_TLS** | Step 4 |
| S3 REST origin with no OAC AND no legacy OAI | **NO_OAC** | Step 5 |
| No WAF Web ACL associated (`WebACLId` empty) | **CONFIG_GAP** | Step 6 |
| `Logging.Enabled: false` | **CONFIG_GAP** | Step 7 |
| `GeoRestriction.RestrictionType: none` | **CONFIG_GAP** | Step 8 |
| Empty `DefaultRootObject` on S3 origin | **CONFIG_GAP** | Step 9 |
| All dimensions pass | **OK** | Step 10 |

See the ordered steps below for edge cases. The verdict priority is
INSECURE_TLS > NO_OAC > CONFIG_GAP > OK.

## Pre-flight: distribution metadata gate

Before evaluating the distribution config, classify the distribution itself.
Several attributes **short-circuit** the audit.

**Multi-distribution sweep note (pagination):** when auditing every
distribution in an account, `aws cloudfront list-distributions` returns at
most 200 per page. Use `--marker` from the prior `NextMarker` to page through
all distributions; iterating only the first page silently skips stale or
forgotten distributions (the ones most likely to be misconfigured).

| Attribute | Value | Effect on audit |
|---|---|---|
| `Enabled` | `false` | **Disabled distribution** — serves no traffic. Note as operational but still audit the config (it may be re-enabled). |
| `Enabled` | `true` | Proceed with full audit. |
| Origin type | S3 REST (`*.s3.amazonaws.com`, `*.s3.<region>.amazonaws.com`) | Evaluate OAC/OAI (Step 5). |
| Origin type | S3 website (`*.s3-website-*.amazonaws.com`) | **Critical** — jump to Step 4. Forces public bucket. |
| Origin type | Custom (`api.example.com`, ALB, etc.) | Evaluate OriginProtocolPolicy (Step 3). Skip OAC check. |
| `ViewerCertificate.Certificate` | ACM cert not in us-east-1 | Note as deployment risk — CloudFront requires ACM certs in us-east-1. |

**If the distribution config JSON is malformed** (invalid JSON, missing
`Origins` or `DefaultCacheBehavior`), output:

```text
DISTRIBUTION: <id>
VERDICT: ERROR
REASON: Distribution config is not valid JSON or is missing required fields — cannot classify.
REMEDIATION: Retrieve the canonical config with `aws cloudfront get-distribution-config --id <id> --output json` and re-audit.
```

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious CloudFront behaviors that change classification

These behaviors are easy to misjudge without operational CloudFront experience.
Each changes a verdict if ignored:

- **TLSv1.2_2021 vs TLSv1.2_2019 is a cipher-suite difference, not a protocol
  difference.** Both policies negotiate TLS 1.2+, but `_2021` removes all CBC-mode
  ciphers, keeping only AEAD suites (GCM). `TLSv1.2_2019` still permits
  `ECDHE-RSA-AES128-SHA256` (CBC), which is vulnerable to padding-oracle
  variants under specific conditions. The threshold for INSECURE_TLS is anything
  below `TLSv1.2_2021`. A policy of `TLSv1.2_2018` or `TLSv1.2_2019` looks
  "TLS 1.2" but silently includes weak ciphers. Do NOT treat TLSv1.2_2019 as
  acceptable — the year suffix is the cipher policy, not the TLS version.

- **ViewerProtocolPolicy `redirect-to-https` still accepts the initial HTTP
  request.** The 301 redirect happens server-side after CloudFront receives the
  request. The request URL (including query parameters) travels over HTTP
  before the redirect. For strict environments (PII in query strings, tokens in
  URLs), `https-only` is the only policy that rejects HTTP at the edge.
  `redirect-to-https` is acceptable for most workloads but flag the distinction.

- **OriginProtocolPolicy `match-viewer` propagates the viewer's protocol to the
  origin.** If the viewer connected over HTTP (before a redirect-to-https), and
  the origin protocol is `match-viewer`, CloudFront connects to the origin over
  HTTP too. This double-exposure (viewer AND origin on HTTP) is why
  `match-viewer` on custom origins is classified as INSECURE_TLS, not
  CONFIG_GAP.

- **OAC vs OAI is not cosmetic.** Origin Access Control (OAC) replaced Origin
  Access Identity (OAI) in 2022. OAC supports SSE-KMS (OAI does not — OAI
  cannot pass the KMS Decrypt permission, breaking encrypted S3 origins). OAC
  also supports IPv6. An S3 origin with OAI but no OAC on an SSE-KMS bucket
  silently fails (403 Access Denied on object GETs). The presence of OAI does
  NOT satisfy the OAC requirement — it is a legacy mechanism that should be
  migrated. However, OAI does keep the bucket private, so it is classified as
  CONFIG_GAP (should migrate), not NO_OAC (bucket is public).

- **S3 website endpoint as origin forces a public bucket.** The S3 website
  endpoint (`bucket.s3-website-us-east-1.amazonaws.com`) serves content only
  if the bucket has public read access — it bypasses S3 access policies
  entirely. Using it as a CloudFront origin means the bucket is publicly
  listable and readable. This is categorically different from the S3 REST
  endpoint, which works with OAC/OAI and private buckets. Always classify a
  website-endpoint origin as INSECURE_TLS (Step 4) — the remediation is to
  switch to the REST endpoint and configure OAC.

- **CloudFront WAF Web ACLs must be in us-east-1.** CloudFront is a global
  service, but the associated Web ACL must exist in us-east-1. A Web ACL in
  any other region cannot be associated. This is an AWS hard constraint, not
  a best practice. When verifying WAF association in a live account, check
  `aws wafv2 list-web-acls --scope CLOUDFRONT --region us-east-1` — the
  `CLOUDFRONT` scope only exists in us-east-1.

- **WebACLId field stores the ARN for WAFv2.** Even when using WAFv2 (not
  WAF Classic), the distribution config field is named `WebACLId` and contains
  the full Web ACL ARN (`arn:aws:wafv2:us-east-1:...:webacl/name/id`). An
  empty string means no WAF is associated. Do not confuse `WebACLId: ""`
  with "WAFv2 not supported" — it simply means no association.

- **Default root object absence leaks S3 listings.** If `DefaultRootObject`
  is empty and the origin is S3, a request to the distribution root path
  returns the S3 XML bucket listing (in REST mode) or the website index
  (in website mode). The REST listing exposes object keys, sizes, and last-
  modified timestamps — an information disclosure that aids enumeration
  attacks. Set `DefaultRootObject` to `index.html` (or equivalent) even if
  the distribution serves only API paths.

- **CloudFront access logging requires a bucket ACL grant.** The logging
  target bucket must grant WRITE and READ_ACP permissions to the
  `awslogsdelivery` account canonical ID. CloudFront does not use bucket
  policies for log delivery — it uses ACLs. A bucket with ACLs disabled
  (BucketOwnerEnforced) will silently reject logs. This is the most common
  cause of "logging enabled but no logs appearing."

- **Field-level encryption is deprecated.** Removed in 2024. Any distribution
  still referencing a field-level encryption profile is relying on a
  decommissioned feature. Flag as a CONFIG_GAP and recommend CloudFront
  Functions for request-body encryption.

- **TrustedKeyGroups empty does not always mean no access control.** Signed
  URLs/cookies require trusted key groups OR trusted signers (legacy). An
  empty list means no signed-URL protection on the cache behavior — but only
  flag this if the content is intended to be access-controlled (paywalled,
  authenticated). Public content does not need signed URLs.

### Step 1: Viewer protocol policy (TLS exposure to the viewer)

Evaluate `DefaultCacheBehavior.ViewerProtocolPolicy`:

- **`allow-all`** → **INSECURE_TLS**. CloudFront serves content over both
  HTTP and HTTPS. HTTP traffic between viewer and edge is sniffable,
  modifiable (MITM), and never encrypted. This is the most severe TLS finding
  because it actively serves unencrypted content.

- **`redirect-to-https`** → OK for this dimension (note the initial-HTTP
  caveat from Step 0). Acceptable for most workloads.

- **`https-only`** → OK. CloudFront rejects all HTTP requests at the edge.

### Step 2: TLS minimum protocol version

Evaluate `ViewerCertificate.MinimumProtocolVersion`. The threshold is
`TLSv1.2_2021` — anything below is INSECURE_TLS:

| Value | Verdict | Reason |
|---|---|---|
| `SSLv3` | **INSECURE_TLS** | POODLE attack — completely broken protocol. |
| `TLSv1` | **INSECURE_TLS** | Deprecated (RFC 8996). Enables BEAST, CRIME variants. |
| `TLSv1_2016` | **INSECURE_TLS** | Allows TLS 1.0 negotiation; weak cipher suite. |
| `TLSv1.1_2016` | **INSECURE_TLS** | Allows TLS 1.0/1.1 negotiation; deprecated protocols. |
| `TLSv1.2_2018` | **INSECURE_TLS** | Includes CBC-mode ciphers vulnerable to padding oracles. |
| `TLSv1.2_2019` | **INSECURE_TLS** | Still permits `ECDHE-RSA-AES128-SHA256` (CBC); weaker than 2021. |
| `TLSv1.2_2021` | **OK** | AEAD-only cipher suite (GCM); minimum acceptable posture. |

If there is no `ViewerCertificate` block (the distribution uses the default
CloudFront certificate), this only applies if the distribution has alternate
domain names. A distribution with no alternate domain names uses the default
`*.cloudfront.net` certificate, which is always TLS 1.2+ — skip this check.

### Step 3: Origin protocol policy (custom origins only)

For origins with `CustomOriginConfig`, evaluate `OriginProtocolPolicy`:

- **`http-only`** → **INSECURE_TLS**. CloudFront connects to the origin over
  plaintext HTTP. All traffic between edge and origin (including custom
  headers with secrets) is unencrypted.

- **`match-viewer`** → **INSECURE_TLS**. If the viewer used HTTP (before a
  redirect), CloudFront connects to the origin over HTTP too. The origin
  traffic inherits the viewer's (potentially insecure) protocol.

- **`https-only`** → OK. CloudFront always uses HTTPS to the origin.

Skip this step for S3 origins — CloudFront-to-S3 traffic uses S3's internal
protocol and is encrypted in transit by AWS infrastructure.

### Step 4: S3 website endpoint origin (forces public bucket)

If any origin's `DomainName` matches the S3 website endpoint pattern
(`*.s3-website-*.amazonaws.com`), classify as **INSECURE_TLS**. The website
endpoint requires the bucket to be publicly readable — it bypasses S3 access
policies entirely. Users can enumerate and read objects directly from the
bucket, bypassing CloudFront, WAF, and geo restrictions.

The remediation is to switch the origin to the REST endpoint
(`bucket.s3.amazonaws.com`) and configure OAC. This is Step 4 (before OAC
check) because it is both an origin exposure AND a TLS issue (website
endpoints do not support HTTPS on the origin connection).

### Step 5: Origin Access Control (S3 REST origins)

For each S3 REST origin (`*.s3.amazonaws.com`, `*.s3.<region>.amazonaws.com`,
`*.s3.dualstack.*.amazonaws.com`):

- **`OriginAccessControlId` is present and non-empty** → OK for this
  dimension. The OAC is configured (verify the OAC exists via
  `aws cloudfront get-origin-access-control --id <id>`).

- **`OriginAccessControlId` is empty AND
  `S3OriginConfig.OriginAccessIdentity` is empty** → **NO_OAC**. Neither OAC
  nor legacy OAI is configured. The S3 bucket must be publicly readable for
  CloudFront to serve content. Users can bypass CloudFront and access the
  bucket directly.

- **`OriginAccessControlId` is empty AND
  `S3OriginConfig.OriginAccessIdentity` is non-empty** → **CONFIG_GAP**
  (not NO_OAC). The legacy OAI keeps the bucket private (not an exposure),
  but OAI is deprecated and does not support SSE-KMS. Flag for migration to
  OAC.

A distribution with multiple S3 origins where ANY origin lacks OAC is
classified by the **worst** origin — one origin without OAC means NO_OAC for
the whole distribution.

### Step 6: WAF Web ACL association

Evaluate `WebACLId`:

- **`WebACLId` is empty or absent** → **CONFIG_GAP**. No WAF at the edge.
  OWASP attacks (SQLi, XSS, bot, path traversal) reach the origin unfiltered.
  The origin must defend itself, defeating the purpose of edge security.

- **`WebACLId` contains a Web ACL ARN** → OK for this dimension. The WAF is
  associated. Note: verify the Web ACL has rules (an empty Web ACL provides
  no protection) — but this audit checks association, not rule quality (use
  the `wafv2-web-acl-auditor` skill for rule-level analysis).

### Step 7: Access logging

Evaluate `Logging.Enabled`:

- **`Logging.Enabled: false`** → **CONFIG_GAP**. No access logs. Breach
  forensics, anomaly detection, and compliance auditing have no signal. For
  PCI/HIPAA/SOC2, logging is a control requirement.

- **`Logging.Enabled: true`** → OK for this dimension. Note: verify the
  logging bucket has the correct ACL grant for `awslogsdelivery` (Step 0
  expert note). Enabled logging with a misconfigured bucket silently drops
  logs.

### Step 8: Geographic restrictions

Evaluate `Restrictions.GeoRestriction.RestrictionType`:

- **`none`** → **CONFIG_GAP**. No geo restriction. The distribution serves
  all countries. For workloads with regulatory or compliance boundaries
  (GDPR data residency, OFAC sanctions), this is a control gap.

- **`whitelist`** → OK. Only listed countries can access.
- **`blacklist`** → OK. Listed countries are blocked.

### Step 9: Default root object

Evaluate `DefaultRootObject`:

- **Empty string AND origin is S3** → **CONFIG_GAP**. Requests to the
  distribution root return the S3 XML object listing — information disclosure
  of object keys and metadata.

- **Non-empty** → OK for this dimension.
- **Empty AND origin is custom** → note but do not flag (custom origins
  handle root requests per their own logic).

### Step 10: Aggregation — worst finding wins

The final verdict is the **maximum severity** across all findings, where
INSECURE_TLS > NO_OAC > CONFIG_GAP > OK:

```text
verdict = max(all_step_severities)
```

If no findings (all dimensions pass), the verdict is **OK**.

## Output format (per distribution)

```text
DISTRIBUTION: <distribution-id>
VERDICT: INSECURE_TLS | NO_OAC | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its step number>
FINDINGS:
  - [INSECURE_TLS] <finding description (Step N)>
  - [CONFIG_GAP] <finding description (Step N)>
  - [OK] <dimension that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — weak TLS and missing OAC

```text
DISTRIBUTION: E1A2B3C4D5
VERDICT: INSECURE_TLS
REASON: MinimumProtocolVersion is TLSv1.2_2019 (below TLSv1.2_2021 — CBC-mode
ciphers still permitted) (Step 2). S3 origin also has no OAC (Step 5).
FINDINGS:
  - [INSECURE_TLS] MinimumProtocolVersion TLSv1.2_2019 includes CBC-mode ciphers
    vulnerable to padding-oracle variants (Step 2) — TLSv1.2_2021 removes them
  - [NO_OAC] S3 origin "app-bucket.s3.amazonaws.com" has no OAC and no legacy
    OAI — bucket must be publicly readable (Step 5)
  - [CONFIG_GAP] No WAF Web ACL associated (Step 6)
  - [CONFIG_GAP] Logging.Enabled is false (Step 7)
REMEDIATION:
  1. Update MinimumProtocolVersion to TLSv1.2_2021.
  2. Create OAC and attach to the S3 origin; update bucket policy.
  3. Associate a Web ACL (must be in us-east-1).
  4. Enable access logging to an S3 bucket with awslogsdelivery ACL grant.
```

## Edge-case handling

- **Partially malformed config.** If the config JSON parses but individual
  sections are missing (e.g., `Origins` exists but `DefaultCacheBehavior` is
  absent), classify the available dimensions and emit an ERROR note for the
  missing section. Do NOT classify the entire distribution as ERROR when only
  one dimension is unparseable.

- **Multiple cache behaviors.** Only the **default** cache behavior's
  `ViewerProtocolPolicy` drives the verdict. Path-specific cache behaviors
  may have tighter policies, but the default behavior applies to all paths
  that do not match a pattern — it is the broadest exposure surface.

- **Multiple S3 origins.** Audit each origin independently. If ANY S3 origin
  lacks OAC, the distribution verdict is NO_OAC (or worse). A single exposed
  origin compromises the entire distribution.

- **Distribution with both S3 and custom origins.** Evaluate each origin by
  its type — S3 origins go through Steps 4-5, custom origins go through Step 3.
  Both findings contribute to the aggregate verdict.

- **ACM certificate in non-us-east-1 region.** Note as a deployment risk but
  do not change the verdict. CloudFront will reject the association at deploy
  time; this finding surfaces the issue before the operator attempts deployment.

- **Real-time logging vs standard logging.** `Logging.Enabled` covers standard
  access logging. Real-time logging is configured separately
  (`DistributionConfig.RealtimeLogConfigArn`). If real-time logging is
  configured but standard logging is disabled, note that real-time logging
  is present but do not flag the CONFIG_GAP — real-time logging satisfies the
  visibility requirement.

## Anti-Patterns — NEVER

- NEVER classify `MinimumProtocolVersion: TLSv1.2_2019` as OK. The `_2019`
  policy still permits CBC-mode ciphers (`ECDHE-RSA-AES128-SHA256`). Only
  `TLSv1.2_2021` restricts the cipher suite to AEAD-only (GCM). Treating
  `_2019` as acceptable misses the cipher-suite downgrade — the most
  common false-negative in CloudFront TLS audits.

- NEVER treat `ViewerProtocolPolicy: allow-all` as acceptable. This actively
  serves content over plaintext HTTP — every request between viewer and edge
  is sniffable. `allow-all` is not "flexible"; it is a compliance violation
  under PCI-DSS 4.1, HIPAA 164.312(e), and SOC2 CC6.1.

- NEVER classify an S3 origin without OAC as CONFIG_GAP when OAI is also
  absent. Without either mechanism, the bucket MUST be public — that is a
  direct-origin bypass, not a configuration gap. OAI-only (no OAC) is
  CONFIG_GAP; neither OAC nor OAI is NO_OAC.

- NEVER treat `OriginProtocolPolicy: match-viewer` as equivalent to
  `https-only`. `match-viewer` propagates the viewer's protocol — if the
  viewer connected over HTTP (before a redirect-to-https), the origin
  connection is also HTTP. Only `https-only` guarantees encrypted origin
  traffic regardless of viewer protocol.

- NEVER classify an S3 website endpoint origin as a simple origin type
  difference. The website endpoint forces the bucket to be publicly readable
  — it bypasses all S3 access policies. This is an active data exposure, not
  a style preference. The only valid remediation is switching to the REST
  endpoint with OAC.

- NEVER assume `WebACLId: ""` means "WAFv2 not supported on this
  distribution." The field stores the WAFv2 ARN for WAFv2 ACLs and the ID
  for WAF Classic ACLs. An empty string always means no association,
  regardless of WAF generation.

- NEVER flag `GeoRestriction: none` as INSECURE_TLS or NO_OAC. A missing geo
  restriction is a CONFIG_GAP — defense-in-depth, not an active exposure.
  Conflating it with TLS or origin issues dilutes the severity signal.

- NEVER recommend disabling a distribution as remediation without confirming
  the impact. A disabled distribution serves zero traffic — every dependent
  workload experiences an immediate outage. Always confirm with the operator
  before recommending `Enabled: false`.

- NEVER assume logging is working just because `Logging.Enabled: true`. The
  logging bucket must have an ACL grant to `awslogsdelivery`. A bucket with
  ACLs disabled (BucketOwnerEnforced) silently rejects all CloudFront logs.
  Verify the bucket ACL separately in live-account audits.

- NEVER confuse the default cache behavior with path-specific cache behaviors
  for viewer protocol policy. Only the default behavior drives the verdict —
  it applies to unmatched paths. A path-specific behavior with
  `https-only` does not override a default behavior with `allow-all`.

- NEVER recommend migrating from OAI to OAC without updating the S3 bucket
  policy. OAC requires a different bucket policy statement
  (`Service: cloudfront.amazonaws.com` with the OAC ARN condition) than OAI
  (`CanonicalUser` with the CloudFront canonical ID). Migrating without the
  policy update breaks all object access (403 Forbidden).

- NEVER flag an empty `TrustedKeyGroups` on a public-content distribution.
  Signed URLs are only needed for access-controlled content. Public
  distributions (marketing sites, documentation) intentionally have no
  trusted key groups.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (update-distribution, associate-web-acl, create-origin-access-control),
  the auditor MUST emit:
  `CONFIRM: About to <action> on distribution <id> in account <account>.
  This affects <consequence>. Proceed? (yes/no)`
  Do NOT execute the CLI command until the operator confirms. Distribution
  changes propagate globally — a misconfiguration affects every edge location.
- Confirm the distribution exists and is accessible:
  `aws cloudfront get-distribution-config --id <id> --profile <p>` — fail
  closed (skip remediation) if it returns an error.
- Capture the current distribution config for rollback:
  `aws cloudfront get-distribution-config --id <id> --output json >
  /tmp/<id>-config-backup-$(date +%s).json` BEFORE any modification.
  Distribution configs are versioned via ETag, but there is no automatic
  rollback — the ETag is required for the update call.
- Before changing `MinimumProtocolVersion`, verify that no legacy clients
  require TLS 1.0/1.1. Some embedded devices, legacy POS terminals, or
  older Java runtimes cannot negotiate TLS 1.2+. Coordinate with application
  owners before enforcing TLSv1.2_2021.
- Before creating OAC and updating the origin, prepare the S3 bucket policy
  update simultaneously. OAC without the bucket policy update breaks all
  object access; the bucket policy without OAC is inert.
- Before associating a Web ACL, verify it exists in us-east-1 with
  `CLOUDFRONT` scope: `aws wafv2 list-web-acls --scope CLOUDFRONT --region
  us-east-1`. A Web ACL in any other region cannot be associated.
- **ETag requirement.** Every `update-distribution` call requires the
  current `ETag` from `get-distribution-config`. A stale ETag (config
  changed between read and update) causes `PreconditionFailedException`.
  Always re-fetch the ETag immediately before the update call.
- **Propagation delay.** Distribution changes take 5-60 minutes to propagate
  globally after `update-distribution` returns `DeploymentStatus: Deployed`.
  Do not treat the API response as the effective state — verify via
  `get-distribution` `Status: Deployed` before declaring remediation complete.

## Remediation guidance

**Ordering principle:** TLS findings first (active data-in-transit exposure),
then OAC (origin bypass), then CONFIG_GAP items (defense-in-depth). This
prioritizes by immediate exploitability.

### For INSECURE_TLS — weak TLS minimum protocol (Step 2)

1. Update the distribution config with `MinimumProtocolVersion: TLSv1.2_2021`:
   ```bash
   # Fetch current config + ETag
   aws cloudfront get-distribution-config --id <id> --output json > /tmp/cf-config.json
   ETAG=$(jq -r '.ETag' /tmp/cf-config.json)
   # Edit MinimumProtocolVersion in the config to TLSv1.2_2021
   jq '.DistributionConfig.ViewerCertificate.MinimumProtocolVersion = "TLSv1.2_2021"' \
     /tmp/cf-config.json | jq '.DistributionConfig' > /tmp/cf-updated.json
   aws cloudfront update-distribution --id <id> \
     --if-match "$ETAG" --distribution-config file:///tmp/cf-updated.json
   ```
2. Verify propagation: `aws cloudfront get-distribution --id <id>` until
   `Status: Deployed`.

### For INSECURE_TLS — viewer protocol allow-all (Step 1)

1. Change `ViewerProtocolPolicy` to `redirect-to-https` (or `https-only` for
   strict environments) in the default cache behavior.
2. Use the same update-distribution flow as above.

### For INSECURE_TLS — custom origin http-only (Step 3)

1. Change `OriginProtocolPolicy` to `https-only` on the custom origin.
2. Verify the origin supports HTTPS (has a valid certificate) before the
   change — CloudFront will fail origin connections if the origin does not
   listen on 443.

### For INSECURE_TLS — S3 website endpoint origin (Step 4)

1. Switch the origin `DomainName` from `bucket.s3-website-<region>.amazonaws.com`
   to `bucket.s3.<region>.amazonaws.com` (REST endpoint).
2. Create an OAC and attach it to the origin (see NO_OAC remediation below).
3. Update the S3 bucket policy to use OAC (deny all except CloudFront OAC).
4. Remove public read access from the bucket.

### For NO_OAC — S3 origin without OAC or OAI (Step 5)

1. Create an OAC:
   ```bash
   aws cloudfront create-origin-access-control \
     --origin-access-control-config \
     '{"Name":"oac-for-<bucket>","Description":"OAC for <bucket>","SigningProtocol":"sigv4","SigningBehavior":"always"}' \
     --output json
   OAC_ID=$(jq -r '.OriginAccessControl.Id' /tmp/oac.json)
   ```
2. Attach the OAC ID to the origin in the distribution config
   (`OriginAccessControlId`).
3. Update the S3 bucket policy to allow CloudFront service principal with the
   OAC condition:
   ```json
   {"Principal": {"Service": "cloudfront.amazonaws.com"},
    "Condition": {"StringEquals":
      {"AWS:SourceArn": "arn:aws:cloudfront::<account>:distribution/<id>"}}}
   ```
4. Deploy the distribution and verify object access.

### For CONFIG_GAP — no WAF (Step 6)

1. Create or identify a Web ACL in us-east-1 with `CLOUDFRONT` scope.
2. Associate it:
   ```bash
   aws cloudfront update-distribution --id <id> --if-match "$ETAG" \
     --distribution-config file:///tmp/cf-config-with-waf.json
   ```
   where the config has `WebACLId` set to the Web ACL ARN.

### For CONFIG_GAP — logging disabled (Step 7)

1. Create or identify an S3 bucket for logs.
2. Grant ACL write permission to `awslogsdelivery`:
   ```bash
   aws s3api put-object-acl --bucket <log-bucket> --key cf-logs/ \
     --grant-write 'id="c4c1ede66af53448b93ce283fc5b7c73"' \
     --grant-read-acp 'id="c4c1ede66af53448b93ce283fc5b7c73"'
   ```
   (The canonical ID `c4c1ede66af53448b93ce283fc5b7c73` is the
   `awslogsdelivery` account.)
3. Enable logging in the distribution config (`Logging.Enabled: true`).

### For CONFIG_GAP — no geo restriction (Step 8)

1. Set `Restrictions.GeoRestriction.RestrictionType` to `whitelist` or
   `blacklist` with the appropriate country codes.

### For CONFIG_GAP — legacy OAI without OAC (Step 5)

1. Create an OAC (same as NO_OAC remediation).
2. Set `OriginAccessControlId` on the origin; clear
   `S3OriginConfig.OriginAccessIdentity`.
3. Update the bucket policy from the OAI canonical-user statement to the OAC
   service-principal statement.

### For OK

1. No remediation required for the current posture.
2. Recommend periodic re-audit after any config change.
3. For defense-in-depth, consider adding response headers (Strict-Transport-
   Security, Content-Security-Policy) via CloudFront response-headers policies.

## Recent AWS features (2024-2026)

- **VPC origins (2024-2025):** CloudFront now supports VPC origins, enabling distribution of private content from VPC-attached ALBs, NLBs, EC2 instances, and ECS services without internet exposure. Auditors should check whether distributions using VPC origins have appropriate origin security groups and that the VPC origin is not inadvertently exposed.
- **KeyValueStore (2024):** CloudFront KeyValueStore allows serverless key-value data for CloudFront Functions. This does not change the audit verdict but auditors should note that KVS data is mutable and could be used to inject configuration that bypasses origin checks.
- **Continuous deployment (2024):** CloudFront continuous deployment allows traffic shifting between distribution versions (canary, blue/green). Auditors should verify that the staging distribution has equivalent security configuration (WAF, TLS, OAC) as the primary — a security regression during traffic shifting is a real risk.
- **TLS 1.3 viewer support (2024):** CloudFront now supports TLS 1.3 for viewer connections. Auditors should recommend upgrading the minimum TLS version to TLSv1.2_2021 or TLSv1.3 where applicable.
- **Origin Access Control (OAC) for Lambda and MediaStore (2024-2025):** OAC now supports Lambda Function URLs and MediaStore origins in addition to S3. Auditors should verify OAC coverage on all origin types, not just S3.

## Domain

AWS CloudOps / CloudFront Edge Security & Compliance.
