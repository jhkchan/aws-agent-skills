---
name: route53-health-check-troubleshooter
description: 'Diagnoses Amazon Route 53 health check and DNS failover failures through a ten-category diagnostic tree: endpoint health check failures (HTTP/HTTPS/TCP protocol mismatch, certificate mismatch), calculated health check logic errors (AND/OR/NOT inverted logic, child aggregation), health check interval and failure threshold misconfiguration (consecutive failures, fast/standard interval), DNS failover routing issues (active-active, active-passive, weighted, latency-based, geolocation), health check region selection and caller IP visibility (15+ regions, health checker IPs external to VPC), CloudWatch alarm-based health check threshold ambiguity (alarm period, datapoints, evaluation periods), DNS resolution verification (NS delegation glue records, TTL caching), and hosted zone delegation issues (glue record propagation). Walks symptoms to a verified root cause with evidence-backed probes; emits ROOT_CAUSE_IDENTIFIED or INSUFFICIENT_DATA.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline symptom classification works from pasted health check status and DNS failover behaviour. Live-account diagnosis uses aws route53 get-health-check, get-health-check-status, list-health-checks, get-routing-policy, list-resource-record-sets, aws cloudwatch get-metric-statistics (AWS/Route53 namespace), aws ec2 describe-network-interfaces, and dig/nslookup for DNS resolution verification (AWS CLI v2, SSO or...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Networking
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
  when_to_use: Diagnosing a Route 53 health check failure or DNS failover problem (endpoint health check unhealthy, calculated health check logic error, failover not triggering, wrong record served, health check region mismatch, CloudWatch alarm-based health check ambiguity, DNS resolution or NS delegation failure), walking a symptom to the failed layer with verify and fix commands, validating why traffic is not failing over or why a health check reports unhealthy, or triaging a "DNS failover is broken" page.
  when_not_to_use: Application-level health endpoint debugging (use the application logs and app-specific health check logic), CloudFront origin failover configuration (use CloudFront origin groups), Global Accelerator endpoint health (use Global Accelerator health checks), or VPC route table / peering posture audits (use ec2-security-group-auditor). This skill diagnoses Route 53 health check and DNS failover layer failures; it does not debug the application endpoint code or audit VPC network posture.
  activation_triggers: Route 53 health check unhealthy, Route 53 health check failure, DNS failover not working, Route 53 failover not triggering, DNS failover active-passive, calculated health check AND OR NOT, Route 53 endpoint health check, Route 53 HTTP health check, Route 53 HTTPS health check, Route 53 TCP health check, health check failure threshold, consecutive health check failures, Route 53 health check interval, DNS failover weighted routing, DNS failover latency-based routing, Route 53 geolocation failover, health check regions, Route 53 caller IP, CloudWatch alarm-based health check, DNS resolution NS delegation, hosted zone delegation issue, glue record propagation, troubleshoot Route 53 health check
  invocation_schema: 'Input: either (a) a symptom description (health check status, observed DNS response, failover behaviour, "health check is unhealthy", "secondary endpoint is not receiving traffic", "DNS still resolves to the primary after failover") optionally paired with the health check configuration (get-health-check output, routing policy, record sets), OR (b) a health check ID or hosted zone ID plus DNS context (domain name, record type, routing policy) for live-account diagnosis. Output: a deterministic TARGET/VERDICT/REASON/LAYER/EVIDENCE/REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_IDENTIFIED, INSUFFICIENT_DATA} and LAYER ∈ {ENDPOINT_HEALTH, PROTOCOL_MISMATCH, CERTIFICATE_MISMATCH, CALCULATED_HC_LOGIC, HC_INTERVAL_THRESHOLD, DNS_FAILOVER_ROUTING, DNS_RESOLUTION, NS_DELEGATION, HC_REGION_SELECTION, ALARM_BASED_HC, LATENCY_MEASUREMENT, UNKNOWN}.'
  invocation_example: '# Minimal valid input (offline symptom classification):

    Symptom: "Route 53 health check hc-abc123 reports

    unhealthy. The endpoint at 10.0.1.10:443 is

    reachable from within the VPC via curl. DNS failover

    should redirect to the secondary, but the

    primary record is still being served."

    HealthCheckId: hc-abc123

    Type: HTTPS

    FullyQualifiedDomainName: api.example.com

    IPAddress: 10.0.1.10

    Port: 443

    RequestInterval: 30

    FailureThreshold: 3

    RoutingPolicy: FAILOVER

    HealthCheckStatus: Unhealthy

    DNSResolution: still returns primary IP'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Route 53, health check, DNS failover, endpoint health, HTTP health check, HTTPS health check, TCP health check, calculated health check, AND OR NOT, health check interval, failure threshold, consecutive failures, latency measurement, DNS routing policy, active-active, active-passive, weighted routing, latency-based routing, geolocation routing, health check regions, caller IP, CloudWatch alarm, alarm-based health check, DNS resolution, NS delegation, hosted zone, glue record, troubleshooting
  tags: route53, networking, troubleshooting, dns, health-check, failover, high-availability
---

# Route 53 Health Check Troubleshooter

## Quick Navigation

| Section | Purpose |
|---|---|
| Quick start | Symptom → layer map, core rules |
| Diagnostic decision tree | Step-by-step probes per layer |
| Output format | Strict contract + worked examples |
| Anti-Patterns (NEVER) | Top mistakes to avoid |
| Expert heuristic | Caller IP visibility + threshold math + TTL trade-off |
| Configuration dependency graph | Visual troubleshooting flow |

## Quick start

- **Symptom → layer map (first plausible match drives the first probe):**
  Health check unhealthy but endpoint works → ENDPOINT_HEALTH /
  PROTOCOL_MISMATCH / CERTIFICATE_MISMATCH; calculated health check
  reports wrong status → CALCULATED_HC_LOGIC; failover not triggering
  → DNS_FAILOVER_ROUTING / HC_INTERVAL_THRESHOLD; DNS still returns
  old record after failover → DNS_RESOLUTION (TTL caching); health
  check works in some regions but not others → HC_REGION_SELECTION;
  CloudWatch alarm-based health check flapping → ALARM_BASED_HC;
  domain not resolving at all → NS_DELEGATION.

- **Always verify with a probe, never guess.** Each layer has a single
  command that proves or disproves it. A ROOT_CAUSE_IDENTIFIED verdict
  requires positive evidence — a failing probe matching the symptom.

- **Route 53 health checkers run from 15+ global regions, not from
  your VPC.** An endpoint reachable from inside the VPC via
  `curl localhost:443` may be unreachable from Route 53 health
  checkers because the health checker IPs are external. Always check
  whether the health check uses a public IP, a private IP (requires
  the health checker to route through the VPC), or a domain name.

- **Failure threshold math: `FailureThreshold` consecutive failures
  are required before a health check flips to unhealthy.** With
  `RequestInterval: 30` and `FailureThreshold: 3`, it takes 90
  seconds (3 × 30s) for the health check to become unhealthy after
  the endpoint stops responding. Operators who expect instant
  failover are surprised by this delay.

- **DNS TTL determines failover speed, not the health check interval.**
  Even after the health check flips to unhealthy, clients caching the
  old record for the TTL duration continue sending traffic to the
  failed endpoint. A TTL of 300 seconds means clients may use the old
  record for up to 5 minutes after failover. For fast failover, use
  low TTLs (60 seconds).

- **INSUFFICIENT_DATA for missing context.** If the symptom cannot be
  routed to a failing probe because critical config (health check type,
  routing policy, NS delegation, alarm threshold) is absent, emit
  INSUFFICIENT_DATA and list exactly what is missing.

## Mindset

A failing Route 53 health check or DNS failover is usually a
configuration, network visibility, or threshold-math issue wearing a
"failover is broken" costume. The application endpoint is fine in the
majority of cases; the broken thing is health check type mismatch
(HTTP vs HTTPS), certificate name mismatch, calculated health check
logic error, failure threshold delay, DNS TTL caching, NS delegation,
or health checker IP visibility. Treat the endpoint as innocent until
the health check config, routing policy, DNS delegation, and network
visibility are proven clean.

## Philosophy

The four senior-engineer behaviours (status drives diagnostic order; checker IPs are external and must be allowed inbound; calculated AND/OR inversion; TTL dominates failover speed) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

## Quick reference — symptom triage table

| Symptom phrase / error | Most likely layer | First probe |
|---|---|---|
| Health check unhealthy but endpoint reachable from VPC | ENDPOINT_HEALTH / PROTOCOL_MISMATCH | `get-health-check` type/port/IP; `get-health-check-status` for per-region results |
| HTTPS health check unhealthy, HTTP works | CERTIFICATE_MISMATCH | `get-health-check` EnableSNI, FQDN; cert SAN on the endpoint |
| Calculated health check reports unexpected status | CALCULATED_HC_LOGIC | `get-health-check` Type: CALCULATED, ChildHealthChecks, Inverted |
| Failover not triggering after health check unhealthy | DNS_FAILOVER_ROUTING / HC_INTERVAL_THRESHOLD | Record set routing policy, health check association, FailureThreshold math |
| DNS still returns old record after failover | DNS_RESOLUTION | Record TTL, resolver cache, dig against authoritative servers |
| Health check healthy in some regions, unhealthy in others | HC_REGION_SELECTION | `get-health-check-status` per-region breakdown |
| CloudWatch alarm-based health check flapping | ALARM_BASED_HC | Alarm period, evaluation periods, datapoints to alarm |
| Domain not resolving at all | NS_DELEGATION | `dig NS <domain>` against root and authoritative servers |
| Latency graph shows high latency but health check healthy | LATENCY_MEASUREMENT | Expected, not a failure — latency is informational |
| None of the above | UNKNOWN / INSUFFICIENT_DATA | Gather health check ID, routing policy, NS delegation |

## Pre-flight: health check state and gather-info gate

Gather-info gate commands 1-7 (get-health-check, get-health-check-status, list-health-checks, list-resource-record-sets, CloudWatch HealthCheckPercentageHealthy metrics, describe-alarms, dig NS/A/authoritative) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand before a live-account diagnosis; offline classification uses pasted probe output.

### Health-check-type identification short-circuit

| `Type` | Effect on diagnosis |
|---|---|
| `HTTP` / `HTTPS` | Endpoint check. Health checker sends GET to `FQDN:Port/ResourcePath`. Expects 2xx/3xx by default. |
| `HTTPS` | Certificate validation enabled by default. EnableSNI must match the cert. |
| `TCP` | TCP connect only. No HTTP request. No certificate validation. |
| `CALCULATED` | Boolean logic over child health checks. ChildHealthChecks lists the IDs. Inverted flag flips the result. |
| `CLOUDWATCH_METRIC` | Alarm-based. Monitors a CloudWatch alarm state. HealthStatus = ALARM → unhealthy. |

INSUFFICIENT_DATA re-prompt block for malformed input (missing HealthCheckId or symptom description): [references/error-handling.md](references/error-handling.md).

## Diagnostic decision tree

### Step 0: Non-obvious behaviours that change diagnosis

The 10 non-obvious behaviours (checkers external to the VPC, HTTPS cert vs FQDN validation, consecutive-failure threshold semantics, Inverted flag, TTL caching, 30s/10s interval tiers, per-record health check association, resolver-location routing, ALARM-only alarm-based checks, 48h NS propagation) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand — each behaviour reroutes a diagnosis.

### Step 1: Symptom entry

| Symptom | Branch |
|---|---|
| Health check unhealthy but endpoint works from VPC | Step 2 — Endpoint health |
| HTTPS health check unhealthy, HTTP works | Step 3 — Certificate mismatch |
| Calculated health check unexpected status | Step 4 — Calculated logic |
| Failover not triggering | Step 5 — DNS failover routing |
| DNS still returns old record after failover | Step 6 — DNS resolution / TTL |
| Health check varies by region | Step 7 — Health check regions |
| CloudWatch alarm-based health check flapping | Step 8 — Alarm-based |
| Domain not resolving at all | Step 9 — NS delegation |
| None of the above | Step 10 — INSUFFICIENT_DATA |

### Step 2: Endpoint health — unhealthy but endpoint works from VPC

Probes (get-health-check config fields, get-health-check-status per-region observations): [references/diagnostic-commands.md](references/diagnostic-commands.md).

Diagnostic checks:

| Pattern | Cause |
|---|---|
| Health checker IP not allowed in SG/firewall | Endpoint works from VPC but health checker (external) is blocked. Add Route 53 health checker IP ranges to the inbound SG. |
| `Type: HTTP` but endpoint redirects to HTTPS | Health checker does not follow redirects by default (HTTP 301/302 is treated as failure depending on configuration). Switch to `Type: HTTPS`. |
| `Port: 443` but endpoint listens on 8443 | Port mismatch. Update the health check port. |
| `ResourcePath: /health` but endpoint serves `/healthz` | Path mismatch. The health checker GETs the wrong path and receives 404 (failure). |
| Endpoint returns 200 but health check expects 2xx/3xx only | If the endpoint returns a non-2xx status (e.g., 503 during drain), the health check correctly fails. Verify the endpoint's actual response. |
| Endpoint is on a private IP with no public path | Health checkers are external; they cannot reach private IPs. Use a public ALB/NLB or a Route 53 resolver inbound endpoint. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: ENDPOINT_HEALTH` or
`PROTOCOL_MISMATCH`. Fix: update health check config or SG rules.

### Step 3: Certificate mismatch — HTTPS health check unhealthy

Probes (get-health-check FQDN/EnableSNI/Port, openssl s_client SAN inspection): [references/diagnostic-commands.md](references/diagnostic-commands.md).

| Pattern | Cause |
|---|---|
| Cert SAN does not include the health check FQDN | Certificate name mismatch. Update the cert or change the health check FQDN to match a SAN entry. |
| `EnableSNI: false` on an SNI-based endpoint | Health checker does not send SNI; server returns the default cert (wrong domain). Enable SNI. |
| Self-signed certificate | HTTPS health check validates the cert chain by default. Use a CA-signed cert, or switch to TCP-only health check (no cert validation). |
| Expired certificate | Renew the certificate. Health checker rejects expired certs. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: CERTIFICATE_MISMATCH`.

### Step 4: Calculated health check — unexpected status

Probe (get-health-check Type/ChildHealthChecks/Inverted): [references/diagnostic-commands.md](references/diagnostic-commands.md).

| Pattern | Cause |
|---|---|
| `AND` logic (default), one child unhealthy → calculated unhealthy | Expected behaviour. If failover should tolerate one region down, use `OR` logic (more children). |
| `OR` logic (multiple children), all children unhealthy → calculated unhealthy | Expected. But if only one child is checked, `OR` is equivalent to the child status. |
| `Inverted: true` accidentally set | Calculated health check reports the OPPOSITE of the underlying expression. Remove the inversion. |
| Child health check IDs reference deleted checks | Child checks were deleted; calculated check has no valid children. Update the child list. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: CALCULATED_HC_LOGIC`. Fix:
update child health checks or invert logic.

### Step 5: DNS failover routing — failover not triggering

Probe (list-resource-record-sets routing policy / SetIdentifier / HealthCheckId / TTL for the name): [references/diagnostic-commands.md](references/diagnostic-commands.md).

| Pattern | Cause |
|---|---|
| Record has no `HealthCheckId` | Route 53 has no signal to remove the record. Associate the health check. |
| FAILOVER policy: primary record has `Failover: PRIMARY` but no health check | The primary record is always served. Associate a health check to the primary. |
| FAILOVER policy: secondary has `Failover: SECONDARY` but no health check on primary | Traffic never fails over because primary never reports unhealthy. |
| Weighted policy: no health check on weighted records | All weighted records receive traffic regardless of health. Associate per-record health checks. |
| Latency/geolocation policy: no health check on records | Same — no health check means record is always served. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: DNS_FAILOVER_ROUTING`.

### Step 6: DNS resolution — old record after failover

Probes (dig +noall +answer, dig @authoritative-ns, dig @8.8.8.8): [references/diagnostic-commands.md](references/diagnostic-commands.md).

| Pattern | Cause |
|---|---|
| Authoritative new, public resolver old | TTL caching. Wait for TTL or lower for future failovers. |
| Authoritative old | Route 53 has not updated. Check health check status and routing policy. |
| Both old after > 2× TTL | Health check may not be unhealthy. Verify `get-health-check-status`. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: DNS_RESOLUTION`. Fix: wait
for TTL expiry, or lower TTL for future failovers.

### Step 7: Health check regions — per-region variation

Probe (get-health-check-status per-region Status): [references/diagnostic-commands.md](references/diagnostic-commands.md).

| Pattern | Cause |
|---|---|
| Unhealthy in specific regions only | Network path issue from those regions. Check geographic IP blocks. |
| Flaps across regions | Endpoint intermittently unreachable. Check capacity, rate limiting. |
| All regions unhealthy | Endpoint is down or unreachable from all health checker IPs. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: HC_REGION_SELECTION`.

### Step 8: CloudWatch alarm-based health check

Probes (get-health-check AlarmIdentifier, describe-alarms alarm config): [references/diagnostic-commands.md](references/diagnostic-commands.md).

| Pattern | Cause |
|---|---|
| Alarm `INSUFFICIENT_DATA` | Not enough datapoints. Health check stays healthy. |
| `Period` too long | Slow detection. Shorten the period. |
| `DatapointsToAlarm` > `EvaluationPeriods` | Impossible to alarm. Fix the ratio. |
| Threshold too high/low | Alarm doesn't fire when expected. Adjust. |
| Wrong metric | Alarm evaluates irrelevant metric. Fix. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: ALARM_BASED_HC`.

### Step 9: NS delegation — domain not resolving

Probes (dig NS @8.8.8.8, NS record-set scan, dig +trace): [references/diagnostic-commands.md](references/diagnostic-commands.md).

| Pattern | Cause |
|---|---|
| Parent NS != hosted zone NS | NS delegation mismatch. Update parent zone NS to match hosted zone. |
| Glue records missing | Add glue A records for subdomain NS delegation. |
| NS records recently changed | Propagation can take up to 48 hours. Check `dig NS` at multiple resolvers. |
| Hosted zone not active | Zone may be suspended or domain registration expired. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: NS_DELEGATION`.

### Step 10: INSUFFICIENT_DATA

If critical configuration is missing (health check ID, routing policy,
NS records, alarm config), emit INSUFFICIENT_DATA listing the exact
missing fields and the next probe to run.

## Output format

```text
TARGET: <health-check-id / domain-name / record-set>
VERDICT: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
REASON: <1-2 sentences naming the failed layer and the failing probe>
LAYER: <ENDPOINT_HEALTH | PROTOCOL_MISMATCH | CERTIFICATE_MISMATCH |
        CALCULATED_HC_LOGIC | HC_INTERVAL_THRESHOLD |
        DNS_FAILOVER_ROUTING | DNS_RESOLUTION | NS_DELEGATION |
        HC_REGION_SELECTION | ALARM_BASED_HC | LATENCY_MEASUREMENT |
        UNKNOWN>
EVIDENCE:
  - <observed symptom — health check status / failover behaviour>
  - <failing probe — command and output confirming the cause>
  - <passing probes — layers ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <health-check-id> /
  <zone-id>. Proceed? (yes/no)"
```

### Worked example — Certificate mismatch on HTTPS health check

```text
TARGET: health-check hc-abc123 / api.example.com
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: HTTPS health check FQDN is health.example.com but the endpoint
  serves a certificate with SAN [api.example.com, www.example.com].
  Route 53 health checker validates the TLS certificate against the
  FQDN and rejects the mismatch, reporting unhealthy (Step 3).
LAYER: CERTIFICATE_MISMATCH
EVIDENCE:
  - Symptom: health check hc-abc123 reports unhealthy; endpoint
    reachable via curl -k from within the VPC.
  - Probe: aws route53 get-health-check returns
    FullyQualifiedDomainName: "health.example.com", Type: HTTPS,
    EnableSNI: true.
  - Probe: openssl s_client -connect 10.0.1.10:443 -servername
    health.example.com returns certificate with subject CN=api.example.com,
    SAN=[api.example.com, www.example.com]. "health.example.com" is
    NOT in the SAN list.
  - Passing: HTTP health check on the same endpoint with Type: HTTP
    reports healthy (protocol works, cert is the issue); health
    checker IPs are allowed in the SG (network is not the issue);
    FailureThreshold = 3 consecutive failures (threshold math is
    correct).
REMEDIATION:
  1. Add health.example.com to the certificate SAN:
     aws acm request-certificate --domain-name api.example.com \
       --subject-alternative-names www.example.com,health.example.com
  2. Deploy the new certificate on the endpoint (ALB listener or NLB
     target).
  3. Verify: aws route53 get-health-check-status --health-check-id
     hc-abc123 should report Healthy across all regions within 3
     intervals (90 seconds at RequestInterval 30).
CONFIRM: Before requesting the certificate, emit: "CONFIRM: About to
  request a new ACM certificate with SAN health.example.com. Proceed?
  (yes/no)"
```

### Worked example — Failure threshold math (failover delay)

Full worked example (90s detection + 300s TTL = 390s failover; lowering FailureThreshold/interval/TTL): [references/worked-examples.md](references/worked-examples.md).

### Worked example — INSUFFICIENT_DATA

Full worked example (failover complaint without HealthCheckId/routing policy/TTL/NS context): [references/worked-examples.md](references/worked-examples.md).

## Anti-Patterns — NEVER

- NEVER declare ROOT_CAUSE_IDENTIFIED without a failing probe matching
  the symptom.

- NEVER assume health checkers can reach private IPs. They are external
  to your VPC. Verify public reachability or configure a Route 53
  Resolver inbound endpoint.

- NEVER ignore certificate validation on HTTPS health checks. The FQDN
  MUST match a SAN on the served certificate. EnableSNI must be true
  for SNI-based virtual hosting.

- NEVER set `FailureThreshold` to 1 without understanding the trade-off.
  A threshold of 1 triggers failover on a single transient failure,
  causing flapping.

- NEVER use a high DNS TTL (300+) for records that need fast failover.
  Use 60 seconds or lower for failover-critical records.

- NEVER assume weighted/latency/geolocation records failover
  automatically. Each record must have a `HealthCheckId` association.

- NEVER invert calculated health check logic accidentally. The
  `Inverted` flag flips the result. Test against known child states.

- NEVER trust a single DNS resolver for failover verification. Check
  authoritative servers first, then multiple public resolvers.

- NEVER expect CloudWatch alarm-based health checks to failover on
  `INSUFFICIENT_DATA` state. Only `ALARM` triggers unhealthy.

- NEVER assume latency-based routing serves the nearest endpoint.
  Route 53 evaluates the DNS RESOLVER's latency, not the client's.

- NEVER change NS delegation records without verifying propagation
  across multiple resolvers. NS propagation can take up to 48 hours.

- NEVER conclude "Route 53 is broken" without checking health check
  status, routing policy association, and NS delegation first.

## Pre-flight safety checks

- **MANDATORY CONFIRMATION GATE.** Before `update-health-check`,
  `change-resource-record-sets`, or any state-changing Route 53
  operation, emit and await operator approval.

- **Read-only first.** Every probe is read-only (`get-health-check`,
  `get-health-check-status`, `list-resource-record-sets`,
  `describe-alarms`, `dig`).

- **`update-health-check --failure-threshold 1`** may cause flapping.
  Confirm the operator understands the trade-off.

- **`change-resource-record-sets`** with a lower TTL increases Route 53
  query costs. Confirm the cost impact.

- **Changing NS delegation** can make the domain unreachable if the
  new NS servers are incorrect. Always verify the hosted zone's
  assigned NS servers match before updating the parent zone.

## Expert heuristic

Three heuristics separate a senior Route 53 engineer from a generalist:

The three heuristics in full (caller IP visibility and all-vs-some-regions reading; failure-threshold math with detection + TTL totals; TTL-vs-cost trade-off and pre-warming) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

## Configuration dependency graph

Configuration dependency graph (resolver -> NS delegation -> routing policy -> health check evaluation -> record served, mapped to Steps 2-9) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

## References (load on demand)

- [Advanced patterns](references/advanced-patterns.md) — philosophy, Step 0 non-obvious behaviours, expert heuristics, configuration dependency graph
- [Diagnostic commands](references/diagnostic-commands.md) — gather-info gate commands, per-step probes (Steps 2-9)
- [Error handling](references/error-handling.md) — malformed-input INSUFFICIENT_DATA re-prompt
- [Worked examples](references/worked-examples.md) — failure threshold math, INSUFFICIENT_DATA
- [Health check and failover reference](references/health-check-and-failover-reference.md) — health check types, failover concepts
- [Health checker IP and regions reference](references/health-checker-ip-and-regions-reference.md) — checker IP ranges and regions

## Domain

AWS CloudOps / Networking, Route 53 Health Check Diagnostics, DNS Failover, and Hosted Zone Delegation.

## AWS documentation

- **Route 53 Health Checks and DNS Failover** — https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/dns-failover.html
- **Health check types** — https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/health-checks-types.html
- **Calculated health checks** — https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/health-checks-type-calc.html
- **DNS failover routing policies** — https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-policy.html
- **Health checker IP ranges** — https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/health-checks-ip-addresses.html
- **Configuring DNS failover** — https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/dns-failover-configuring.html
- **Migrating DNS service for an existing domain** — https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/MigratingDNS.html
