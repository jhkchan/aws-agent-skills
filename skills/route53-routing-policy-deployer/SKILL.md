---
name: route53-routing-policy-deployer
description: 'Provisions Route 53 routing policies and dependent primitives with production defaults: simple, weighted (canary), latency, failover (primary/secondary with health checks), geolocation (continent/ country/subdivision), geoproximity (bias), multivalue answer (round-robin with HCs), IP-based (CIDR), alias records (ALB, CloudFront, API Gateway, S3 website, VPC interface endpoint) with EvaluateTargetHealth, health checks (endpoint, string match, inverted, calculated), traffic policies (versioned), and Route 53 Application Recovery Controller (routing control + readiness check + safety rule). Emits READY_TO_DEPLOY / PREREQUISITES_MISSING with every record and HC verified and copy-pasteable route53 / route53-recovery-cluster commands. Use when provisioning DNS routing for multi-region, canary, geolocation, DR failover, or aliasing to an AWS service. Triggers: Route 53, routing policy, weighted, latency, failover, geolocation, health check, alias, traffic policy.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Live provisioning uses AWS CLI v2 with route53 (change-resource-record-sets, create-health-check, create-traffic- policy, test-dns-answer), route53domains, and route53-recovery-cluster config (create-routing-control, create-readiness-check) for Application Recovery Controller. Works with Terraform aws_route53_record / aws_route53_health_check and CloudFormation AWS::Route53::* resources.
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Networking
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  when_to_use: Provisioning a Route 53 routing policy (simple, weighted, latency, failover, geolocation, geoproximity, multivalue answer, IP-based), creating an alias record to an AWS service (ALB, CloudFront, API Gateway, S3 website, VPC interface endpoint), configuring a health check (endpoint, string matching, inverted, calculated), versioning a traffic policy, or setting up Route 53 Application Recovery Controller (routing control + readiness check). Do NOT invoke for emergency failover execution (use route53-failover-operator), or for non-Route-53 DNS providers.
  activation_triggers: Route 53 routing policy, weighted routing, latency routing, failover routing, geolocation routing, geoproximity routing, multivalue answer routing, IP-based routing, CIDR routing, alias record to ALB, alias record to CloudFront, Route 53 health check, Route 53 traffic policy, Application Recovery Controller, routing control, readiness check
  invocation_schema: 'Input: either (a) a hosted zone ID + record name + routing policy type + target value(s), or (b) an alias-record spec (AWS resource + record name), or (c) an Application Recovery Controller spec (control tower + routing controls + readiness checks). Output: deterministic RECORD_SET / VERDICT / CHECKLIST / VERIFICATION_COMMANDS block per the STRICT output contract, where VERDICT is READY_TO_DEPLOY or PREREQUISITES_MISSING.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: aws, route53, dns, routing-policy, weighted, latency, failover, geolocation, geoproximity, multivalue-answer, ip-based-routing, alias-record, health-check, traffic-policy, application-recovery-controller, routing-control, readiness-check, cloudops, deploy
  tags: aws, route53, dns, routing-policy, health-check, failover, deploy, networking
  dependencies: aws-orchestrator
---

# Route 53 Routing Policy Deployer

## What this skill does

Provisions Route 53 routing policies, alias records, health checks,
traffic policies, and Application Recovery Controller primitives with
correct defaults. The skill walks an 8-step procedure, surfaces the
silent-failure modes unique to Route 53 (most dangerous: weighted
routing with no health checks silently sends traffic to dead targets,
and failover records without `EvaluateTargetHealth` silently fail
closed to the secondary even when the primary recovers), and emits a
READY_TO_DEPLOY checklist verifying every record and health check
against actual state. The single most common incident this skill
prevents: an operator configures weighted routing across two targets
with weights 90/10, but the 10% target is down and there is no health
check — 10% of traffic returns SERVFAIL for the whole TTL window,
repeatedly, with no alarm.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **Quick reference** | Provisioning summary (8 steps), verdict thresholds, policy matrix | Before any operation |
| **Activation keywords** | Phrases that route to this skill | Disambiguating routing |
| **Invocation contract** | Required literal labels in the response | Formatting the response |
| **Reasoning framework** | Why the 8-step order matters; effective-permission model | Understanding the deploy model |
| **Dependency graph** | Which configs silently no-op without their prerequisite | Debugging "policy doesn't take effect" |
| **Expert heuristic** | Weighted-no-health-check myth; TTL trade-offs; ARC safety | Pre-empt production incidents |
| **Prerequisites** | What to verify before emitting any command | Avoid PREREQUISITES_MISSING rework |
| **8-step procedure** | The actual provisioning with copy-pasteable CLI | Executing the deploy |
| **NEVER (top 5)** | Hard rules that prevent silent exposure / data-plane bugs | Review before deploy |
| **STRICT output contract** | Required RECORD_SET / VERDICT / CHECKLIST / VERIFICATION_COMMANDS block | Formatting the response |
| **Recent AWS features** | CIDR routing, ARC improvements, traffic-policy versioning | Stay current |

## Quick reference — provisioning summary (8 steps)

| Step | Action | Reversible? | Key risk if skipped |
|---|---|---|---|
| 1 | Confirm hosted zone + name + record type | — | wrong zone = silent wrong namespace |
| 2 | Choose routing policy (8 types + alias) | Yes | wrong policy = wrong traffic shape |
| 3 | Resolve target value(s) / alias targets | Yes | wrong target = misrouted traffic |
| 4 | Configure health checks (per target where required) | Yes | no HC = traffic to dead targets |
| 5 | Build the change-batch POST (atomic) | — | non-atomic changes race |
| 6 | (Optional) Traffic policy / ARC routing control | Yes | see per-feature silent failures |
| 7 | Apply TTL appropriate to the policy | Yes | 300s on weighted = slow canary |
| 8 | Verify via `test-dns-answer` + `get-health-check-status` + emit checklist | — | silent no-ops |

**Critical ordering constraints:** hosted zone + name confirmed before
target resolution (wrong zone is silent); routing policy chosen before
health checks (the policy dictates whether HC is mandatory); health
checks provisioned before the record references them (a record
referencing a non-existent HC ID is a silent no-op on
`EvaluateTargetHealth`); change-batch posted atomically (sequential
POSTs produce partial states); TTL applied deliberately per policy
(60s for failover, 300s for stable simple, 60s for weighted canary).
Rationale and the silent-failure table are below.

## Activation keywords

Route 53 routing policy, weighted routing, latency routing, failover
routing, geolocation routing, geoproximity routing, multivalue answer
routing, IP-based routing, CIDR routing, alias record, alias to ALB,
alias to CloudFront, alias to API Gateway, alias to S3 website, alias
to VPC interface endpoint, Route 53 health check, health check string
matching, calculated health check, inverted health check, Route 53
traffic policy, traffic policy version, Application Recovery
Controller, routing control, readiness check, Route 53 ARC.

## Invocation contract (hard requirement)

When this skill is invoked with a routing-policy provisioning request,
the agent MUST respond with the checklist defined in §"STRICT output
contract" using the literal all-caps labels `RECORD_SET:`, `VERDICT:`,
`CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels
breaks automation silently.

## Reasoning framework (why the provisioning order matters)

Route 53 looks like "create a record, point it at an IP" but the
underlying model has four traps:

1. **Each routing policy is a different API shape, not a flag.** The
   `RoutingPolicy` field on a record set is one of `simple`,
   `weighted`, `latency`, `failover`, `geolocation`, `geoproximity`,
   `multivalue answer`, `ipbased`. The chosen policy dictates which
   other fields are required (`SetIdentifier`, `Region`, `GeoLocation`,
   `TTL`, `TrafficConfigMappings`). Picking the policy first is not
   stylistic; it determines the schema.

2. **Health checks are mandatory for failover, optional but critical
   for weighted/latency/multivalue.** A weighted record without a
   health check sends its allotted percentage of traffic to the target
   even when the target is down. The DNS resolver returns the dead
   target's IP; the client gets a connection timeout. There is no
   automatic failover at the DNS layer without HC + the policy that
   consumes it.

3. **Alias records are NOT a record type; they are a value shape.**
   An alias to an ALB uses `AliasTarget.DNSName = <alb-dns-name>` and
   `AliasTarget.EvaluateTargetHealth = true`. The record's `Type` is
   `A` (or `AAAA`), NOT `CNAME` and NOT `ALIAS`. Operators who try
   `Type: CNAME` with an alias target get a schema error.

4. **`EvaluateTargetHealth` is the silent-failure multiplier.** When
   true, Route 53 considers the alias target's health when answering.
   When false (the default), Route 53 returns the target IP even if
   the target is down. For alias records pointing at ELB / CloudFront,
   `EvaluateTargetHealth: true` is almost always what you want; the
   exception is a target that does not expose health to Route 53 (some
   VPC interface endpoints), where the flag is silently ignored.

The procedure below sequences the steps to surface these traps.

## Dependency graph (silent-failure table)

| Configuration | Hard dependencies (API error without) | Silent failure mode (returns 200, does nothing) | Enables downstream |
|---|---|---|---|
| Simple routing | hosted zone, record name | wrong zone ID silently posts to a different namespace | baseline resolution |
| Weighted routing | `SetIdentifier` per record; >= 2 records in the set | **weights 100/0 to a down target with no HC = 100% to dead target for whole TTL window** | canary, percentage split |
| Latency routing | `Region` per record; >= 2 records in the set | **single-region latency record silently behaves like simple (no alternative to route to)** | multi-region active-active |
| Failover routing | `Failover` per record (PRIMARY/SECONDARY); HC on PRIMARY | **SECONDARY used indefinitely if `EvaluateTargetHealth` is false on the PRIMARY alias — no auto-failback** | DR primary/secondary |
| Geolocation routing | `GeoLocation` per record; default record recommended | **no default + no matching geo = NXDOMAIN to client, no alarm** | geo compliance, geo routing |
| Geoproximity routing | `GeoProximityLocation` per record; bias -99..99 | **bias 0 = no effect, silent; bias outside ±99 rejected** | fine-grained geo tuning |
| Multivalue answer | `MultiValueAnswer` config; HC per value recommended | **without HC, dead IPs returned in round-robin rotation** | round-robin with failover |
| IP-based routing | `CidrRoutingConfig` per record; CIDR block list | **overlapping CIDRs evaluated in document order, first match wins — wrong order = wrong routing** | EDNS-client-subnet routing |
| Alias record | target AWS resource exists; correct alias DNS name | **`Type: CNAME` with `AliasTarget` = API error; `EvaluateTargetHealth: false` on ALB = no HC effect** | apex domains, AWS service aliasing |
| Health check | endpoint reachable from Route 53 checkers (multi-region) | **endpoint behind private VPC = HC always unhealthy; no signal until CloudWatch alarm fires** | policy-driven failover |
| Calculated health check | >= 2 child health checks | **AND of children when one child is inverted = inverted logic bug** | aggregated DR decision |
| Traffic policy | policy document JSON; version increments | **traffic policy instance not updated to new version = old routing persists silently** | versioned routing-as-code |
| Routing control (ARC) | control panel in cluster; safety rules | **routing control flip without safety rule = total outage if both sides flipped off** | sub-second DR cutover |
| Readiness check (ARC) | resource set + check type per resource | **readiness check blocks cutover if any resource NOT ready — silent until you try to flip** | ARC pre-cutover gate |

**The four most dangerous silent-failure rows** are weighted-no-HC,
failover-`EvaluateTargetHealth`-false, geolocation-no-default, and
routing-control-no-safety-rule. All return success on apply; the
failure surfaces only when traffic doesn't behave as expected. Step 4
(HC) and Step 8 (`test-dns-answer` + `get-health-check-status`) are
non-negotiable for any non-simple policy.

## Expert heuristic: the weighted-without-health-check myth

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Expert heuristic: the weighted-without-health-check myth".
> Load when: reasoning about weighted/latency/multivalue/geoproximity without health checks

## Expert heuristic: TTL and routing-policy interaction

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Expert heuristic: TTL and routing-policy interaction".
> Load when: choosing the TTL for a policy (Step 7)

## Expert heuristic: Application Recovery Controller safety rules

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Expert heuristic: Application Recovery Controller safety rules".
> Load when: planning any ARC routing-control deployment (safety rule, readiness check, alarms)

## Prerequisites (verify before provisioning)

Before emitting any provisioning command, verify these prerequisites.
If any are missing, the verdict is **PREREQUISITES_MISSING** with a
specific gap citation.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Hosted zone exists | Record sets live in a zone; wrong zone = silent wrong namespace | `aws route53 list-hosted-zones-by-name --dns-name <domain>` |
| Caller IAM | `route53:ChangeResourceRecordSets` required to post | `aws sts get-caller-identity` + IAM policy check |
| Record name within zone | Name must be a subdomain of (or apex of) the zone | `aws route53 get-hosted-zone --id <id>` |
| Target resource exists (alias) | Alias target must be resolvable and in same account (or in-region partition) | depends on target (ELB `describe-load-balancers`, CloudFront `list-distributions`) |
| Health check exists (if referenced) | Record referencing a non-existent HC ID is a silent no-op on `EvaluateTargetHealth` | `aws route53 get-health-check --health-check-id <id>` |
| Cross-account hosted zone | If zone is in another account, the caller needs a `route53:ChangeResourceRecordSets` grant on the zone ARN | `aws route53 list-resource-record-sets --hosted-zone-id <id>` |
| ARC cluster (ARC only) | Routing controls live in a cluster; cluster must exist first | `aws route53-recovery-cluster list-routing-controls --control-panel-arn <arn>` |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## 8-step provisioning procedure

### Step 1 — Confirm hosted zone + name + record type

```bash
aws route53 list-hosted-zones-by-name --dns-name <DOMAIN> \
  --query 'HostedZones[0].Id' --output text
```

Confirm the record name (`<name>.<domain>`) is within the zone's
namespace. Confirm the record type (`A`, `AAAA`, `CNAME`, `MX`,
`TXT`, `PTR`, `SRV`, `SPF`, `CAA`, `NAPTR`, or alias-as-A/AAAA).

**Common mistake:** posting to the wrong zone ID when the same name
exists in a public and a private zone. Always disambiguate with
`--hosted-zone-id`, never `--hosted-zone-name`.

### Step 2 — Choose routing policy

| Policy | Field value | When to use | HC mandatory? |
|---|---|---|---|
| Simple | `simple` | one target, no policy | no |
| Weighted | `weighted` | canary, percentage split | yes (per record) |
| Latency | `latency` | multi-region active-active | yes (per record) |
| Failover | `failover` | primary/secondary DR | yes (on PRIMARY) |
| Geolocation | `geolocation` | continent/country/subdivision routing | recommended |
| Geoproximity | `geoproximity` | bias toward/away (calculated) | recommended |
| Multivalue answer | `multivalue answer` | round-robin with failover | yes (per value) |
| IP-based | `ipbased` | EDNS-client-subnet CIDR routing | recommended |

### Step 3 — Resolve target value(s) / alias targets

For non-alias records, capture the IP / CNAME value. For alias
records, capture the AWS resource's DNS name and set
`EvaluateTargetHealth`:

```bash
# ALB alias target
aws elbv2 describe-load-balancers --query \
  'LoadBalancers[0].DNSName' --output text

# CloudFront alias target
aws cloudfront list-distributions --query \
  'DistributionList.Items[0].DomainName' --output text
```

### Step 4 — Configure health checks (per target where required)

```bash
aws route53 create-health-check \
  --caller-reference $(date +%s) \
  --health-check-config Type=HTTPS,Port=443,ResourcePath=/healthz,\
FullyQualifiedDomainName=api.example.com,RequestInterval=30,\
FailureThreshold=3,MeasureLatency=true
```

For string matching, add `EnableSNI=true` and the `MatchString` /
`MatchThreshold` fields. For calculated (AND/OR of children), use
`Type=CALCULATED` and `ChildHealthChecks`. For inverted, set
`Inverted=true` on a child reference.

**Common mistake:** pointing the HC at a VPC-private endpoint. Route
53 health checkers run on public AWS infrastructure and cannot reach
private VPC resources. The HC reports unhealthy forever with no alarm
unless you add one. Use a public endpoint, a Lambda-based HC via
CloudWatch alarm, or a calculated HC of a reachable proxy.

### Step 5 — Build the change-batch POST (atomic)

Route 53 applies a `ChangeResourceRecordSets` call atomically. Always
batch related records (e.g., all weighted records in a set) in a
single POST:

```bash
aws route53 change-resource-record-sets \
  --hosted-zone-id <ZONE_ID> \
  --change-batch file://change-batch.json
```

> **Moved verbatim** → [references/routing-policy-change-batches.md](references/routing-policy-change-batches.md) § "Weighted 90/10 canary change-batch (Step 5 worked JSON)".
> Load when: writing the atomic change-batch for a weighted canary set

**Common mistake:** posting weighted records one-at-a-time. Until both
exist, the weighted set is incomplete and Route 53 sends 100% to the
single existing record, defeating the canary intent. Batch them.

### Step 6 — Optional: Traffic policy / ARC routing control

> **Moved verbatim** → [references/health-check-and-arc-procedures.md](references/health-check-and-arc-procedures.md) § "Step 6 — Traffic policy / ARC routing control CLIs".
> Load when: provisioning a traffic policy + instance or ARC cluster / control panel / routing control / safety rule / readiness check

### Step 7 — Apply TTL appropriate to the policy

Apply per-policy defaults (see the TTL heuristic). Override only with
a reason documented in the checklist rationale.

### Step 8 — Verify via `test-dns-answer` + `get-health-check-status`

```bash
# Resolve as a client would, from a specific resolver
aws route53 test-dns-answer \
  --hosted-zone-id <ZONE_ID> \
  --record-name api.example.com. \
  --record-type A

# Confirm each health check is healthy
aws route53 get-health-check-status --health-check-id <hc-id>

# ARC: confirm routing control state
aws route53-recovery-cluster get-routing-control-state \
  --routing-control-arn <CONTROL_ARN>
```

`test-dns-answer` resolves as if from the Route 53 resolver and shows
exactly which record was returned — this is the only way to verify a
weighted/latency/geo split without a real client.

## NEVER do these things

These anti-patterns cause silent exposure, data-plane bugs, or DR
failures. Each is observed in real production incidents.

1. **NEVER configure weighted / latency / multivalue routing without
   a health check on EVERY record in the set.** Why it's wrong: the
   policy itself does not check target health. A weighted set with one
   dead target and no HC sends the dead target's allotted percentage
   of traffic to a dead IP for the whole TTL window, repeatedly, with
   no alarm. Attach `HealthCheckId` to every record; verify with
   `get-health-check-status` in Step 8.

2. **NEVER create an alias record with `Type: CNAME`.** Why it's
   wrong: alias records are an A/AAAA record with an `AliasTarget`
   value shape, not a CNAME. A CNAME-with-AliasTarget is an API error.
   Worse, a regular CNAME at the zone apex violates DNS standards;
   only alias records can sit at the apex. Always use `Type: A` (or
   `AAAA`) for alias records.

3. **NEVER set `EvaluateTargetHealth: false` on an alias to a load
   balancer and expect automatic failover.** Why it's wrong: Route 53
   returns the alias target's IP regardless of its health when ETH is
   false. A multi-AZ ALB with healthy targets in only one AZ still
   receives all traffic; no DNS-level failover. Set ETH true for any
   alias where you want DNS to react to target health.

4. **NEVER create a geolocation routing set without a default record.**
   Why it's wrong: clients from a continent/country with no matching
   geo record get NXDOMAIN. There is no implicit fallback. Always add
   a final record with `GeoLocation: { Continent: "*" }` (or a
   `simple` record of the same name) as the default.

5. **NEVER flip an ARC routing control without a safety rule and a
   readiness check.** Why it's wrong: a routing control flip is sub-
   second and irreversible until flipped back. Without a safety rule,
   flipping both regional controls off takes the workload to zero with
   no DNS recourse. Without a readiness check, cutover overloads the
   secondary and triggers a cascade failure. Safety rule = mandatory;
   readiness check = mandatory before every flip.

## Output format

```
RECORD_SET: <name> <type> (routing policy: <policy>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Hosted zone confirmed: <zone-id> (<zone-name>)
  [✓|✗] Routing policy: <simple|weighted|latency|failover|geolocation|geoproximity|multivalue|ipbased|alias>
  [✓|✗] Target(s) resolved: <list> (alias: <alias-dns-name>, ETH: true|false)
  [✓|✗] Health check(s) per record: <hc-id-list> (status: Healthy|Unhealthy)
  [✓|✗] Change-batch atomic: <action> <record-count> records
  [✓|✗] Optional feature: traffic-policy | ARC | none
  [✓|✗] TTL applied: <ttl>s (rationale: <policy-appropriate>)
VERIFICATION_COMMANDS:
  <copy-pasteable verification commands>
```

## STRICT output contract

The rules below are hard constraints. Violating any one produces a
checklist that looks complete but contains a silent misconfiguration.
Self-check EVERY emitted block against these rules before returning.

### Required output structure

Every response MUST be a single block using these literal labels, in
this order. Do NOT preface with prose, headings, or disclaimers.

```text
RECORD_SET: <name> <type> (routing policy: <policy>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Hosted zone confirmed: <zone-id> (<zone-name>)
  [✓|✗] Routing policy: <simple|weighted|latency|failover|geolocation|geoproximity|multivalue|ipbased|alias>
  [✓|✗] Target(s) resolved: <list> (alias: <alias-dns-name>, ETH: true|false)
  [✓|✗] Health check(s) per record: <hc-id-list> (status: Healthy|Unhealthy)
  [✓|✗] Change-batch atomic: <action> <record-count> records
  [✓|✗] Optional feature: traffic-policy | ARC | none
  [✓|✗] TTL applied: <ttl>s (rationale: <policy-appropriate>)
VERIFICATION_COMMANDS:
  <copy-pasteable verification commands — one per [✓] item>
```

### FORBIDDEN output patterns

1. **NEVER emit `VERDICT: READY_TO_DEPLOY` without showing ALL 7
   checklist items.** Every item MUST appear with a status marker:
   `[✓]`, `[✗]`, or `[OPTIONAL]`. Omitting a row implies it was not
   evaluated.

2. **NEVER mark Routing policy as `[✓] weighted|latency|multivalue`
   without also marking Health check(s) `[✓]`.** These policies send
   traffic to dead targets without HCs. If the operator declined HCs,
   the HC row MUST be `[✗]` with a one-line warning AND the verdict
   MUST be `PREREQUISITES_MISSING`.

3. **NEVER mark Target(s) `[✓] alias` without confirming
   `EvaluateTargetHealth` is true for ALB/CloudFront/NLB targets.**
   ETH false defeats DNS-level failover for aliases. The checklist
   MUST cite the ETH value explicitly.

4. **NEVER mark Routing policy `[✓] geolocation` without confirming
   a default record.** Geolocation without a default returns NXDOMAIN
   for unmatched regions. The checklist MUST cite the default record
   name or mark the item `[✗]`.

5. **NEVER mark Optional feature `[✓] ARC` without confirming the
   safety rule AND readiness check.** A routing control without a
   safety rule is a single misdirected click away from a total outage.
   The checklist MUST cite the safety rule name and the readiness
   check name.

6. **NEVER mark TTL `[✓]` without a one-line rationale tied to the
   policy.** A 300s TTL on a weighted canary is wrong; a 60s TTL on a
   simple static record is wasteful. The checklist MUST include the
   rationale (e.g., "60s for fast weighted-canary re-normalization").

7. **NEVER emit `VERDICT: PREREQUISITES_MISSING` without citing the
   specific gap.** Each `[✗]` item MUST have a one-line reason:
   `[✗] Health check hc-1234 not found — create HC for target 10.0.0.10
   before referencing it`. A bare `[✗]` is non-compliant.

### Perfect example output — READY_TO_DEPLOY

```text
RECORD_SET: api.example.com A (routing policy: weighted)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Hosted zone confirmed: Z1DABCDEFGHIJ (example.com)
  [✓] Routing policy: weighted
  [✓] Target(s) resolved: primary 10.0.0.10 (w=90, hc-aaa), canary 10.0.0.20 (w=10, hc-bbb)
  [✓] Health check(s): hc-aaa (Healthy), hc-bbb (Healthy) — both endpoint HTTPS /healthz, interval 30s, threshold 3
  [✓] Change-batch atomic: CREATE 2 records (single POST, weighted set complete before apply)
  [OPTIONAL] Optional feature: none
  [✓] TTL applied: 60s (rationale: weighted canary needs fast re-normalization on HC flip)
VERIFICATION_COMMANDS:
  aws route53 test-dns-answer --hosted-zone-id Z1DABCDEFGHIJ --record-name api.example.com. --record-type A
  aws route53 get-health-check-status --health-check-id hc-aaa
  aws route53 get-health-check-status --health-check-id hc-bbb
  aws route53 list-resource-record-sets --hosted-zone-id Z1DABCDEFGHIJ --query 'ResourceRecordSets[?Name==`api.example.com.`]'
```

### Perfect example output — PREREQUISITES_MISSING

> **Moved verbatim** → [references/worked-examples.md](references/worked-examples.md) § "Perfect example output — PREREQUISITES_MISSING".
> Load when: emitting the checklist block for a PREREQUISITES_MISSING verdict (missing HC on a weighted canary)

**Self-check before emit:**
- [ ] All 7 checklist rows present (no omitted items)?
- [ ] Every `[✓]` has a matching verification command?
- [ ] If Routing policy is weighted/latency/multivalue, Health check(s) is also `[✓]` (or verdict is PREREQUISITES_MISSING)?
- [ ] Alias targets cite `EvaluateTargetHealth` value explicitly?
- [ ] Geolocation sets cite a default record?
- [ ] TTL rationale ties to the policy?
- [ ] Every `[✗]` cites the specific gap?

## Recent AWS features

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Recent AWS features".
> Load when: deciding whether a newer feature (CIDR routing, ARC improvements, TP versioning, Lambda HCs, subdivisions) applies


## References (load on demand)

- [references/routing-policy-change-batches.md](references/routing-policy-change-batches.md) — per-policy change-batch JSON, including the weighted 90/10 canary batch moved from SKILL.md
- [references/health-check-and-arc-procedures.md](references/health-check-and-arc-procedures.md) — health-check / traffic-policy / ARC procedures, including the Step 6 CLIs moved from SKILL.md
- [references/worked-examples.md](references/worked-examples.md) — PREREQUISITES_MISSING example output moved from SKILL.md
- [references/advanced-patterns.md](references/advanced-patterns.md) — expert heuristics (weighted-no-HC myth, TTL interaction, ARC safety) and recent AWS features
