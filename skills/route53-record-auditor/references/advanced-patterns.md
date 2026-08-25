# Advanced Patterns — Route 53 Record Auditor

Step 0 expert knowledge, edge-case handling, and recent AWS features moved verbatim from SKILL.md. Loaded on demand.

## Step 0: Expert knowledge — non-obvious Route 53 behaviours

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

## Recent AWS features (2024-2026)

- **DNSSEC improvements (2024):** Route 53 DNSSEC signing now supports more key algorithms and automated key rotation. Auditors should verify that DNSSEC is enabled on all public hosted zones and that KMS keys used for signing have rotation enabled.
- **Application Recovery Controller integration (2024-2025):** Route 53 ARC routing controls integrate with health checks for regional failover. Auditors should verify that ARC routing control health checks are monitored and that failover tested scenarios are documented.
- **Geoproximity and calculator routing policies (2024):** New geoproximity routing with bias settings. No new audit-surface fields, but auditors should verify that geo-based routing policies have health checks on all routed endpoints.
- **CNAME flattening at zone apex:** Enhanced CNAME flattening support. No audit-surface change.
