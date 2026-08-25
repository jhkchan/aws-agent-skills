---
name: route53-failover-operator
description: Operates Route 53 health checks and DNS failover workflows end-to-end — health-check configuration (endpoint HTTP/HTTPS/TCP, CloudWatch alarm, calculated AND/OR, insulated child checks), the five failover routing policies (failover, latency, geolocation, multivalue, weighted), planned vs emergency failover and failback sequences, TTL strategy (60s for fast failover vs 300s for stability), cross-account hosted zone IAM, and full diagnostic loops (get-health-check-status, list-resource-record-sets, test-dns-answer, CloudWatch HealthCheckMetrics). Runs deterministic pre-checks (health check healthy, secondary reachable, TTL appropriate, CloudWatch alarm exists, cross-account IAM grant) behind a CONFIRM gate and emits a READY, BLOCKED, or COMPLETED verdict per failover. Use when executing a planned weighted failover, emergency failover, failback, diagnosing a failover that did not switch, or wiring cross-account Route 53.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline plan classification. Live-account operations use aws route53 list-health-checks, get-health-check, get-health-check-status, list-resource-record-sets, change-resource-record- sets, get-traffic-policy-instance, test-dns-answer, aws cloudwatch describe-alarms, and dig/nslookup (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '4'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Networking
  task_type: operate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY | BLOCKED | COMPLETED
  when_to_use: Executing a planned DNS failover (weighted 100/0 to 0/100, or swapping failover primary/secondary), running an emergency failover, failing back to primary after a failover, diagnosing why a failover did not switch traffic, creating or updating a health check, choosing between failover/latency/geolocation/multivalue/weighted routing for DR, setting TTL for fast failover, or wiring cross-account Route 53 hosted zone access.
  activation_triggers: failover DNS, switch Route 53 primary secondary, planned failover weighted, emergency failover, failback to primary, Route 53 health check, DNS failover did not switch, traffic not failing over, multivalue answer routing, weighted routing canary, geolocation DR routing, cross-account Route 53 hosted zone, TTL for failover, test-dns-answer
  invocation_schema: 'Input: either (a) a hosted zone + record set configuration plus the intended operation (planned-failover, emergency-failover, failback, create-health-check, update-health-check, diagnose-failover, update- routing), OR (b) a hosted-zone-id + record-name + operation for live- account execution. Output: deterministic OPERATION / VERDICT / PRE_CHECKS / STEPS / POST_VERIFY / NOTES block per failover, where VERDICT is one of READY, BLOCKED, COMPLETED.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Route 53, DNS failover, health check, failover routing, latency routing, geolocation routing, multivalue answer, weighted routing, primary secondary, DNS TTL, planned failover, emergency failover, failback, cross-account hosted zone, CloudWatch alarm, calculated health check, insulated health check, test-dns-answer, change-resource-record-sets
  tags: aws, route53, networking, dns, failover, health-check, dr, operate
---

# Route 53 Failover Operator

## What this skill does

Executes Route 53 DNS failover operations correctly and safely. Runs
deterministic pre-checks before any state-changing CLI (health check
healthy, secondary endpoint reachable, TTL appropriate for the failover
window, CloudWatch alarm wired, cross-account IAM grant present), executes
the failover behind a CONFIRM gate, and verifies the result by confirming
the new record set is authoritative via `test-dns-answer` and the
application is reachable on the secondary. Every planned failover produces
a weighted-shift or primary/secondary swap plan; every emergency failover
surfaces the TTL-lowering step so the operator can shrink the failover
window before flipping routing.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **§ Quick reference** | Verdict thresholds + pre-check priority | Before any operation |
| **§ Mindset** | Why failover is TTL-bound, the healthy-but-broken trap, the confirm gate | Understanding the safety model |
| **§ Pre-flight** | Hosted zone + record set gate — cross-account, recovery window, delegated zones | Before executing any CLI |
| **§ Process** | Per-operation planning: planned, emergency, failback, health check, diagnose, update-routing | When choosing which operation to run |
| **§ Output format** | Structured OPERATION/VERDICT/PRE_CHECKS/STEPS/POST_VERIFY template | Formatting the response |
| **§ Anti-Patterns** | NEVER list — common mistakes that strand traffic or break failover | Review before risky operations |
| **§ Pre-flight safety** | Capture pre-state, confirm gate, DNS propagation verification | Defense-in-depth |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `BLOCKED` | One or more pre-checks failed (health check unhealthy, secondary unreachable, TTL too high for emergency failover, cross-account IAM denied, hosted zone deleted, primary and secondary both unhealthy) | List failures, do NOT execute |
| `READY` | All pre-checks passed; awaiting CONFIRM gate | Emit exact CLI sequence, wait for operator yes |
| `COMPLETED` | Failover finished and post-verification passed (`test-dns-answer` returns secondary IP, primary health check still unhealthy, application reachable on secondary, no client error spike) | Emit verification results, monitoring plan |

**Priority order for pre-checks (apply in this sequence, all must pass for
READY):**

1. **Hosted zone reachability** — zone exists, NOT deleted, record set
   exists with the expected routing policy.
2. **Health check state** — health check exists; for failover routing the
   PRIMARY record's health check is monitored. If the primary health check
   is already unhealthy, Route 53 SHOULD be serving the secondary — verify
   via `test-dns-answer` before changing anything.
3. **Secondary endpoint reachability** — secondary IP/endpoint is actually
   serving traffic (TCP/HTTP probe from outside Route 53).
4. **TTL appropriateness** — for emergency failover the record TTL should
   be <= 60s (or a one-time TTL lower is required first). For planned
   failover any TTL is acceptable but propagation time = TTL.
5. **Cross-account IAM** — if the hosted zone is in a different account,
   the operator's role must have `route53:ChangeResourceRecordSets` on
   `arn:aws:route53:::hostedzone/<id>` granted by the zone-owning account.
6. **CloudWatch alarm wiring** — a CloudWatch alarm on the
   `AWS/Route53` `HealthCheckStatus` metric (or the endpoint's uptime
   metric) exists; without it, the next failover is silent.
7. **Client-side caching awareness** — browser / OS DNS caches may serve
   the old IP for up to TTL; the post-failover verification window must
   account for this.

**Cost/time baselines (2026):**

- Endpoint health check: $0.50/endpoint/month for the first 100, then
  $0.25 each above 100. CloudWatch-alarm-based and calculated health
  checks are free (the underlying alarm costs apply).
- HTTP/HTTPS health check interval: 10s (Fast) or 30s (Standard). 10s
  roughly doubles cost.
- DNS propagation after a record change: bounded by the record TTL.
  Lower TTL = faster failover but more DNS query traffic to Route 53
  authoritative servers.
- Calculated health checks (AND/OR of up to 256 child checks): free, but
  each child check is billed at its own type's rate.

## Mindset

**One-line takeaway:** a failover is not "complete" when the API returns
`PENDING` — it is complete when `test-dns-answer` returns the secondary
IP from all configured resolver regions AND application metrics confirm
the secondary is serving real traffic. Driven by three Route 53
realities:

- **Failover speed is TTL-bound, not health-check-bound.** The health
  check may flip to unhealthy in 10-30 seconds, but every client that
  cached the old IP at TTL=N will keep sending traffic to the primary
  until that cache entry expires. The single highest-leverage failover
  lever is the record TTL — set it to 60s for failover records. A
  300s TTL means up to 5 minutes of stale traffic even after a perfect
  health-check transition.

- **"Healthy" does not mean "working."** A health check that probes
  `/health` returning 200 will report healthy even when the application
  is broken on every other route. The failover trigger is only as good
  as the probe. Pair the endpoint health check with a CloudWatch alarm
  on a real business metric (request success rate, error rate) so a
  false-healthy health check does not mask a real outage.

- **Cross-account Route 53 requires the zone-owning account to grant
  the operator account.** The operator account's IAM role identity-based
  policy is NOT sufficient by itself. The zone-owning account must
  attach a resource-based policy (or delegate via RAM / Organizations
  `AWS::Route53Resolver::*`, or use a cross-account role assumption) that
  allows the operator's role ARN to call
  `route53:ChangeResourceRecordSets` on the hosted zone ARN.

## Pre-flight: hosted zone + record set gate

Run before classification. Misclassifying these produces wrong plans.

**Pagination:** `list-resource-record-sets` paginates at 300 record sets
per page — drain `--start-record-name` / `--start-record-type` to
completion for large zones. `list-health-checks` paginates at 100/page.

**Live-account pre-flight (skip if offline plan audit):**
1. `aws route53 list-hosted-zones-by-name --dns-name <domain>` — find
   the zone; capture `Id`, `Name`, `Config.Comment`, `ResourceRecordSetCount`.
2. `aws route53 list-resource-record-sets --hosted-zone-id <id>` — find
   the failover records; capture `Type`, `SetIdentifier`, `Failover`
   (PRIMARY/SECONDARY), `TTL`, `ResourceRecords`, `HealthCheckId`,
   `RoutingPolicy`.
3. `aws route53 get-health-check --health-check-id <id>` — capture
   `HealthCheckConfig` (Type, FullyQualifiedDomainName, IPAddress, Port,
   ResourcePath, SearchString, Type, RequestInterval, FailureThreshold),
   `HealthCheckVersion`, and the linked CloudWatch alarm region.
4. `aws route53 get-health-check-status --health-check-id <id>` —
   capture `HealthCheckObservations` (one per Route 53 checker region),
   `Status` (Healthy/Unhealthy/LastKnownGoodStatus).
5. `aws route53 get-health-check-last-failure-reason --health-check-id
   <id>` — capture the most recent failure reason string.
6. `aws route53 test-dns-answer --hosted-zone-id <id> --record-name
   <fqdn> --record-type A --resolver-ip 1.1.1.1` — verify what Route 53
   is currently authoritatively answering. Repeat from multiple
   `--resolver-ip` values (1.1.1.1, 8.8.8.8, 9.9.9.9) to catch
   regional divergence.
7. `aws cloudwatch describe-alarms --alarm-name-prefix <name>` — verify
   an alarm exists on the `AWS/Route53` `HealthCheckStatus` metric for
   this health check ID.
8. For cross-account zones: `aws route53 list-resource-record-sets
   --hosted-zone-id <id> --profile <zone-account-profile>` — verify the
   operator has the cross-account grant.

**Malformed input:** if the input JSON is invalid or missing required
fields, emit `VERDICT: ERROR` with `REASON: Hosted zone / record set
configuration is not valid JSON or is missing required fields — cannot
plan.` and `REMEDIATION: Re-fetch with aws route53 list-resource-record-
sets --hosted-zone-id <id> --output json and re-plan.`

| Attribute | Effect on operation |
|---|---|
| Hosted zone `Config.Comment` indicates delegation | Sub-domain delegated to another zone; changes here have no effect on the sub-domain. |
| Record `RoutingPolicy` is not what the operation expects | Wrong operation. Re-classify: a weighted failover requires `WeightedRoutingPolicy`; a failover swap requires `Failover` records. |
| Record `TTL > 300` and operation is `emergency-failover` | BLOCKED — lower TTL to 60 first, wait for old TTL to expire (or accept stale traffic). |
| PRIMARY record `HealthCheckId` is null | BLOCKED — no health check wired; Route 53 always serves PRIMARY. Wire a health check first. |
| Health check `Status: Healthy` but application is broken | False-healthy trap. Investigate the probe path before relying on the health check for failover decisions. |
| Health check `Status: Unhealthy` and operation is `planned-failover` | Route 53 may have already failed over. Verify `test-dns-answer` returns secondary before making changes. |
| Both PRIMARY and SECONDARY health checks `Unhealthy` | BLOCKED — Route 53 returns all records (no healthy target); fix the secondary first. |
| Cross-account zone and operator role lacks `route53:ChangeResourceRecordSets` | BLOCKED — request the grant from the zone-owning account. |
| `CalculatorConfig` present (calculated health check) | Verify child health checks individually; the parent's status is AND/OR of children. |

## Process — operation planning (apply in order)

### Step 0: Expert knowledge — non-obvious Route 53 behaviors

These behaviors are easy to misjudge without operational failover
experience. Each changes a plan if ignored:

- **Route 53 health checks run from 3+ global regions, not one.** Each
  checker region issues the probe independently; a health check is
  unhealthy only when the failure threshold (default 3) is hit
  consecutively across the merged observation. This means a single-
  region network blip rarely triggers failover, but a true outage does
  in ~10-30 seconds (interval x threshold).

- **The record TTL is the failover contract, not the health check
  interval.** Even after Route 53 marks the primary unhealthy and stops
  returning its IP, every recursive resolver and every client OS that
  cached the old IP at the previous TTL will keep using it. Lowering TTL
  to 60s ahead of a planned failover is the single highest-leverage
  action; for an emergency failover with a 300s TTL, the operator must
  either accept up to 5 minutes of stale traffic or proactively purge
  caches.

- **Failover routing policy requires paired records.** One record has
  `Failover: PRIMARY` with a `HealthCheckId`; the other has `Failover:
  SECONDARY` (no health check, or its own health check). Route 53
  returns the PRIMARY IP when its health check is healthy, otherwise
  the SECONDARY. There is no weighted gradient.

- **Weighted routing is the right tool for canary/blue-green, not
  failover routing.** A weighted policy with weights 100/0 is a valid
  "failover" shape, and shifting 100->0/0->100 is a planned failover
  that can be paused (50/50) or rolled back. Failover routing is
  automatic but binary; weighted is manual but graduated. Choose
  weighted for planned failovers that may need to pause.

- **Multivalue answer is NOT load balancing.** It returns up to 8
  healthy IPs per query (shuffled), but clients pick one. It is a
  "round-robin with health checks" — useful for spreading load across
  many endpoints, not for primary/secondary failover. Combine with
  per-endpoint health checks for opportunistic redundancy.

- **Latency routing does not fail over; it falls back.** If the lowest-
  latency region's endpoint is unhealthy, Route 53 serves the next-
  lowest-latency healthy region. This is automatic and works without a
  failover record. Use latency routing for multi-region active-active.

- **Geolocation routing can pair with failover for regional DR.** A
  geolocation record (e.g., "users in Europe") can be paired with a
  geolocation + failover SECONDARY record so that if the primary EU
  endpoint is unhealthy, EU users fall back to a secondary EU endpoint.
  This requires both records to share the same geolocation continent
  code.

- **Calculated health checks (AND/OR) compose other health checks.** A
  calculated check lets you say "failover only when BOTH the endpoint
  check AND the database-alarm-based check are unhealthy." This is the
  antidote to the false-healthy trap. Up to 256 child checks; the
  calculated check itself is free.

- **Insulated health checks prevent child-check influence on other
  calculated checks.** Insulating a child health check prevents it from
  affecting the status of OTHER calculated health checks that reference
  it. Use when a child check is shared between multiple calculated
  checks with different semantics.

- **`test-dns-answer` shows what Route 53 authoritatively answers from
  a specific resolver IP.** It does NOT show what a real client at that
  IP sees — recursive resolvers cache. To verify end-to-end, run
  `dig @1.1.1.1 <fqdn>` and `dig @8.8.8.8 <fqdn>` from multiple
  networks. `test-dns-answer` is authoritative truth; `dig` is observed
  truth.

- **CloudWatch-alarm-based health checks are free but slower.** A
  CloudWatch alarm in ALARM state flips the health check unhealthy.
  This avoids the per-endpoint fee but adds alarm-evaluation latency
  (typically 1 minute for a 1-minute period). Use for composite health
  signals; use endpoint checks for fast failover.

- **Cross-account hosted zone IAM requires a resource-based grant.**
  Route 53 does NOT support resource-based policies on hosted zones the
  way S3/KMS do — the zone-owning account must either (a) attach an
  inline policy to a role the operator assumes via STS, or (b) use AWS
  RAM to share the hosted zone with the operator account via
  Organizations or a direct invitation. Identity-based policies in the
  operator account alone cannot grant cross-account Route 53 access.

- **`UPSERT` is the safer change action than `CREATE` or `DELETE`.**
  `UPSERT` creates the record if it does not exist, or updates it if it
  does. `CREATE` fails if the record exists; `DELETE` fails if it does
  not. For failover operations, prefer `UPSERT` so the same change
  batch works whether the record is in its pre-state or post-state.

- **`ChangeResourceRecordSets` is eventually consistent.** The API
  returns a `ChangeInfo` with `Status: PENDING` immediately; the actual
  DNS change propagates within 60 seconds typically. Poll
  `get-change --id <change-id>` until `Status: INSYNC` before declaring
  the failover applied.

- **Both records unhealthy means Route 53 returns all records.** If
  PRIMARY and SECONDARY are both unhealthy (both have failing health
  checks), Route 53 returns BOTH IPs — it prefers serving a possibly-
  bad answer over no answer. This is why a BLOCKED pre-check on "both
  unhealthy" matters: failing over when the secondary is also down does
  not help.

### Step 1: Pre-check gate — BLOCKED if any check fails

Run ALL pre-checks for the chosen operation. If ANY fails, the verdict
is BLOCKED with the failed checks in PRE_CHECKS. Do NOT execute.

**For ALL operations:**
1. Hosted zone exists (`list-hosted-zones-by-name` returns the zone).
2. Record set(s) exist with the expected `RoutingPolicy`.
3. Cross-account IAM grant present (if zone is in another account).
4. The `ChangeBatch` is well-formed (no duplicate names+types+set-
   identifiers; `UPSERT` actions specify all required fields for the
   routing policy).

**For planned-failover (weighted 100/0 -> 0/100):**
5. Both weighted records exist with `WeightedRoutingPolicy`.
6. The "next-primary" record's endpoint is reachable (TCP/HTTP probe).
7. The "next-primary" record's health check (if any) is `Healthy`.
8. The current-primary's `TTL` is appropriate for the failover window
   (recommend <= 300s; 60s for fast).

**For planned-failover (failover routing swap — make OLD primary the
secondary, OLD secondary the primary):**
5. PRIMARY and SECONDARY records exist with `Failover` policy.
6. PRIMARY health check exists and is currently `Healthy` OR the
   operator is intentionally inverting the topology (see failback).
7. The NEW primary (old SECONDARY) endpoint is reachable and its health
   check (if any) is `Healthy`.
8. The change-batch upserts BOTH records atomically (PRIMARY and
   SECONDARY in the same change-batch).

**For emergency-failover:**
5. PRIMARY health check is `Unhealthy` (the trigger for the emergency).
6. SECONDARY endpoint is reachable (independent probe outside Route 53).
7. SECONDARY's health check (if any) is `Healthy`.
8. TTL of the failover record: if > 60s, the plan must lower TTL first
   (UPSERT the record with TTL=60, wait old-TTL seconds, THEN swap) —
   OR the operator explicitly accepts stale-traffic window = old TTL.

**For failback (reverse a prior failover):**
5. The prior-failover's NEW primary (the secondary during the outage)
   is currently serving traffic (confirmed via `test-dns-answer`).
6. The prior PRIMARY's endpoint has been restored and its health check
   is `Healthy` for at least 2 consecutive intervals (avoid flapping).
7. TTL is <= 60s for the failback (or accept the stale window).
8. Application team has signed off on the failback timing.

**For create-health-check / update-health-check:**
5. The endpoint URL/port/path is reachable from at least one public IP
   (Route 53 checkers are on the public internet).
6. For HTTPS checks, the certificate is valid (not expired, hostname
   matches). Route 53 does NOT validate the cert by default — enable
   `EnableSNIProvisionally` and check `EnableSNI` for SNI support.
7. For search-string checks, the response body contains the string when
   healthy.
8. For CloudWatch-alarm-based checks, the alarm exists in the same
   region as the health check's CloudWatch metric.
9. For calculated checks, `ChildHealthChecks` references valid health
   check IDs and `InsufficientDataHealthStatus` is set intentionally.

**For diagnose-failover (read-only, no BLOCKED gate):**
5. Read `get-health-check-status`, `test-dns-answer`, and the failure-
   mode table to identify the root cause.

**For update-routing (change routing policy or weights):**
5. New `RoutingPolicy` is valid for the record type (A/AAAA only for
   multivalue; any for weighted/latency/geolocation/failover).
6. New weights sum to a sensible total (Route 53 normalizes, but a
   0-weight record gets NO traffic).
7. If changing FROM `WeightedRoutingPolicy` TO `Failover`, the change
   batch must DELETE the weighted records and CREATE the failover
   pair (you cannot UPSERT across routing policies).

**Failover failure-mode table (use during diagnose-failover):**

| Symptom | Root cause | Fix |
|---|---|---|
| `test-dns-answer` still returns PRIMARY IP after health check unhealthy | TTL caching by recursive resolvers; or `ChangeResourceRecordSets` not yet INSYNC | Wait TTL seconds; poll `get-change`; verify `test-dns-answer` from multiple resolvers |
| PRIMARY health check `Healthy` but app is broken | Health check probe path too shallow (e.g., `/health` returns 200 while app is broken) | Deepen the probe (check a real endpoint), or add a calculated health check with a CloudWatch alarm on error rate |
| PRIMARY health check `Unhealthy` but failover did not happen | PRIMARY record missing `HealthCheckId`, or the record's routing policy is not `Failover`, or there is no SECONDARY record | Wire the health check to the PRIMARY record; add a SECONDARY record |
| Both records returned (both unhealthy) | PRIMARY and SECONDARY health checks both failing | Fix the secondary before failing over; Route 53 returns both as a last resort |
| Health check `Unhealthy` with reason "Connection timed out" | Endpoint firewall blocks Route 53 checker IPs (route53-checker-ips AWS-managed prefix list) | Allow the AWS Route 53 checker prefix list on the endpoint SG/firewall |
| Health check `Unhealthy` with reason "No response from server" | Endpoint crashed or port closed | Restart the endpoint service |
| Health check `Unhealthy` with reason "String not found" | Search string not in response body (app deployed a new build that changed the response) | Update `SearchString` or the application's health endpoint |
| Cross-account `AccessDenied` on `ChangeResourceRecordSets` | Operator role not granted by zone-owning account | Zone account attaches inline policy or shares via RAM |
| DNS still serves old IP from `dig` but `test-dns-answer` is correct | Recursive resolver / OS DNS cache | Wait TTL seconds; flush DNS (`sudo dscacheutil -flushcache` macOS, `sudo systemctl restart systemd-resolved` Linux) |
| Latency routing serves a "wrong" region | Latency DB has stale measurements; or endpoint moved | Use `test-dns-answer --resolver-ip <client-resolver>` to inspect per-resolver answers |
| Weighted routing returns a 0-weight record | Both records have weight 0; or weights mis-typed | Verify `Weight` values; sum of all weights for the same name+type = traffic distribution |
| `ChangeInfo` stuck `PENDING` > 5 minutes | Rare Route 53 backend delay | Open AWS support; do NOT submit a second change-batch for the same record |

### Step 2: READY — emit operation plan

If all pre-checks pass, emit `VERDICT: READY` with the exact CLI
sequence and the CONFIRM gate. The plan includes:

- The exact `change-resource-record-sets` JSON batch with all fields
  populated from the current record set + the operation parameters.
- The expected DNS propagation time (TTL seconds for cached resolvers;
  near-instant for uncached).
- The expected side-effects (which IPs Route 53 will answer with after
  INSYNC; which health check transitions to expect).
- The CONFIRM gate prompt.
- The verification step (`test-dns-answer` + `dig` from multiple
  resolvers + application metric check).

### Step 3: Execute behind CONFIRM gate

- **MANDATORY CONFIRMATION GATE.** Before any state-changing CLI
  (`change-resource-record-sets`, `update-health-check`,
  `delete-health-check`, `create-health-check`), emit:
  `CONFIRM: About to <operation> on <fqdn> in hosted zone <id> (account
  <account> region global). This will <consequence>. Proceed? (yes/no)`.
  Do NOT execute until the operator confirms.
- Capture pre-state for rollback: `aws route53 list-resource-record-sets
  --hosted-zone-id <id> --output json > /tmp/<id>-rrsets-pre-$(date
  +%s).json` AND `aws route53 test-dns-answer --hosted-zone-id <id>
  --record-name <fqdn> --record-type A --resolver-ip 1.1.1.1 --output
  json > /tmp/<fqdn>-dnsanswer-pre-$(date +%s).json`.
- Execute the change-batch. The API returns `ChangeInfo.Id`; capture
  it for status polling.
- Poll `aws route53 get-change --id <change-id>` until
  `Status: INSYNC` (typically 5-60 seconds).

### Step 4: Post-verification — COMPLETED

After the change reaches INSYNC, run post-verification. ALL checks must
pass for `COMPLETED`.

1. `test-dns-answer --hosted-zone-id <id> --record-name <fqdn>
   --record-type A --resolver-ip 1.1.1.1` returns the NEW primary IP.
   Repeat from `8.8.8.8` and `9.9.9.9`.
2. `dig @1.1.1.1 <fqdn> +short` returns the NEW primary IP from at
   least one major public resolver (tolerate cache lag on others).
3. The PRIMARY health check (if applicable) reports `Healthy` for the
   new primary, OR (for failover FROM a down primary) the SECONDARY
   health check reports `Healthy`.
4. Application metric dashboards show traffic shifting to the new
   primary (sample 2x TTL post-change).
5. For weighted failover: confirm the new weight distribution by
   observing traffic share in the metrics.
6. For failover routing: confirm `test-dns-answer` no longer returns
   the old primary IP from any resolver.

If ANY verification fails, emit `VERDICT: ERROR` with the failure
details — do not claim COMPLETED. A failed verification typically means
DNS caching is still serving the old IP (wait longer) or the change-
batch did not apply as expected (inspect the INSYNC record set).

## Output format (per operation)

```text
OPERATION: <planned-failover | emergency-failover | failback | create-health-check | update-health-check | diagnose-failover | update-routing>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <fqdn> (hosted zone: <id>, routing policy: <policy>)
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command or change-batch JSON with all fields populated>
  2. <wait / monitoring command>
  3. <next step>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
NOTES: <TTL, propagation estimate, monitoring, caveats>
```

### Worked example — planned-failover (weighted 100/0 -> 0/100)

```text
OPERATION: planned-failover
VERDICT: READY
TARGET: api.example.com (hosted zone: Z2ABCDEFGHIJK, routing policy:
        weighted)
PRE_CHECKS:
  - [PASS] Hosted zone Z2ABCDEFGHIJK exists, not deleted
  - [PASS] Weighted records found:
    api.example.com A SetIdentifier=blue  Weight=100  Value=10.0.0.10
    api.example.com A SetIdentifier=green Weight=0    Value=10.0.1.10
  - [PASS] Green endpoint 10.0.1.10 reachable on port 443 (TCP probe OK)
  - [PASS] Green health check h-abcdef1234 Status: Healthy
  - [PASS] Current TTL: 60s (acceptable for fast failover)
  - [PASS] Cross-account IAM: operator role authorized in zone account
  - [PASS] CloudWatch alarm api-example-failover exists on
    AWS/Route53 HealthCheckStatus
STEPS:
  1. CONFIRM: About to flip weighted routing on api.example.com in
     hosted zone Z2ABCDEFGHIJK (account 111111111111, global Route 53).
     Blue weight 100->0; Green weight 0->100. Traffic will shift from
     10.0.0.10 (blue) to 10.0.1.10 (green). DNS propagation bounded by
     60s TTL. Proceed? (yes/no)
  2. aws route53 change-resource-record-sets \
       --hosted-zone-id Z2ABCDEFGHIJK \
       --change-batch '{
         "Changes": [
           {"Action":"UPSERT","ResourceRecordSet":{
             "Name":"api.example.com.",","Type":"A",
             "SetIdentifier":"blue","Weight":0,
             "TTL":60,"ResourceRecords":[{"Value":"10.0.0.10"}],
             "HealthCheckId":"h-blue123"}},
           {"Action":"UPSERT","ResourceRecordSet":{
             "Name":"api.example.com.","Type":"A",
             "SetIdentifier":"green","Weight":100,
             "TTL":60,"ResourceRecords":[{"Value":"10.0.1.10"}],
             "HealthCheckId":"h-abcdef1234"}}
         ]
       }'
  3. Capture ChangeInfo.Id; poll:
     aws route53 get-change --id <change-id>
     until Status: INSYNC (typically 5-30 seconds).
POST_VERIFY:
  - (pending execution)
NOTES:
  - DNS propagation: up to 60s for cached recursive resolvers (TTL).
    Uncached resolvers see the new answer within seconds of INSYNC.
  - Rollback: re-run the same change-batch with weights inverted
    (blue=100, green=0). Keep the rollback command ready.
  - Watch the application error-rate dashboard for 2x TTL post-change
    (120s) to catch a bad green deployment before declaring COMPLETED.
```

### Worked example — emergency-failover (TTL lowering required)

```text
OPERATION: emergency-failover
VERDICT: READY
TARGET: api.example.com (hosted zone: Z2ABCDEFGHIJK, routing policy:
        failover)
PRE_CHECKS:
  - [PASS] Failover records found:
    api.example.com A SetIdentifier=primary   Failover=PRIMARY
      Value=10.0.0.10 HealthCheckId=h-primary
    api.example.com A SetIdentifier=secondary Failover=SECONDARY
      Value=10.0.1.10
  - [PASS] PRIMARY health check h-primary Status: Unhealthy
    (reason: Connection timed out, 3 consecutive failures)
  - [PASS] Secondary endpoint 10.0.1.10 reachable on port 443
  - [PASS] CloudWatch alarm api-example-failover in ALARM state
  - [WARN] Current TTL: 300s — lowering to 60s FIRST to shrink the
    stale-traffic window. The full failover will take up to old-TTL
    (300s) for clients that cached at 300s; new clients see 60s.
STEPS:
  1. CONFIRM: About to lower TTL on api.example.com failover records
     from 300s to 60s in hosted zone Z2ABCDEFGHIJK. Then, after old TTL
     expires, swap PRIMARY and SECONDARY values (10.0.0.10 becomes
     SECONDARY, 10.0.1.10 becomes PRIMARY). This redirects traffic from
     the down primary to the secondary. Proceed? (yes/no)
  2. Phase 1 — lower TTL (apply immediately, then wait old-TTL seconds):
     aws route53 change-resource-record-sets \
       --hosted-zone-id Z2ABCDEFGHIJK \
       --change-batch '{
         "Changes": [
           {"Action":"UPSERT","ResourceRecordSet":{
             "Name":"api.example.com.","Type":"A",
             "SetIdentifier":"primary","Failover":"PRIMARY",
             "TTL":60,"ResourceRecords":[{"Value":"10.0.0.10"}],
             "HealthCheckId":"h-primary"}},
           {"Action":"UPSERT","ResourceRecordSet":{
             "Name":"api.example.com.","Type":"A",
             "SetIdentifier":"secondary","Failover":"SECONDARY",
             "TTL":60,"ResourceRecords":[{"Value":"10.0.1.10"}]}}
         ]
       }'
     # Wait 300 seconds (old TTL) for resolver caches to expire.
  3. Phase 2 — swap topology after old TTL expires:
     aws route53 change-resource-record-sets \
       --hosted-zone-id Z2ABCDEFGHIJK \
       --change-batch '{
         "Changes": [
           {"Action":"UPSERT","ResourceRecordSet":{
             "Name":"api.example.com.","Type":"A",
             "SetIdentifier":"primary","Failover":"PRIMARY",
             "TTL":60,"ResourceRecords":[{"Value":"10.0.1.10"}],
             "HealthCheckId":"h-secondary"}},
           {"Action":"UPSERT","ResourceRecordSet":{
             "Name":"api.example.com.","Type":"A",
             "SetIdentifier":"secondary","Failover":"SECONDARY",
             "TTL":60,"ResourceRecords":[{"Value":"10.0.0.10"}]}}
         ]
       }'
  4. Poll: aws route53 get-change --id <change-id> until INSYNC.
POST_VERIFY:
  - (pending execution)
NOTES:
  - Emergency mode: the primary is already unhealthy. Route 53 SHOULD
    already be serving the secondary (10.0.1.10) for clients whose
    caches expired. Verify with test-dns-answer and dig BEFORE running
    Phase 2 — if Route 53 is already serving 10.0.1.10, you only need
    Phase 1 (TTL lowering) and can defer Phase 2 (topology swap) until
    the primary is restored.
  - Bring a new health check online for the new primary (10.0.1.10)
    before the swap, OR confirm the existing h-secondary health check
    is wired to 10.0.1.10 and reports Healthy.
```

### Worked example — diagnose-failover (BLOCKED with remediation)

```text
OPERATION: diagnose-failover
VERDICT: BLOCKED
TARGET: api.example.com (hosted zone: Z2ABCDEFGHIJK, routing policy:
        failover)
PRE_CHECKS:
  - [PASS] Hosted zone exists, failover records present
  - [PASS] PRIMARY health check h-primary Status: Unhealthy
  - [FAIL] SECONDARY health check h-secondary Status: Unhealthy
    (reason: "Connection timed out" from all 3 checker regions)
  - [INFO] test-dns-answer returns BOTH IPs (10.0.0.10 and 10.0.1.10) —
    Route 53 is in last-resort mode because both records are unhealthy
STEPS: (none — secondary is also down)
POST_VERIFY: (none)
NOTES:
  - Root cause: the failover target (secondary) is also unreachable.
    Route 53 returns both records because it prefers a possibly-bad
    answer over no answer.
  - Fix order:
    1. Restore the secondary endpoint 10.0.1.10 (restart service /
       fix network / fail over the underlying compute).
    2. Verify h-secondary flips to Healthy:
       aws route53 get-health-check-status --health-check-id h-secondary
    3. Once secondary is Healthy, test-dns-answer should return only
       10.0.1.10. Confirm before any further routing changes.
    4. Then diagnose and restore the primary separately; failback only
       when h-primary has been Healthy for >= 2 consecutive intervals.
```

## STRICT output contract

This section codifies the exact output shape the eval harness asserts
against. Every invocation MUST produce output that matches this
contract or the response is rejected. The labels are case-sensitive
all-caps keywords — no markdown styling, no lowercase variants.

### Required output structure

Every response MUST be a single block with these literal labels, in
this order:

```text
OPERATION: <planned-failover | emergency-failover | failback | create-health-check | update-health-check | diagnose-failover | update-routing>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <fqdn> (hosted zone: <id>, routing policy: <policy>)
PRE_CHECKS:
  - [PASS|FAIL|WARN|INFO] <check description>
STEPS:
  1. <CONFIRM gate prompt>
  2. <CLI command or change-batch JSON with all fields populated>
  3. <wait / monitoring command>
POST_VERIFY:
  - [PASS|FAIL] <verification description>
NOTES: <TTL, propagation estimate, monitoring, caveats>
```

### FORBIDDEN output patterns

1. **NEVER output READY without verifying the health check status
   (get-health-check-status).** The health check observation status
   is the single most critical pre-check — a READY verdict without an
   explicit `[PASS] Health check <id> Status: Healthy|Unhealthy` row
   in PRE_CHECKS is rejected. The status must come from
   `get-health-check-status`, not `get-health-check` (which returns
   config, not runtime state).

2. **NEVER recommend a TTL > 300 for failover scenarios — low TTL
   (60s) is required for fast failover.** A plan that emits a
   failover record with TTL > 300 and does not include a TTL-lowering
   step first is a hard failure. For emergency failover with existing
   TTL > 60s, the plan MUST include Phase 1 (lower TTL) before Phase 2
   (topology swap).

3. **NEVER confuse weighted routing with failover routing — weighted
   shifts traffic gradually, failover is binary.** A plan that uses
   `Failover: PRIMARY/SECONDARY` records for a canary deployment, or
   uses `WeightedRoutingPolicy` for an automatic failover, is
   misclassified. The OPERATION label and the record routing policy
   must be consistent.

4. **NEVER emit STEPS without a CONFIRM gate preceding any
   state-changing CLI command.** Every STEPS block that includes
   `change-resource-record-sets`, `create-health-check`,
   `update-health-check`, or `delete-health-check` MUST have a
   `CONFIRM: About to <operation>...` prompt as the first step.
   Auto-executing without the gate is a hard failure.

5. **NEVER omit POST_VERIFY verification commands — a failover is
   COMPLETED only after `test-dns-answer` confirms the new IP.** A
   verdict of COMPLETED without `[PASS] test-dns-answer returns
   <new-IP>` in POST_VERIFY is rejected. INSYNC from the API is not
   sufficient — recursive resolvers cache up to TTL.

6. **NEVER submit a change-batch that UPSERTs only one record of a
   failover pair.** PRIMARY and SECONDARY must be in the SAME
   `change-resource-record-sets` batch — splitting them creates a
   window where neither record is in a consistent state.

### Perfect example output

```text
OPERATION: planned-failover
VERDICT: READY
TARGET: api.example.com (hosted zone: Z2ABCDEFGHIJK, routing policy: weighted)
PRE_CHECKS:
  - [PASS] Hosted zone Z2ABCDEFGHIJK exists, not deleted
  - [PASS] Weighted records found:
    api.example.com A SetIdentifier=blue  Weight=100  Value=10.0.0.10
    api.example.com A SetIdentifier=green Weight=0    Value=10.0.1.10
  - [PASS] Green endpoint 10.0.1.10 reachable on port 443 (TCP probe OK)
  - [PASS] Green health check h-abcdef1234 Status: Healthy
  - [PASS] Current TTL: 60s (acceptable for fast failover)
  - [PASS] Cross-account IAM: operator role authorized in zone account
  - [PASS] CloudWatch alarm api-example-failover exists on
    AWS/Route53 HealthCheckStatus
STEPS:
  1. CONFIRM: About to flip weighted routing on api.example.com in
     hosted zone Z2ABCDEFGHIJK (account 111111111111, global Route 53).
     Blue weight 100->0; Green weight 0->100. Traffic will shift from
     10.0.0.10 (blue) to 10.0.1.10 (green). DNS propagation bounded by
     60s TTL. Proceed? (yes/no)
  2. aws route53 change-resource-record-sets \
       --hosted-zone-id Z2ABCDEFGHIJK \
       --change-batch '{
         "Changes": [
           {"Action":"UPSERT","ResourceRecordSet":{
             "Name":"api.example.com.","Type":"A",
             "SetIdentifier":"blue","Weight":0,
             "TTL":60,"ResourceRecords":[{"Value":"10.0.0.10"}],
             "HealthCheckId":"h-blue123"}},
           {"Action":"UPSERT","ResourceRecordSet":{
             "Name":"api.example.com.","Type":"A",
             "SetIdentifier":"green","Weight":100,
             "TTL":60,"ResourceRecords":[{"Value":"10.0.1.10"}],
             "HealthCheckId":"h-abcdef1234"}}
         ]
       }'
  3. Capture ChangeInfo.Id; poll:
     aws route53 get-change --id <change-id>
     until Status: INSYNC (typically 5-30 seconds).
POST_VERIFY:
  - (pending execution)
NOTES:
  - DNS propagation: up to 60s for cached recursive resolvers (TTL).
    Uncached resolvers see the new answer within seconds of INSYNC.
  - Rollback: re-run the same change-batch with weights inverted
    (blue=100, green=0). Keep the rollback command ready.
  - Watch the application error-rate dashboard for 2x TTL post-change
    (120s) to catch a bad green deployment before declaring COMPLETED.
```

## Anti-Patterns — NEVER

- NEVER submit an emergency failover change-batch without first lowering
  the TTL to 60s (or explicitly accepting the stale-traffic window =
  old TTL). A 300s TTL means up to 5 minutes of traffic continues to
  the down primary even after Route 53 stops returning it.

- NEVER assume `Status: INSYNC` from `ChangeResourceRecordSets` means
  clients see the new IP. INSYNC means Route 53's authoritative servers
  have the change. Recursive resolvers and OS DNS caches serve stale
  answers up to TTL. Verify with `dig` from multiple resolvers.

- NEVER trust a single health check as the sole failover trigger. A
  shallow probe (`/health` returning 200) reports healthy even when the
  app is broken everywhere else. Pair with a calculated health check
  (AND) that includes a CloudWatch alarm on a real business metric.

- NEVER operate failover routing without a SECONDARY record. A PRIMARY
  record alone, when unhealthy, causes Route 53 to return NO answer
  (NXDOMAIN-like behavior for that record). The failover contract
  requires the pair.

- NEVER submit a change-batch that UPSERTs only one of the failover
  pair. PRIMARY and SECONDARY must be updated in the SAME change-batch
  (Route 53 applies changes atomically within a batch). Splitting them
  risks a window where neither record is in a consistent state.

- NEVER delete a health check that is still associated with a record
  set. Route 53 will treat the record as always-healthy (or always-
  unhealthy depending on policy) once the check is gone. Always
  disassociate (`UPSERT` the record without `HealthCheckId`) before
  `delete-health-check`.

- NEVER use weighted routing with a 0-weight on BOTH records. Route 53
  returns nothing for the name. At least one record must have weight
  >= 1.

- NEVER assume a cross-account operator role has Route 53 access by
  default. The zone-owning account MUST grant the operator's role ARN
  via an inline policy or RAM share. Identity-based policies in the
  operator account are not sufficient on their own.

- NEVER rely on `dig` from a single network for failover verification.
  Different recursive resolvers cache independently. Probe at least
  `1.1.1.1`, `8.8.8.8`, and `9.9.9.9`. Use `test-dns-answer` for
  authoritative truth.

- NEVER use `CREATE` action in a failover change-batch when the record
  might already exist. `CREATE` fails if the record exists. Use
  `UPSERT`. Use `DELETE` only when you intend to remove the record.

- NEVER treat multivalue answer routing as load balancing. It returns
  up to 8 healthy IPs per query, shuffled, but clients pick one and
  stick with it. Multivalue is for spreading load across many
  endpoints, not for primary/secondary failover.

- NEVER assume latency routing will fail over. It falls back to the
  next-lowest-latency healthy region automatically. There is no
  explicit failover record needed. But if ALL regions are unhealthy,
  latency routing returns all records (last-resort).

- NEVER change routing policy (e.g., from Weighted to Failover) via a
  single UPSERT. Routing policy is fixed per record. You must DELETE
  the old-policy record(s) and CREATE the new-policy record(s) in the
  same change-batch.

- NEVER auto-execute a state-changing Route 53 CLI without the CONFIRM
  gate. Failovers have traffic-shifting side effects that can storm
  the workload if the target is unprepared.

- NEVER failback to a primary that has been Healthy for less than 2
  consecutive health check intervals. A flapping primary causes
  repeated failover/failback cycles that destabilize the workload.

- NEVER block on a calculated health check's `InsufficientDataHealthStatus`
  default. If child checks have insufficient data, the calculated
  check's behavior depends on this setting (Healthy/Unhealthy/LastKnown-
  GoodStatus). Set it explicitly to match the workload's risk tolerance.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`change-resource-record-sets`, `create-health-check`,
  `update-health-check`, `delete-health-check`), emit: `CONFIRM: About
  to <operation> on <fqdn> in hosted zone <id> (account <account>,
  global Route 53). This will <consequence>. Proceed? (yes/no)`. Do
  NOT execute until the operator confirms.

- **Capture pre-state for rollback.** Before any failover:
  `aws route53 list-resource-record-sets --hosted-zone-id <id> --output
  json > /tmp/<id>-rrsets-pre-$(date +%s).json` AND `aws route53
  test-dns-answer --hosted-zone-id <id> --record-name <fqdn>
  --record-type A --resolver-ip 1.1.1.1 --output json > /tmp/<fqdn>-
  dnsanswer-pre-$(date +%s).json`. These captures are critical for
  rollback — if the failover makes things worse, you need the exact
  pre-change record set to revert.

- **Verify the failover target is healthy before swapping.** For
  planned and failback operations, the new primary's health check must
  be `Healthy` for >= 2 consecutive intervals. For emergency
  operations, the secondary endpoint must be independently reachable
  even if no health check is wired.

- **Verify the change-batch is well-formed.** All records in a
  failover pair must be in the same change-batch. `UPSERT` actions
  must specify `Name`, `Type`, `TTL`, and the routing-policy-specific
  fields (`Weight`, `Failover`, `Region`, `GeoLocation`, or
  `MultiValueAnswer`).

- **Prefer additive changes over destructive ones.** Lowering TTL,
  adding a SECONDARY record, and creating a health check are
  reversible. DELETing a record or a health check is hard to reverse —
  do it only after confirming the new state is stable.

- **Poll `get-change` until `INSYNC`.** The `ChangeResourceRecordSets`
  API returns immediately with `PENDING`. Authoritative DNS only
  reflects the change after `INSYNC`. Do not declare COMPLETED based
  on the API response alone.

## Recent AWS features (2024-2026)

- **Health check `EnableSNI` GA (2024):** Server Name Indication
  support on HTTPS health checks. Required when the endpoint uses
  virtual-hosted TLS (multiple certs on one IP). Without SNI, Route 53
  receives the default certificate which may not match the probe
  hostname.

- **CloudWatch-alarm-based health check refinements (2024-2025):**
  Health checks can now be driven directly by a CloudWatch alarm in
  ALARM state, with no per-endpoint probe. Useful when the health
  signal is a composite metric (e.g., error rate > threshold) rather
  than an HTTP response.

- **Calculated health check `InsufficientDataHealthStatus` (2024):**
  Explicit control over the parent's status when child checks have
  insufficient data. Default is `LastKnownGoodStatus`; set to
  `Unhealthy` for fail-fast workloads.

- **Insulated child health checks (2024-2025):** A child health check
  can be marked insulated so that its status does not affect OTHER
  calculated checks that reference it. Use when sharing a child check
  between calculated checks with different semantics.

- **Cross-account hosted zone sharing via RAM (2024):** AWS RAM
  supports sharing Route 53 hosted zones with member accounts in an
  Organization. The zone-owning account creates a RAM resource share;
  member accounts can then manage records via their own IAM roles.
  Replaces the older inline-policy-only pattern.

- **`test-dns-answer` mulcdtiple resolver IPs (2024):** The
  `test-dns-answer` API now accepts any public resolver IP, allowing
  operators to verify Route 53's answer from the perspective of
  specific resolver networks. Previously limited to a small set.

- **Route 53 Resolver DNS Firewall integration (2024-2025):** For
  VPC-resolver-based failover verification, the Resolver DNS Firewall
  can block or allow specific domains. Verify the firewall is not
  blocking the failover target domain during VPC-internal tests.

- **CidrRoutingConfig (2025):** A new routing policy that returns
  different answers based on the client's CIDR block. Useful for
  deterministic failover by client geography (e.g., send corporate
  ranges to a known-good endpoint during DR).

## Domain

AWS CloudOps / Route 53 DNS Failover, Health Checks & Disaster Recovery.

## AWS documentation

- **Route 53 Developer Guide** — https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/
- **Health checks** — https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/dns-failover-determining-health-of-endpoints.html
- **Routing policies** — https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-policy.html
- **Configuring DNS failover** — https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/dns-failover.html
- **Calculated health checks** — https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/health-checks-type-calc.html
- **Cross-account hosted zones** — https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/Cross-Account-Zones.html
- **Route 53 API Reference** — https://docs.aws.amazon.com/Route53/latest/APIReference/
- **Route 53 CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/route53/
- **Route 53 checker IP ranges** — https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/route-53-ip-addresses.html
