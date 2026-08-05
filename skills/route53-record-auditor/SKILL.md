---
name: route53-record-auditor
description: >-
  Audits AWS Route 53 record sets for missing health checks on weighted,
  failover, latency, geolocation, and multivalue routing policies; dangling
  ALIAS records pointing to deleted AWS resources (ELB, CloudFront, S3
  website, API Gateway); DNSSEC signing gaps on public hosted zones; public
  hosted-zone exposure of private/internal IP addresses; and TTL
  inconsistency within routing-policy record groups. Emits a deterministic
  verdict (NO_HEALTH_CHECK | DNSSEC_GAP | DANGLING | CONFIG_GAP | OK) per
  record with enumerated findings and specific CLI remediation. Use when
  reviewing Route 53 records, checking for dangling DNS records, validating
  failover or weighted health checks, auditing DNSSEC posture, or hardening
  DNS configuration before production deployment.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline record-set classification.
  Live-account audits use aws route53 list-hosted-zones, list-resource-record-sets,
  get-hosted-zone, get-dnssec, list-health-checks, and aws ec2
  describe-network-interfaces (AWS CLI v2, SSO or key-based credentials).
keywords:
  - Route 53
  - DNS
  - health check
  - failover routing
  - weighted routing
  - latency routing
  - geolocation routing
  - multivalue answer
  - DNSSEC
  - dangling record
  - subdomain takeover
  - ALIAS record
  - public hosted zone
  - TTL consistency
  - record set audit
  - DNS hardening
  - Route 53 misconfiguration
tags: [route53, dns, networking, health-check, dnssec, dangling-record, ttl, audit]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Networking
  verdict_shape: "NO_HEALTH_CHECK | DNSSEC_GAP | DANGLING | CONFIG_GAP | OK"
  when_to_use: >-
    Reviewing Route 53 record sets before production deployment, auditing
    DNS failover health-check coverage, detecting dangling ALIAS records
    pointing to deleted AWS resources, validating DNSSEC signing on public
    hosted zones, checking public-zone exposure of private IPs, or
    hardening DNS configuration across an account.
  activation_triggers:
    - "audit these Route 53 records"
    - "is my DNS failover healthy"
    - "dangling Route 53 record"
    - "missing health check weighted"
    - "DNSSEC not enabled"
    - "public hosted zone exposure"
    - "Route 53 TTL inconsistency"
    - "subdomain takeover risk"
    - "failover PRIMARY no health check"
  invocation_schema: >-
    Input: either (a) one or more Route 53 record sets (list-resource-record-sets
    JSON), optionally paired with hosted-zone metadata (get-dnssec,
    get-hosted-zone), OR (b) a hosted-zone-id for live-account audit.
    Output: deterministic RECORD/VERDICT/REASON/RISK/FINDINGS/REMEDIATION
    block per record, where VERDICT is in {NO_HEALTH_CHECK, DNSSEC_GAP,
    DANGLING, CONFIG_GAP, OK, ERROR}.
---

# Route 53 Record Auditor

## Mindset

**One-line takeaway:** a DNS record set is the last hop before a user reaches
your infrastructure. Every routing-policy record that distributes traffic
without a health check is a promise to route users to a potentially dead
endpoint, and every dangling ALIAS to a deleted AWS resource is either an
immediate outage or a subdomain-takeover vector.

Route 53 record auditing is not just "does the record resolve." It is:
- **Health-check coverage** — failover routing without a health check on the
  PRIMARY record means Route 53 can never detect failure, so it serves the
  dead primary forever. This is the single most dangerous Route 53
  misconfiguration.
- **Dangling ALIAS targets** — an ALIAS to a deleted ELB, CloudFront
  distribution, or S3 website bucket causes NXDOMAIN (outage) or, for S3
  website and API Gateway custom domains, subdomain takeover (another
  account recreates the deleted resource and intercepts traffic).
- **DNSSEC** — a public hosted zone without DNSSEC signing is susceptible to
  cache-poisoning and DNS-spoofing attacks. A zone with signing enabled but
  no DS record at the parent provides no resolver-side validation.
- **Public-zone exposure** — an A record to `10.50.10.20` in a public hosted
  zone discloses internal network topology to anyone who queries the zone.
- **TTL consistency** — mismatched TTLs within a weighted record group cause
  inconsistent caching behaviour across resolvers, breaking load
  distribution assumptions.

## Quick reference — severity thresholds

| Condition | Verdict | Risk | Step |
|---|---|---|---|
| ALIAS to deleted S3 website / API Gateway custom domain | **DANGLING** | **CRITICAL** | 1a |
| ALIAS to deleted ELB / CloudFront / VPC endpoint | **DANGLING** | **HIGH** | 1b |
| Failover PRIMARY, no HealthCheckId | **NO_HEALTH_CHECK** | **CRITICAL** | 2a |
| Weighted (weight > 0), no HealthCheckId | **NO_HEALTH_CHECK** | **HIGH** | 2b |
| Latency routing, no HealthCheckId | **NO_HEALTH_CHECK** | **HIGH** | 2c |
| Geolocation routing, no HealthCheckId | **NO_HEALTH_CHECK** | **MEDIUM** | 2d |
| Multivalue answer, no HealthCheckId | **NO_HEALTH_CHECK** | **MEDIUM** | 2e |
| Public zone, DNSSEC signing disabled | **DNSSEC_GAP** | **HIGH** | 3a |
| Public zone, DNSSEC signed but no DS at parent | **DNSSEC_GAP** | **MEDIUM** | 3b |
| Private IP (RFC 1918/4193) in a public zone | **CONFIG_GAP** | **HIGH** | 4a |
| TTL variance > 2x within routing group | **CONFIG_GAP** | **MEDIUM** | 5a |
| TTL > 3600 on frequently changing records | **CONFIG_GAP** | **LOW** | 5b |
| All checks pass | **OK** | **OK** | 6 |

## Pre-flight: zone and record-set metadata gate

Before evaluating individual record sets, classify the hosted zone. Zone-level
attributes short-circuit several audit dimensions — misclassifying them
produces false positives.

**Pagination note:** `aws route53 list-resource-record-sets` returns up to
300 record sets per call. Use `--start-record-name` and `--start-record-type`
from the prior `NextRecordName` to page through all records. Iterating only
the first page silently skips the tail of the zone — these are the records
most likely to be stale or unmanaged.

| Attribute | Value | Effect on audit |
|---|---|---|
| `Config.PrivateZone: true` | **Private hosted zone.** DNSSEC is N/A (private zones are not publicly resolvable). Public-zone exposure is N/A. Still audit health checks and dangling ALIAS. |
| `Config.PrivateZone: false` | **Public hosted zone.** Full audit — DNSSEC, exposure, health checks, dangling, TTL. |
| `DnssecSigning` absent or key-signing key inactive | **DNSSEC not enabled.** Jump to Step 3a if public zone. |
| `DnssecSigning` present, KSK active | DNSSEC signing is on. Check for DS record at parent (Step 3b). |

**If the record-set JSON is malformed** (missing required fields `Name`,
`Type`, `TTL`), output:

```text
RECORD: <name>
VERDICT: ERROR
REASON: Record set is malformed or missing required fields — cannot classify.
REMEDIATION: Retrieve the canonical record set with
  aws route53 list-resource-record-sets --hosted-zone-id <id> --output json
  and re-audit.
```

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious Route 53 behaviours

These behaviours are easy to misjudge without operational Route 53
experience. Each changes the classification if ignored:

- **ALIAS record TTL is ignored by Route 53.** Route 53 uses the TTL of the
  target resource (ELB, CloudFront, S3). Setting `TTL: 60` on an ALIAS
  record that points to an ELB with a 60-second TTL has no additional
  effect. Do NOT flag ALIAS TTL values — flag the target's TTL only.

- **Failover SECONDARY records do not require a health check by design.**
  Route 53 serves the SECONDARY only when the PRIMARY health check fails.
  Adding a health check to SECONDARY means it also stops serving when the
  secondary endpoint is unhealthy (fail-closed). The recommended pattern
  depends on the SLO: fail-open (no health check on SECONDARY — always
  serve something) vs fail-closed (health check on both — stop serving if
  both are down). Flag SECONDARY-without-health-check as LOW
  (informational), not as NO_HEALTH_CHECK.

- **Weight 0 in a weighted record set is a deliberate drain.** Route 53
  never serves records with `Weight: 0`. It is the standard way to remove
  traffic from an endpoint without deleting the record. A weight-0 record
  does not need a health check — no traffic reaches it. Do NOT flag
  weight-0 records as missing health checks.

- **CNAME at the zone apex is invalid; ALIAS is required.** Route 53
  rejects CNAME records at the apex (`example.com`). Only ALIAS can point
  the apex to an AWS resource. If the input shows a CNAME at the apex,
  this is a configuration error (the record was created through an
  out-of-band tool or API manipulation), not a DNS posture issue — flag
  as CONFIG_GAP.

- **DNSSEC signing without a DS record at the parent zone provides zero
  resolver-side validation.** The DS record at the TLD/registrar is what
  tells resolvers to validate signatures. Without it, Route 53 signs the
  zone, but no upstream resolver checks the signature — cache-poisoning
  protection is not active. This is why Step 3b is a separate finding.

- **Health check type determines failure semantics.** A TCP health check
  passes if the TCP handshake succeeds, even if the endpoint returns HTTP
  500. An HTTP/HTTPS health check can match on a specific response string.
  A health check that tests only TCP connectivity will route traffic to a
  web server returning 500 errors. When auditing health-check coverage,
  note the type alongside presence.

- **DNSSEC key-signing key (KSK) rollover has a DS-record update window.**
  During KSK rollover, the old DS record at the parent must remain until
  resolvers have cached the new one. Premature DS removal causes validation
  failures (SERVFAIL). If `get-dnssec` shows a KSK in `ACTION_COMPLETE` or
  `ACTION_PENDING`, flag as an operational risk — the rollover is in
  progress and the DS record state is transitional.

- **Multi-value answer routing is not load balancing.** Route 53
  randomises up to 8 healthy records per query. It does not track response
  times, connection counts, or geographic proximity. Without health
  checks, it serves potentially dead IPs. Treat multivalue-answer without
  health checks as MEDIUM (lower than failover PRIMARY, because the
  randomisation naturally reduces traffic to a dead IP — but does not
  eliminate it).

- **Geolocation routing with a default record.** A geolocation record set
  should include a `Geolocation: Continent: *` or a wildcard default
  record to catch unrecognised regions. Without a default, queries from
  unmapped regions receive NXDOMAIN. Flag the absence of a default
  geolocation record as CONFIG_GAP.

- **Alias to a CloudFront distribution requires same-account ownership.**
  Route 53 validates that the distribution belongs to the same AWS
  account as the hosted zone. Cross-account ALIAS to CloudFront is not
  supported — the record silently fails. If the input shows a cross-account
  CloudFront ALIAS, flag as CONFIG_GAP.

- **Private hosted zones associated with VPCs.** A private hosted zone
  must be associated with at least one VPC to resolve. If the input shows
  a private zone with no VPC associations, flag as CONFIG_GAP — records in
  the zone are unreachable.

### Step 1: Dangling ALIAS target detection (highest priority — outage or takeover)

For each record with `AliasTarget`, verify the target resource exists. The
detection method depends on the target type:

- **ALIAS to S3 website endpoint** (`*.s3-website-*.amazonaws.com`): if the
  bucket has been deleted or website hosting disabled, the DNS name
  returns NXDOMAIN. Another AWS account can recreate a bucket with the same
  name and re-enable website hosting — **subdomain takeover**. This is
  **DANGLING**, RISK: **CRITICAL** (Step 1a).

- **ALIAS to API Gateway custom domain** (`*.execute-api.*.amazonaws.com`):
  if the custom domain or API mapping has been deleted, the endpoint
  returns NXDOMAIN. Another account can claim the same custom domain in
  some configurations. **DANGLING**, RISK: **CRITICAL** (Step 1a).

- **ALIAS to ELB / ALB / NLB** (`*.elb.amazonaws.com`): if the load
  balancer has been deleted, the DNS name does not resolve. ELB DNS names
  include a random suffix, making direct takeover unlikely, but the record
  causes NXDOMAIN (immediate outage). **DANGLING**, RISK: **HIGH** (Step 1b).

- **ALIAS to CloudFront** (`*.cloudfront.net`): if the distribution has
  been deleted, the DNS name returns NXDOMAIN. Distribution IDs are
  globally unique, so takeover is not possible. **DANGLING**, RISK: **HIGH**
  (Step 1b).

- **ALIAS to VPC interface endpoint** (`*.execute-api.*.amazonaws.com` or
  service-specific): if the endpoint has been deleted, the private DNS
  name does not resolve. **DANGLING**, RISK: **HIGH** (Step 1b).

Detection signal: `AliasTarget.DNSName` that does not resolve when queried
(or the `EvaluateTargetHealth: true` flag combined with an unreachable
target). For offline audits, the operator provides the resolution status.

### Step 2: Health check on routing-policy records

For records with a routing policy (`Weighted`, `Failover`, `Latency`,
`GeoLocation`, `MultiValueAnswer`), check for `HealthCheckId`:

- **Failover PRIMARY, no `HealthCheckId`** → **NO_HEALTH_CHECK**, RISK:
  **CRITICAL** (Step 2a). Without a health check, Route 53 has no signal
  to fail over — the PRIMARY is always considered healthy. A failover
  configuration with a health-check-less PRIMARY is functionally
  indistinguishable from no failover at all.

- **Weighted, `Weight > 0`, no `HealthCheckId`** → **NO_HEALTH_CHECK**,
  RISK: **HIGH** (Step 2b). Route 53 distributes the weight proportionally
  even if the endpoint is dead — dead endpoints receive their full share
  of traffic.

- **Latency routing, no `HealthCheckId`** → **NO_HEALTH_CHECK**, RISK:
  **HIGH** (Step 2c). Users are routed to the lowest-latency region even
  if that region's endpoint is down.

- **Geolocation routing, no `HealthCheckId`** → **NO_HEALTH_CHECK**,
  RISK: **MEDIUM** (Step 2d). Users from a mapped region are always routed
  to that region's endpoint.

- **Multivalue answer, no `HealthCheckId`** → **NO_HEALTH_CHECK**,
  RISK: **MEDIUM** (Step 2e). Route 53 randomises across all records,
  including dead ones (reduced but not eliminated traffic to dead IPs).

- **Weighted, `Weight: 0`, no `HealthCheckId`** → **no finding**. Weight 0
  is a deliberate drain — no traffic reaches this record.

- **Failover SECONDARY, no `HealthCheckId`** → **no finding** (informational
  note only). The secondary is served when the primary fails. A health
  check on SECONDARY is recommended for fail-closed behaviour but not
  required for basic failover.

### Step 3: DNSSEC signing gap (public hosted zones only)

Evaluate DNSSEC only for **public** hosted zones (`Config.PrivateZone: false`):

- **No active key-signing key (KSK) or zone-signing key (ZSK)** →
  **DNSSEC_GAP**, RISK: **HIGH** (Step 3a). The zone is susceptible to
  cache-poisoning. Enable DNSSEC signing, create a KSK, and publish the DS
  record at the parent zone (registrar/TLD).

- **KSK active but no DS record at the parent zone** → **DNSSEC_GAP**,
  RISK: **MEDIUM** (Step 3b). Route 53 signs the zone, but resolvers cannot
  validate signatures without the DS chain. Verify the DS record is
  published by querying the parent zone or checking the registrar.

- **Private hosted zone** → skip DNSSEC evaluation entirely. DNSSEC is
  irrelevant for private DNS — private zones are resolved only within
  associated VPCs, not by public recursive resolvers.

### Step 4: Public hosted-zone exposure

For records in **public** hosted zones, check for private/internal targets:

- **A/AAAA record pointing to RFC 1918 private IP** (`10.0.0.0/8`,
  `172.16.0.0/12`, `192.168.0.0/16`) or ULA (`fc00::/7`) → **CONFIG_GAP**,
  RISK: **HIGH** (Step 4a). Internal network topology is disclosed to
  anyone who queries the zone publicly. While not directly exploitable
  (the IPs are not routable from the internet), the information leak aids
  reconnaissance.

- **CNAME to an internal hostname** (e.g., `db.internal.corp`) →
  **CONFIG_GAP**, RISK: **MEDIUM**. Leaks internal naming conventions.

- **Private hosted zone** → skip exposure evaluation. Private zones are
  not publicly queryable.

### Step 5: TTL consistency

For records grouped under the same routing policy (same `Name` + `Type`,
different `SetIdentifier`):

- **TTL variance > 2x within a routing group** → **CONFIG_GAP**, RISK:
  **MEDIUM** (Step 5a). Resolvers cache the records for different durations,
  breaking the traffic-distribution assumptions. Example: a weighted group
  with TTL 60 and TTL 3600 means one endpoint is cached 60x longer.

- **TTL > 3600 on records whose values change frequently** (A records to
  ELB/autoscaling, weighted records during canary deploys) → **CONFIG_GAP**,
  RISK: **LOW** (Step 5b). Stale cache delays propagation of value changes.

- **ALIAS records** → do NOT flag TTL. Route 53 ignores the ALIAS TTL and
  uses the target's TTL (Step 0 expert knowledge).

### Step 6: Aggregation — worst finding wins

The final verdict is the category of the **highest-risk finding** across all
steps. When two findings have the same risk level, use category priority:
**DANGLING > NO_HEALTH_CHECK > DNSSEC_GAP > CONFIG_GAP**.

If no findings are produced (all checks pass), the verdict is **OK**.

## Output format (per record set)

```text
RECORD: <name> (<type>, <routing-policy>)
VERDICT: NO_HEALTH_CHECK | DNSSEC_GAP | DANGLING | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and step number>
RISK: CRITICAL | HIGH | MEDIUM | LOW | OK
FINDINGS:
  - [CRITICAL] <finding description (Step Na)>
  - [HIGH] <finding description (Step Nb)>
  - [OK] <dimension that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — failover PRIMARY without health check

```text
RECORD: api.example.com (A, failover)
VERDICT: NO_HEALTH_CHECK
REASON: Failover PRIMARY record has no HealthCheckId — Route 53 cannot
detect primary failure and will never serve the secondary (Step 2a).
RISK: CRITICAL
FINDINGS:
  - [CRITICAL] Failover PRIMARY with no HealthCheckId (Step 2a) — failover
    is functionally disabled; traffic goes to dead primary forever
  - [OK] DNSSEC signing is enabled on the public hosted zone (Step 3)
  - [OK] No dangling ALIAS detected (Step 1)
REMEDIATION:
  1. Create or attach a health check:
     aws route53 create-health-check --caller-reference <ref>
     --health-check-config Type=HTTPS,FullyQualifiedDomainName=api.example.com
     ,ResourcePath=/health,RequestInterval=30,FailureThreshold=3
  2. Associate the health check:
     aws route53 change-resource-record-sets --hosted-zone-id <id>
     --change-batch file://update-record.json  (add HealthCheckId)
```

## Edge-case handling

- **Multiple routing policies on one record.** A record can only have ONE
  routing policy. If the input shows conflicting policies (e.g., both
  `Weighted` and `Failover` on the same record), flag as ERROR — Route 53
  rejects this at the API level.

- **Health check deleted but still referenced.** If `HealthCheckId` is set
  but the health check was deleted, Route 53 treats the record as always
  healthy (no health-check signal). Flag as CONFIG_GAP — the health-check
  reference is stale.

- **Records in a zone with no DNSSEC metadata.** If `get-dnssec` returns
  an empty `KeySigningKeys` array, treat as "DNSSEC not enabled" (Step 3a).

- **CloudFront ALIAS with `EvaluateTargetHealth: false`.** When
  `EvaluateTargetHealth` is false on an ALIAS, Route 53 does not check the
  target's health. For failover configurations using ALIAS, this defeats
  the purpose — flag as CONFIG_GAP in addition to the health-check finding.

## Anti-Patterns — NEVER

- NEVER flag missing health checks on **simple-routing** records (`Type:
  A/AAAA/CNAME` with no routing policy). Simple routing has a single
  target — there is nothing to fail over to. Health checks are optional
  and add cost without routing benefit.

- NEVER require a health check on a **failover SECONDARY** record. The
  secondary is served when the primary health check fails. A health check
  on the secondary changes the behaviour from fail-open to fail-closed —
  both are valid patterns depending on the SLO. Flag as informational,
  not as NO_HEALTH_CHECK.

- NEVER flag a **weight-0** weighted record for missing health checks.
  Weight 0 means no traffic reaches this endpoint — it is a deliberate
  drain. A health check is irrelevant when no traffic is served.

- NEVER flag **DNSSEC** on a **private hosted zone**. DNSSEC is irrelevant
  for private DNS — the zone is not publicly resolvable, so there is no
  cache-poisoning surface. Flagging it is a false positive.

- NEVER flag **ALIAS TTL** as inconsistent. Route 53 ignores the TTL on
  ALIAS records and uses the target resource's TTL. The ALIAS TTL field
  exists in the API but has no runtime effect.

- NEVER recommend **CNAME** at the zone apex. Route 53 rejects CNAME at
  the apex — always use ALIAS. If a CNAME-at-apex is detected, recommend
  converting to ALIAS.

- NEVER confuse **DNS resolution failure** with a dangling alias. An ALIAS
  to an ELB may temporarily fail to resolve during a deployment or
  configuration change. Confirm the target resource is deleted (not just
  temporarily unreachable) before flagging as DANGLING. Use
  `aws elbv2 describe-load-balancers --query
  'LoadBalancers[?DNSName==`<dns>`]'` to verify existence.

- NEVER recommend deleting a dangling record without first confirming the
  target resource is truly gone. Cross-region or cross-account resources
  may still exist. Deleting the record before confirming the target is
  permanently removed can mask a configuration issue.

- NEVER flag a **private hosted zone** for public-zone exposure. Private
  zones are only resolvable from associated VPCs — a private IP in a
  private zone is correct and expected.

- NEVER assume **DNSSEC signing is active** just because a KSK exists.
  The KSK must be in `ACTIVE` key state. A KSK in `INACTIVE` or
  `ACTION_PENDING` means signing is not yet effective. Check
  `KeySigningKeyTMPL.Status` in the `get-dnssec` output.

- NEVER flag **multivalue answer** records as equivalent to failover.
  Multivalue answer is randomised distribution, not failover. A dead IP in
  a multivalue set still receives some traffic — but the severity is MEDIUM
  (reduced traffic), not CRITICAL (all traffic).

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`change-resource-record-sets`, `delete-health-check`,
  `enable-hosted-zone-dnssec`), the auditor MUST emit:
  `CONFIRM: About to <action> on record <name> in zone <id>. This affects
  DNS resolution for <domain>. Proceed? (yes/no)`
  Do NOT execute the CLI command until the operator confirms. DNS changes
  propagate globally and cannot be instantaneously rolled back.

- **Capture current state for rollback:**
  `aws route53 list-resource-record-sets --hosted-zone-id <id> --output json
  > /tmp/<zone-id>-records-backup-$(date +%s).json`
  BEFORE any record change. Route 53 does not version record sets — there
  is no undo without a backup.

- **Verify the health check exists before associating:**
  `aws route53 get-health-check --health-check-id <id>`. A stale or
  deleted health-check ID silently disables the health-check signal.

- **For DNSSEC enablement:** verify the parent zone supports DNSSEC and
  obtain the DS record from the Route 53 console (`get-dnssec` returns the
  DS record value to publish at the registrar). Enabling DNSSEC without
  publishing the DS record provides no resolver validation (Step 3b).

- **For dangling-record remediation:** confirm the target resource is
  deleted before removing the record. If the target still exists (cross-
  region, different account), the record is not dangling — investigate the
  DNS resolution path instead.

- **Prefer UPSERT over CREATE/DELETE** in change-resource-record-sets
  batches. UPSERT is idempotent — it creates if absent and updates if
  present, reducing the risk of duplicate records or accidental deletion.

## Remediation guidance

### For DANGLING — deleted ALIAS target (Step 1)

1. **Verify** the target resource is deleted:
   - ELB: `aws elbv2 describe-load-balancers --query 'LoadBalancers[?DNSName==\`<dns>\`]'`
   - CloudFront: `aws cloudfront list-distributions --query
     'DistributionList.Items[?DomainName==\`<dns>\`]'`
   - S3: `aws s3api get-bucket-website --bucket <name>` (NXDOMAIN if deleted)
2. If the target is confirmed deleted, **delete or update the record**:
   `aws route53 change-resource-record-sets --hosted-zone-id <id>
   --change-batch file://delete-record.json`
3. If the target was S3 website or API Gateway custom domain and the record
   was in a public zone, **assume potential takeover** during the exposure
   window. Audit for unauthorised requests to the domain.
4. If the target still exists in another region/account, update the ALIAS
   to the correct DNS name or remove the record if it is no longer needed.

### For NO_HEALTH_CHECK — failover PRIMARY (Step 2a)

1. **Create a health check** that tests the primary endpoint:
   ```bash
   aws route53 create-health-check --caller-reference hc-$(date +%s) \
     --health-check-config '{"Type":"HTTPS","FullyQualifiedDomainName":"api.example.com","ResourcePath":"/health","RequestInterval":30,"FailureThreshold":3,"MeasureLatency":true}'
   ```
2. **Associate** the HealthCheckId with the failover PRIMARY record using
   a change-resource-record-sets UPSERT batch.
3. **Verify** the health check is passing:
   `aws route53 get-health-check-status --health-check-id <id>`
4. **Test failover** by stopping the primary endpoint and confirming Route
   53 serves the secondary within the health-check interval (30s default +
   FailureThreshold).

### For NO_HEALTH_CHECK — weighted / latency (Step 2b/2c)

1. Create health checks for each endpoint in the group.
2. Associate HealthCheckId with each record that has `Weight > 0`.
3. Set `EvaluateTargetHealth: true` on ALIAS records within the group so
   Route 53 also considers the target's own health.

### For DNSSEC_GAP — signing disabled (Step 3a)

1. Enable DNSSEC signing:
   ```bash
   aws route53 enable-hosted-zone-dnssec --hosted-zone-id <id>
   aws route53 create-key-signing-key --hosted-zone-id <id> \
     --key-management-service-arn <kms-key-arn> \
     --name <ksk-name> --status ACTIVE
   ```
2. **Publish the DS record** at the parent zone (registrar/TLD). The DS
   value is returned by `aws route53 get-dnssec --hosted-zone-id <id>`.
3. Verify resolver validation with `dig +dnssec <domain>` from an external
   resolver.

### For DNSSEC_GAP — DS record not published (Step 3b)

1. Retrieve the DS record:
   `aws route53 get-dnssec --hosted-zone-id <id>` — copy the `DS` value.
2. Publish it at the domain's registrar (Route 53 registered domains:
   `aws route53domains associate-delegation-signer`).
3. Verify propagation: `dig DS <domain> +short` at the parent TLD.

### For CONFIG_GAP — private IP in public zone (Step 4a)

1. Move the record to a **private hosted zone** associated with the VPC,
   or replace the private IP with the public-facing endpoint (ELB/ALB/CDN).
2. If the record must remain public (e.g., for split-horizon DNS), use a
   separate private zone for internal resolution and keep only public IPs
   in the public zone.

### For CONFIG_GAP — TTL inconsistency (Step 5a)

1. Align all records in the same routing group to the same TTL.
2. Recommended TTLs: 60 for failover/weighted with frequent changes,
   300 for latency/geolocation, 3600 for stable simple-routing records.

### For OK

1. No remediation required for the current posture.
2. Recommend periodic re-audit after infrastructure changes (new load
   balancers, deleted resources, new routing policies).
3. For public zones, verify the DS record remains published after any KSK
   rollover.

## Recent AWS features (2024-2026)

- **DNSSEC improvements (2024):** Route 53 DNSSEC signing now supports more key algorithms and automated key rotation. Auditors should verify that DNSSEC is enabled on all public hosted zones and that KMS keys used for signing have rotation enabled.
- **Application Recovery Controller integration (2024-2025):** Route 53 ARC routing controls integrate with health checks for regional failover. Auditors should verify that ARC routing control health checks are monitored and that failover tested scenarios are documented.
- **Geoproximity and calculator routing policies (2024):** New geoproximity routing with bias settings. No new audit-surface fields, but auditors should verify that geo-based routing policies have health checks on all routed endpoints.
- **CNAME flattening at zone apex:** Enhanced CNAME flattening support. No audit-surface change.

## Domain

AWS CloudOps / Route 53 DNS Security & Reliability.
