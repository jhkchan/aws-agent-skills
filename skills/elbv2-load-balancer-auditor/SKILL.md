---
name: elbv2-load-balancer-auditor
description: >-
  Audits AWS ELBv2 load balancers (ALB/NLB) for insecure TLS listener policies
  (TLS 1.0/1.1, weak ciphers, cleartext HTTP), disabled access logs, permissive
  security groups (all-ports-open, internal-LB-exposed-to-internet), idle load
  balancers with zero healthy targets, disabled cross-zone load balancing (NLB),
  and missing deletion protection. Emits a deterministic categorical verdict
  (INSECURE_LISTENER | NO_ACCESS_LOGS | PERMISSIVE_SG | IDLE | CONFIG_GAP | OK)
  per load balancer with enumerated findings and specific CLI remediation. Use
  when reviewing ALB or NLB configurations, checking listener TLS posture,
  validating access-log enablement, auditing security group exposure, finding
  idle or abandoned load balancers, or hardening load balancer posture before
  production deployment.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline config classification. Live-account
  audits use aws elbv2 describe-load-balancers, describe-listeners,
  describe-target-groups, describe-target-health, and describe-tags (AWS CLI v2,
  SSO or key-based credentials).
keywords:
  - ELBv2
  - ALB
  - NLB
  - load balancer
  - TLS
  - SSL policy
  - security policy
  - access logs
  - security group
  - cross-zone
  - deletion protection
  - idle load balancer
  - listener
  - cipher suite
  - TLS 1.0
  - TLS 1.1
  - PCI-DSS
  - ELBSecurityPolicy
  - network exposure
  - load balancer audit
tags: [elbv2, alb, nlb, load-balancer, tls, security-group, networking, audit]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Networking
  verdict_shape: "INSECURE_LISTENER | NO_ACCESS_LOGS | PERMISSIVE_SG | IDLE | CONFIG_GAP | OK"
  when_to_use: >-
    Reviewing an ALB or NLB configuration before production deployment, checking
    listener TLS protocol/cipher posture, validating access-log enablement,
    auditing security group exposure, finding idle or abandoned load balancers,
    checking NLB cross-zone load balancing, or verifying deletion protection.
  activation_triggers:
    - "audit this load balancer"
    - "check ALB TLS policy"
    - "is my NLB secure"
    - "load balancer access logs disabled"
    - "permissive security group ALB"
    - "idle load balancer no targets"
    - "cross-zone load balancing NLB"
    - "deletion protection load balancer"
    - "ELBSecurityPolicy TLS 1.0"
    - "hardening load balancer"
  invocation_schema: >-
    Input: either (a) an ELBv2 load balancer configuration (type, scheme,
    listeners with protocols/SSL policies, security group rules, target group
    health, attributes), OR (b) a load-balancer ARN for live-account audit.
    Output: deterministic LB/VERDICT/REASON/FINDINGS/REMEDIATION block per
    load balancer, where VERDICT is from
    {INSECURE_LISTENER, NO_ACCESS_LOGS, PERMISSIVE_SG, IDLE, CONFIG_GAP, OK}.
---

# ELBv2 Load Balancer Auditor

## Mindset

**One-line takeaway:** the verdict is always the **worst** finding across all
dimensions, and the most dangerous finding is an insecure listener — TLS 1.0/1.1
negotiation means an attacker on the network path can downgrade and decrypt
traffic with BEAST, POODLE, or CRIME-family attacks.

ELBv2 load balancers are the network ingress point for most AWS workloads.
- **TLS termination** happens at the LB for HTTPS/TLS listeners. The
  `SslPolicy` determines which protocol versions and cipher suites clients can
  negotiate. A permissive policy silently accepts a downgrade to TLS 1.0 — the
  client never sees it, and the operator never knows unless they audit the
  policy by name.
- **Access logs** are the forensic trail. Without them, a breach investigation
  has zero request-level signal — no source IPs, no paths, no response codes.
- **Security groups** on an ALB control who can reach the LB. An all-ports-open
  rule on an internet-facing ALB exposes every listener (including future ones)
  to the entire internet.

## Quick reference — verdict priority (worst finding wins)

| Priority | Verdict | Severity | What triggers it | Step |
|---|---|---|---|---|
| 1 | **INSECURE_LISTENER** | CRITICAL | TLS 1.0/1.1 in SslPolicy; weak ciphers; HTTP-only with no HTTPS redirect | Step 1 |
| 2 | **PERMISSIVE_SG** | HIGH | SG open to 0.0.0.0/0 on ports beyond the listener set; all-ports-open | Step 2 |
| 3 | **NO_ACCESS_LOGS** | HIGH | AccessLogsEnabled is false on ALB; access_logs.s3.enabled false on NLB | Step 3 |
| 4 | **IDLE** | MEDIUM | Zero registered targets, or all targets unhealthy | Step 4 |
| 5 | **CONFIG_GAP** | MEDIUM | NLB cross-zone off; deletion protection off (additive) | Step 5 |
| 6 | **OK** | LOW | All dimensions pass | Step 6 |

If multiple findings exist, the **highest-priority** (lowest number) verdict
wins. Additional findings appear in the FINDINGS list but do not change the
verdict.

## Pre-flight: load balancer type gate (run before classification)

The load balancer type determines which checks apply. Misidentifying the type
produces false positives.

| Attribute | Value | Effect on audit |
|---|---|---|
| `Type` | `application` | **ALB.** Full audit: TLS/cipher (Step 1), SG (Step 2), access logs (Step 3), target health (Step 4), deletion protection (Step 5). Cross-zone is **always on** — do NOT evaluate it. |
| `Type` | `network` | **NLB.** TLS/cipher check applies ONLY to TLS-protocol listeners (not TCP passthrough). SG check applies if the NLB has an attached SG (supported since 2023; older NLBs may have none). Cross-zone is **off by default** — evaluate it (Step 5). |
| `Scheme` | `internet-facing` | The LB has public IP addresses. SG allowing 0.0.0.0/0 on ports 80/443 is **expected and OK**. |
| `Scheme` | `internal` | The LB has private IP addresses. SG allowing 0.0.0.0/0 on **any** port is PERMISSIVE_SG — internal LBs should be restricted to known CIDRs (VPC, peered ranges). |
| `State` | `failed` | The LB is in a failed provisioning state. Output ERROR. Do not classify. |

**If the listener/SG/target input is missing or malformed**, output:

```text
LB: <arn>
VERDICT: ERROR
REASON: Load balancer configuration is incomplete or malformed — cannot classify.
REMEDIATION: Retrieve full config with aws elbv2 describe-load-balancers, describe-listeners, describe-target-groups, describe-target-health.
```

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious ELBv2 behaviors that change classification

These behaviors are easy to misjudge without operational ELBv2 experience.
Each changes a verdict if ignored:

- **ALB cross-zone load balancing is ALWAYS ENABLED.** It cannot be disabled.
  Never flag an ALB for cross-zone being off — it is not a configurable
  attribute. Only NLB has the toggle (off by default).

- **ELBSecurityPolicy-2016-08 is the AWS default SslPolicy.** It includes TLS
  1.0 and 1.1, both deprecated by PCI-DSS (3.2.1+, effective 2018) and
  NIST SP 800-52r2. The default policy is insecure by modern standards — most
  production ALBs carry this finding without anyone knowing.

- **NLB TCP (non-TLS) listeners have no SslPolicy.** Traffic passes through
  unencrypted at L4. Do NOT flag a TCP listener for missing TLS — it is by
  design. Only TLS-protocol listeners have an SslPolicy to evaluate. If
  end-to-end encryption is required, the application must handle it.

- **HTTP listener with redirect-to-HTTPS is a SECURE pattern.** The standard
  ALB hardening pattern is HTTP:80 → redirect to HTTPS:443. Do NOT flag an
  HTTP listener that has a redirect action. Only flag an HTTP listener that
  forwards cleartext traffic with no HTTPS listener present.

- **Access logs silently fail if the S3 bucket policy is wrong.** The bucket
  must grant `elasticloadbalancing.amazonaws.com` the `s3:PutObject`
  permission with an `aws:SourceAccount` condition matching the LB owner
  account. AccessLogsEnabled may be `true` but logs never appear. This skill
  checks the `enabled` flag; the bucket-policy check is a live-account
  follow-up (not classifiable from the LB config alone).

- **NLB access logs have a 5-minute delivery granularity minimum.** ALB logs
  are emitted per-request; NLB logs are aggregated in 5-minute windows. A
  low-traffic NLB may produce very few log objects — do not confuse this with
  logs being disabled.

- **Deletion protection blocks delete-load-balancer.** When enabled,
  `aws elbv2 delete-load-balancer` returns
  `OperationNotPermittedException`. Operators who do not know this waste time
  debugging "permission denied" that is actually a safety feature. The
  remediation note must explain: disable deletion protection first, then
  delete.

- **ALB security group controls LB ingress, NOT target ingress.** The ALB SG
  governs client→LB traffic. Target SGs govern LB→target traffic. A common
  misconfiguration is opening the target SG to 0.0.0.0/0 "because the ALB
  handles security" — this exposes targets directly, bypassing the ALB.

- **WAF is ALB-only.** WAFv2 Web ACL association is available for ALB, not
  NLB (NLB is L4). Do not suggest WAF as remediation for an NLB finding.

- **Target group deregistration delay defaults to 300 seconds.** During
  deregistration, targets are in `draining` state — they receive in-flight
  requests but no new ones. An LB with all targets `draining` is effectively
  idle but not flagged as IDLE unless zero targets are `healthy` or
  `unhealthy` (i.e., `unused` or empty).

- **ALB attribute `routing.http.x_amzn_tls_version_and_cipher_suite.enabled`
  is OFF by default.** Without it, access logs show source IP, path, and
  status but NOT the negotiated TLS version or cipher suite. A successful
  downgrade attack (client forced to TLS 1.0) is invisible in the logs —
  the request line is indistinguishable from a TLS 1.3 request. This means
  NO_ACCESS_LOGS understates the forensic gap: even with logs enabled, you
  are TLS-blind unless this attribute is on. Treat a `false` value here as
  an amplifier on any INSECURE_LISTENER finding — without it, you cannot
  reconstruct which requests were downgraded, so the incident-response
  scope is unknowable.

- **NLB default health check is TCP-level, not application-level.**
  `HealthCheckConfig.Type` defaults to `TCP` for NLB target groups — a
  successful TCP handshake marks the target `healthy` even when the
  application is returning 500s or serving the wrong content. A target
  group flagged healthy may be a dead app at L7. This makes the IDLE
  verdict unreliable for NLB unless `health_check.type` is HTTP/HTTPS with
  a real `path`. Always inspect the health-check type before trusting a
  `healthy` status on an NLB target group; a TCP check on an HTTP target
  produces a false non-IDLE verdict (the LB has "healthy" targets that are
  actually broken, and users see 502/503 with no IDLE flag raised).

- **NLB `preserve_client_ip.enabled` defaults differ by listener protocol:
  enabled for TCP, disabled for TLS.** Behind a TLS-terminated NLB, targets
  see the NLB's private IP, not the client IP. IP-based rate limiting,
  geo-blocking, or source-IP audit logging on targets silently breaks when
  migrating a listener from TCP to TLS termination. The target SG must
  allow the NLB subnet CIDR for TLS listeners — not the original client
  CIDRs. A common SG-audit false positive is flagging the target SG for
  "only allowing the NLB subnet" when the fronting listener is TLS: that
  is the *correct* posture for TLS-terminated NLBs, not a permissive gap.

### Step 1: Listener TLS security evaluation — INSECURE_LISTENER

For each listener on the load balancer:

**TLS protocol version check (HTTPS/TLS listeners):**

Classify the `SslPolicy` by known-name lookup first, then by explicit
protocol/cipher list if provided:

**INSECURE policies (include TLS 1.0 or TLS 1.1):**

| Policy name | TLS versions | Notes |
|---|---|---|
| `ELBSecurityPolicy-2015-05` | 1.0, 1.1, 1.2 | Legacy. |
| `ELBSecurityPolicy-2016-08` | 1.0, 1.1, 1.2 | **AWS default.** Most common in production. |
| `ELBSecurityPolicy-TLS-1.0-2015-04` | 1.0, 1.1, 1.2 | Explicitly TLS 1.0. |
| `ELBSecurityPolicy-TLS-1-0-2015-04` | 1.0, 1.1, 1.2 | Same, alternate naming. |
| `ELBSecurityPolicy-FS-1-1-2019-08` | 1.1, 1.2 | Forward Secrecy but TLS 1.1 is deprecated. |

Any listener using one of these policies → **INSECURE_LISTENER** (CRITICAL).

**ACCEPTABLE policies (TLS 1.2+ only, strong ciphers):**

| Policy name | TLS versions | Notes |
|---|---|---|
| `ELBSecurityPolicy-TLS13-1-2-2021-06` | 1.3, 1.2 | **Current best practice.** |
| `ELBSecurityPolicy-TLS13-1-2-Res-2021-06` | 1.3, 1.2 | Resizable cipher (FIPS). |
| `ELBSecurityPolicy-FS-1-2-2019-08` | 1.2 | Forward Secrecy, TLS 1.2 only. |
| `ELBSecurityPolicy-TLS-1-2-2017-01` | 1.2 | TLS 1.2 only (no FS guarantee but acceptable). |
| `ELBSecurityPolicy-TLS-1-2-ext-2018-06` | 1.2 | Extended cipher suites, TLS 1.2 only. |

**Custom policies:** If the SslPolicy name does not match any known policy,
evaluate the explicit `Protocols` and `Ciphers` lists if provided:
- If `Protocol-TLSv1` or `Protocol-TLSv1.1` is in the Protocols → INSECURE.
- If any weak cipher is enabled (RC4-MD5, RC4-SHA, DES-CBC3-SHA, ECDHE-RCA
  variants) → INSECURE.
- If only TLS 1.2+ and AEAD ciphers (GCM, ChaCha20-Poly1305) → OK.

**Cleartext HTTP listener check:**

For each HTTP (non-HTTPS) listener:
- If the listener has a `redirect` action to HTTPS → **OK** for this listener.
- If the listener has a `forward` action and NO HTTPS/TLS listener exists on
  the same LB → **INSECURE_LISTENER** (cleartext traffic with no encrypted
  alternative).
- If the listener has a `forward` action AND an HTTPS/TLS listener exists →
  **OK** (HTTP serves non-sensitive content; HTTPS handles encrypted traffic).

**NLB TCP listener:** No TLS evaluation — skip. The NLB does not terminate
TLS for TCP listeners. If end-to-end encryption is required, note it as an
operational recommendation but do NOT classify as INSECURE_LISTENER.

### Step 2: Security group exposure evaluation — PERMISSIVE_SG

Evaluate each inbound rule on every SG attached to the load balancer.

**CRITICAL — all-ports-open to internet:**
Any SG rule with source `0.0.0.0/0` or `::/0` on port range `0-65535` (or
`all`) → **PERMISSIVE_SG** (CRITICAL). This exposes every current and future
listener to the entire internet.

**HIGH — internet-open on non-listener ports (internet-facing LB):**
For an `internet-facing` LB, a SG rule with source `0.0.0.0/0` or `::/0` on
a port that is NOT one of the listener ports → **PERMISSIVE_SG** (HIGH). The
SG should only expose the ports the listeners actually use.

**HIGH — internet-open on any port (internal LB):**
For an `internal` LB, ANY SG rule with source `0.0.0.0/0` or `::/0` →
**PERMISSIVE_SG** (HIGH). Internal LBs should only be reachable from known
CIDRs (VPC ranges, peered networks, VPN).

**OK — internet-facing LB with 0.0.0.0/0 on listener ports only:**
For an `internet-facing` ALB with listeners on ports 80 and 443, SG rules
allowing `0.0.0.0/0` on TCP 80 and TCP 443 → **OK**. This is the expected
posture for a public-facing load balancer.

### Step 3: Access logs evaluation — NO_ACCESS_LOGS

**ALB:** Check `LoadBalancerAttributes` for
`access_logs.s3.enabled`. If `false` (or absent) → **NO_ACCESS_LOGS** (HIGH).
Access logs are the only per-request forensic signal for an ALB — without
them, incident response cannot reconstruct source IPs, request paths, or
response codes.

**NLB:** Check `LoadBalancerAttributes` for
`access_logs.s3.enabled`. Same logic as ALB. NLB access logs capture
connection-level telemetry (source IP, port, TLS handshake details for TLS
listeners).

**If enabled:** OK for this dimension. Note: the S3 bucket policy must
correctly grant the ELB service principal write access — if logs are enabled
but the bucket policy is wrong, logs silently fail. This is a live-account
follow-up, not classifiable from the LB config alone.

### Step 4: Target health and idle evaluation — IDLE

Check each target group associated with the load balancer via listener
default actions or rules.

**IDLE — zero registered targets:**
If every target group has zero registered targets (TargetHealthDescriptions
is empty or all targets are in `unused` state) → **IDLE** (MEDIUM). The LB
is accepting traffic on its listeners but has nowhere to send it — clients
receive 502 (Bad Gateway) or 503 (Service Unavailable). This is typically a
forgotten LB from a decommissioned service.

**IDLE — all targets unhealthy:**
If every registered target across all target groups is `unhealthy` → **IDLE**
(MEDIUM). The LB is live but not serving traffic. This may be a transient
outage (health-check failure) or a permanently broken deployment.

**OK — at least one healthy target:**
If at least one target group has at least one `healthy` target → OK for this
dimension.

### Step 5: Configuration best practices — CONFIG_GAP

These are additive findings that do not override higher-priority verdicts but
are reported in the FINDINGS list.

**NLB cross-zone load balancing disabled:**
If the LB type is `network` and `load_balancing.cross_zone.enabled` is `false`
→ CONFIG_GAP finding. Cross-zone off means traffic is distributed per-AZ,
which can lead to uneven distribution if one AZ has more capacity than
another. Enabling it incurs inter-AZ data transfer charges but improves
availability and distribution. Note: ALB cross-zone is always on — never
evaluate this for ALB.

**Deletion protection disabled:**
If `deletion_protection.enabled` is `false` → CONFIG_GAP finding. Without
deletion protection, `aws elbv2 delete-load-balancer` succeeds without a
second confirmation. An accidental deletion (script error, IaC teardown)
destroys the LB and all listener/rule configurations — there is no undo.

**HTTP desync mitigation mode not strict (ALB only):**
If `routing.http.desync_mitigation_mode` is `monitor` → CONFIG_GAP finding.
Monitor mode logs HTTP request smuggling attempts but does not block them.
`defensive` (default) or `strict` is recommended for production.

If none of these apply → OK for this dimension.

### Step 6: Aggregation — worst finding wins

The final verdict is the **highest-priority** finding across all steps, where
INSECURE_LISTENER > PERMISSIVE_SG > NO_ACCESS_LOGS > IDLE > CONFIG_GAP > OK:

```text
verdict = first_match(Step1, Step2, Step3, Step4, Step5, OK)
```

If no findings (all dimensions pass), the verdict is **OK**.

## Output format (per load balancer)

```text
LB: <arn or name>
VERDICT: INSECURE_LISTENER | NO_ACCESS_LOGS | PERMISSIVE_SG | IDLE | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its step number>
FINDINGS:
  - [CRITICAL] <finding description (Step N)>
  - [HIGH] <finding description (Step N)>
  - [OK] <dimension that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — TLS 1.0 policy with access logs disabled

```text
LB: arn:aws:elasticloadbalancing:us-east-1:111111111111:load-balancer/app/prod-web/abc123
VERDICT: INSECURE_LISTENER
REASON: HTTPS listener on port 443 uses ELBSecurityPolicy-TLS-1.0-2015-04
which enables TLS 1.0/1.1 — traffic is vulnerable to protocol-downgrade
attacks (Step 1). Access logs are also disabled (Step 3).
FINDINGS:
  - [CRITICAL] HTTPS:443 SslPolicy ELBSecurityPolicy-TLS-1.0-2015-04 includes
    TLS 1.0/1.1 — deprecated by PCI-DSS, vulnerable to BEAST/POODLE (Step 1)
  - [HIGH] Access logs disabled — no per-request forensic trail for incident
    response (Step 3)
  - [OK] Security group allows 0.0.0.0/0 only on port 443 — expected for
    internet-facing ALB (Step 2)
REMEDIATION:
  1. CRITICAL — Update the listener SslPolicy:
     aws elbv2 modify-listener --listener-arn <arn> \
       --ssl-policy ELBSecurityPolicy-TLS13-1-2-2021-06
  2. HIGH — Enable access logs:
     aws elbv2 modify-load-balancer-attributes --load-balancer-arn <arn> \
       --attributes Key=access_logs.s3.enabled,Value=true \
       Key=access_logs.s3.bucket,Value=<bucket> \
       Key=access_logs.s3.prefix,Value=<prefix>
```

## Anti-Patterns — NEVER

- NEVER flag an ALB for cross-zone load balancing being disabled. Cross-zone
  is **always enabled** for ALB — it is not a configurable attribute. Only
  NLB has the toggle (off by default). Flagging ALB cross-zone is a false
  positive that erodes trust.

- NEVER flag a TCP listener on an NLB for "missing TLS." TCP is a
  passthrough protocol — the NLB does not terminate TLS for TCP listeners.
  Only TLS-protocol listeners have an SslPolicy to evaluate. If
  end-to-end encryption is required, note it as a recommendation, not a
  finding.

- NEVER flag an HTTP:80 listener with a redirect-to-HTTPS action as
  insecure. The redirect pattern (HTTP→HTTPS) is the **standard secure
  hardening** for ALB. Only flag an HTTP listener that forwards cleartext
  with no HTTPS alternative on the same LB.

- NEVER flag `0.0.0.0/0` on ports 80 and/or 443 for an `internet-facing` ALB.
  This is the **expected posture** — the ALB must accept traffic from the
  internet on its listener ports. Only flag 0.0.0.0/0 on non-listener ports
  or on all ports (0-65535).

- NEVER assume `ELBSecurityPolicy-2016-08` is secure because it is the AWS
  default. It includes TLS 1.0 and 1.1, both deprecated by PCI-DSS since
  2018. The default is insecure by modern standards. Always classify it as
  INSECURE_LISTENER.

- NEVER recommend WAF as remediation for an NLB finding. WAFv2 Web ACL
  association is available for ALB only — NLB operates at Layer 4 and cannot
  inspect HTTP payloads.

- NEVER classify an LB as IDLE if at least one target group has at least one
  `healthy` target. A single healthy target means the LB is serving traffic.
  Only flag IDLE when all target groups have zero registered targets or all
  targets are `unhealthy`.

- NEVER assume access logs are working just because `access_logs.s3.enabled`
  is `true`. The S3 bucket policy must grant `elasticloadbalancing.amazonaws.com`
  the `s3:PutObject` permission with `aws:SourceAccount` condition. A
  misconfigured bucket policy causes logs to silently fail — the attribute
  says enabled but no log objects ever appear. Always verify with a live
  bucket-policy check.

- NEVER recommend enabling deletion protection without explaining the
  trade-off. Deletion protection prevents accidental deletion (good) but also
  blocks `delete-load-balancer` with `OperationNotPermittedException` until
  explicitly disabled (can confuse operators). State both sides.

- NEVER evaluate TLS cipher suites on a custom SslPolicy without checking the
  explicit Protocols list. A policy name you do not recognize may be a
  customer-managed custom policy with TLS 1.2+ only — or it may include TLS
  1.0. Always check `Protocols` and `Ciphers` if provided.

- NEVER conflate ALB and NLB security group models. ALB has its own SG
  attached to the LB. NLB may or may not have an SG (pre-2023 NLBs have none;
  the target SGs control access). Applying ALB SG logic to an NLB without an
  attached SG produces a false negative.

- NEVER assume access logs are being delivered just because
  `access_logs.s3.enabled` is `true`. The S3 bucket policy MUST grant
  `elasticloadbalancing.amazonaws.com` the `s3:PutObject` permission with an
  `aws:SourceAccount` (or `aws:SourceArn`) condition matching the LB owner
  account. A missing or incorrect bucket policy causes logs to silently fail
  — the attribute says enabled but no log objects ever appear in S3. Always
  verify with `aws s3 ls` on the prefix after 5-10 minutes.

- NEVER trust an NLB `healthy` status without verifying
  `health_check.type`. The default TCP health check succeeds on a bare TCP
  handshake — an application returning 500s or serving wrong content is
  marked `healthy`. For HTTP/HTTPS target groups, require
  `health_check.type` = HTTP/HTTPS with a real `path`; a TCP check on an
  HTTP target produces a false-negative IDLE verdict (the LB appears to
  have healthy targets, but the app is broken and users see 502/503 with
  no IDLE flag raised). This is the most common cause of "healthy but
  down" incidents on NLB-fronted services.

- NEVER assume the target group's default `Port` is the port targets
  actually listen on. `register-targets` accepts a per-target `Port`
  override that can differ from the group default — a target registered on
  the wrong port passes the health check (which uses the group port) but
  fails under real traffic, producing intermittent 502s. When auditing
  live targets, list `TargetHealthDescriptions` and compare each target's
  registered port to the group `Port`; a mismatch is a CONFIG_GAP finding,
  not an IDLE finding.

- NEVER conflate deregistration delay with unhealthy-threshold timing. If
  `health_check.interval_seconds * unhealthy_threshold_count` exceeds the
  deregistration delay, a failing target may be deregistered (after
  draining) BEFORE the health check marks it `unhealthy` — the LB sends
  traffic to a dying target throughout the gap. Conversely, if the
  product is shorter than the delay, a target flaps in and out of
  rotation during deploys. Always verify the timing relationship as part
  of a CONFIG_GAP finding on target groups with non-default dereg delay.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (modify-listener, modify-load-balancer-attributes, delete-load-balancer),
  the auditor MUST emit:
  `CONFIRM: About to <action> on LB <arn>. This affects <consequence>.
  Proceed? (yes/no)`
  Do NOT execute the CLI command until the operator confirms.

- **SslPolicy change validation.** Before modifying a listener SslPolicy,
  verify the new policy is compatible with the listener protocol:
  `aws elbv2 describe-listener-attributes --listener-arn <arn>`. Changing
  the SslPolicy on a live listener immediately renegotiates TLS for all new
  connections — clients with old cipher suites may be disconnected.

- **Access-log enablement requires a valid S3 bucket.** Before enabling
  access logs, verify the bucket exists and has the correct policy granting
  `elasticloadbalancing.amazonaws.com` write access with `aws:SourceAccount`
  condition. Enabling logs on a non-existent bucket silently fails.

- **Deletion protection toggle is a two-step process.** To delete an LB with
  deletion protection: (1) disable deletion protection, (2) delete the LB.
  Attempting to delete without disabling returns
  `OperationNotPermittedException`.

- **Target group health check after changes.** After modifying listeners or
  target groups, verify target health:
  `aws elbv2 describe-target-health --target-group-arn <arn>`. A
  configuration change can cause health-check failures that take minutes to
  surface.

## Remediation guidance

### For INSECURE_LISTENER — TLS 1.0/1.1 policy (Step 1)

1. Update the listener SslPolicy to a TLS 1.2+ policy:
   ```bash
   aws elbv2 modify-listener --listener-arn <arn> \
     --ssl-policy ELBSecurityPolicy-TLS13-1-2-2021-06 --profile <p>
   ```
2. Verify the new policy is applied:
   ```bash
   aws elbv2 describe-listeners --listener-arns <arn> \
     --query 'Listeners[0].SslPolicy' --profile <p>
   ```
3. Test with an external TLS scanner (ssllabs.com, testssl.sh) to confirm no
   client can negotiate TLS 1.0 or 1.1.

### For INSECURE_LISTENER — HTTP-only with no HTTPS (Step 1)

1. Add an HTTPS listener on port 443 with a TLS 1.2+ SslPolicy and an ACM
   certificate.
2. Change the HTTP:80 listener to redirect to HTTPS:
   ```bash
   aws elbv2 modify-listener --listener-arn <http-arn> \
     --default-actions Type=redirect,RedirectConfig.Protocol=HTTPS,\
   RedirectConfig.Port=443,RedirectConfig.StatusCode=HTTP_301 --profile <p>
   ```

### For PERMISSIVE_SG — over-exposed security group (Step 2)

1. Identify the listener ports the LB actually uses (e.g., 80, 443).
2. Remove SG rules that open non-listener ports to 0.0.0.0/0:
   ```bash
   aws ec2 revoke-security-group-ingress --group-id <sg-id> \
     --ip-permissions IpProtocol=tcp,FromPort=0,ToPort=65535,\
   IpRanges=[{CidrIp=0.0.0.0/0}] --profile <p>
   ```
3. Add SG rules scoped to the exact listener ports:
   ```bash
   aws ec2 authorize-security-group-ingress --group-id <sg-id> \
     --ip-permissions IpProtocol=tcp,FromPort=443,ToPort=443,\
   IpRanges=[{CidrIp=0.0.0.0/0}] --profile <p>
   ```
4. For internal LBs, replace 0.0.0.0/0 with the VPC CIDR or known ranges.

### For NO_ACCESS_LOGS — access logs disabled (Step 3)

1. Create or identify an S3 bucket with the correct policy granting
   `elasticloadbalancing.amazonaws.com` write access.
2. Enable access logs:
   ```bash
   aws elbv2 modify-load-balancer-attributes --load-balancer-arn <arn> \
     --attributes Key=access_logs.s3.enabled,Value=true \
     Key=access_logs.s3.bucket,Value=<bucket> \
     Key=access_logs.s3.prefix,Value=<prefix> --profile <p>
   ```
3. Verify log delivery after 5–10 minutes by listing the S3 prefix.

### For IDLE — zero healthy targets (Step 4)

1. Determine whether the LB is still needed:
   `aws elbv2 describe-tags --resource-arns <arn>` — check for ownership tags.
2. If the LB is abandoned, delete it (disable deletion protection first if
   enabled):
   ```bash
   aws elbv2 modify-load-balancer-attributes --load-balancer-arn <arn> \
     --attributes Key=deletion_protection.enabled,Value=false --profile <p>
   aws elbv2 delete-load-balancer --load-balancer-arn <arn> --profile <p>
   ```
3. If the LB is needed but targets were deregistered by accident, re-register:
   ```bash
   aws elbv2 register-targets --target-group-arn <tg-arn> \
     --targets Id=<instance-id>,Port=<port> --profile <p>
   ```

### For CONFIG_GAP — cross-zone off (NLB, Step 5)

```bash
aws elbv2 modify-load-balancer-attributes --load-balancer-arn <arn> \
  --attributes Key=load_balancing.cross_zone.enabled,Value=true --profile <p>
```
Note: enabling cross-zone on NLB incurs inter-AZ data transfer charges.

### For CONFIG_GAP — deletion protection off (Step 5)

```bash
aws elbv2 modify-load-balancer-attributes --load-balancer-arn <arn> \
  --attributes Key=deletion_protection.enabled,Value=true --profile <p>
```

### For OK

No remediation required for the current posture. Recommend:
- Periodic SslPolicy review as AWS releases new policies.
- Verify the S3 bucket policy for access logs is intact (log-delivery
  silent-failure check).
- For ALB: associate a WAFv2 Web ACL for defense-in-depth (ALB only).

## Deep reference: ELBv2 TLS security policy catalog

### How SslPolicy negotiation works

When a TLS client connects to an ALB or NLB TLS listener, the LB selects the
highest mutually supported protocol version and cipher suite from the
SslPolicy. If the policy includes TLS 1.0, a client that only supports TLS 1.0
will negotiate TLS 1.0 — the server cannot force an upgrade. This is why
including TLS 1.0/1.1 in the policy is dangerous even if modern clients use
1.2+: an attacker performing a downgrade attack can force the weaker protocol.

### ELBSecurityPolicy naming convention

- `FS` prefix: Forward Secrecy (all cipher suites provide PFS via ECDHE/DHE).
- `TLS13` prefix: includes TLS 1.3 cipher suites.
- `TLS-1-2` / `TLS-1-0`: indicates the minimum TLS version.
- `Res` suffix: resizable cipher suite (for FIPS 140-2 compliance).
- `Ext` suffix: extended compatibility (includes broader cipher set).

### ALB vs NLB TLS termination

- **ALB HTTPS listener:** Terminates TLS at the ALB. The SslPolicy controls
  client→ALB negotiation. Backend traffic (ALB→target) uses the target group
  protocol (HTTP or HTTPS) — a separate encryption decision.
- **NLB TLS listener:** Terminates TLS at the NLB. Same SslPolicy model as
  ALB. Backend traffic can be re-encrypted (TLS to target) or plaintext.
- **NLB TCP listener:** No TLS termination. Traffic passes through at L4.
  No SslPolicy to evaluate. The application must handle encryption.

### Operational edge cases (deep reference)

These are production-experience insights that affect remediation ordering and
post-remediation validation, but do not change the verdict classification:

- **SslPolicy modification only affects NEW TLS handshakes.** Existing
  connections keep their negotiated parameters until closed. After updating a
  TLS 1.0 policy, an attacker with an active TLS 1.0 session retains it until
  TCP close or idle timeout. Incident-response for INSECURE_LISTENER must
  include force-closing existing connections (temporarily lower the idle
  timeout or cycle the listener), not just updating the policy.

- **TLS 1.3 cipher suites are protocol-fixed, not SslPolicy-controlled.**
  When an ELBSecurityPolicy-TLS13-* policy is used, TLS 1.3 cipher negotiation
  follows RFC 8446 — the policy cipher list applies only to TLS 1.2 and below.
  A TLS 1.3-capable client always gets a strong cipher regardless of the
  policy's TLS 1.2 cipher ordering. But a TLS 1.2-only client falls back to
  the policy's 1.2 cipher list — so weak 1.2 ciphers in a TLS13 policy are
  still a finding.

- **ALB idle timeout (60s default) cascades to backend connections.** The
  timeout applies to BOTH frontend (client→ALB) and backend (ALB→target)
  connections. If the target's keep-alive exceeds 60s, the ALB sends a TCP
  RST — the application sees a connection error, not a clean close.
  Long-polling or WebSocket workloads need the timeout raised to match the
  target's keep-alive.

- **Health-check interval vs deregistration delay timing.** If
  `health_check.interval_seconds * unhealthy_threshold_count` exceeds the
  deregistration delay, a failing target may be deregistered before the health
  check marks it unhealthy. The LB continues sending traffic to the failing
  target during the gap. Always verify the timing relationship.

- **Multiple ALBs sharing the same S3 access-log prefix produce interleaved
  logs.** The S3 path includes the LB ARN hash, but the user-controlled prefix
  is the primary organizational key. Each ALB should have a unique prefix
  (e.g., `prod-web`, `prod-api`) to avoid log collision.

- **NLB static IPs vs ALB dynamic IPs.** NLB provides one static IP per AZ
  that never changes for the LB's lifetime. ALB IPs can change when the ALB
  scales. NLB is the only choice when static IPs are required — but migrating
  ALB→NLB loses WAF, content-based routing, and HTTP-level features.

## Recent AWS features (2024-2026)

- **TLS 1.3 support on ALB (2024):** ALB now supports TLS 1.3 for listener connections. Auditors should verify that the security policy is updated to include TLS 1.3 while maintaining a minimum of TLS 1.2.
- **mTLS on NLB (2024-2025):** NLB now supports mutual TLS (mTLS) for TCP listeners. Auditors should verify that mTLS is enabled on NLBs fronting internal APIs and that certificate revocation checking is configured.
- **ALB routing enhancements (2024):** Weighted routing, hostname-based routing, and query-string-based routing improvements. No new audit-surface fields, but auditors should verify that routing rules do not inadvertently bypass WAF rules on specific paths.
- **Capacity reservations integration:** ALB integration with Capacity Reservations for more predictable scaling. No direct audit-surface change.

## Domain

AWS CloudOps / ELBv2 Load Balancer Security & Compliance.
