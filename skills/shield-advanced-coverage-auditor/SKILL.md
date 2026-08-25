---
name: shield-advanced-coverage-auditor
description: Audits AWS Shield Advanced coverage posture — protected-resource coverage (CloudFront/Route 53 auto-protection, ALB/NLB/CLB/EIP/EC2 explicit protection), DDoS Response Team (DRT) role and log-bucket access, health-based detection per protection, proactive engagement and emergency contact list, and WAF Web ACL integration for L7 mitigation. Emits a deterministic verdict (UNPROTECTED | NO_DRT_ACCESS | CONFIG_GAP | OK) with enumerated findings and specific remediation. Use when reviewing Shield Advanced coverage, checking which internet-facing resources are protected, validating DRT access, auditing health-based detection, or hardening DDoS posture before a launch or after an incident.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline config-document classification. Live-account audits use aws shield get-subscription-state, aws shield list-protections, aws shield describe-drt-access, aws shield describe-emergency-contact-settings, and aws wafv2 get-web-acl (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Security
  verdict_shape: UNPROTECTED | NO_DRT_ACCESS | CONFIG_GAP | OK
  when_to_use: Reviewing Shield Advanced coverage before a public launch, checking which internet-facing resources (ALB, NLB, CLB, EIP, CloudFront, Route 53) are protected, validating DRT role and log-bucket access, auditing health-based detection wiring, verifying proactive engagement and emergency contacts, or hardening DDoS posture after an incident.
  activation_triggers: audit Shield Advanced coverage, is my ALB protected by Shield Advanced, check DRT access, is proactive engagement enabled, Shield Advanced health-based detection, which resources are DDoS protected, Shield Advanced subscription state, DDoS response team access, harden DDoS posture
  invocation_schema: 'Input — one of: (a) config_snapshot object with keys: subscription_state (ACTIVE|INACTIVE), resource_inventory (list of {type, arn}), protections (list of {id, name, resource_arn, health_check_ids}), drt_access ({role_arn, log_buckets}), proactive_engagement (ENABLED|DISABLED), emergency_contact_list (list), web_acls (list of {resource_arn, web_acl_arn}); OR (b) account_id (string) for live-account audit. Output — deterministic block: SCOPE (string), VERDICT (enum: UNPROTECTED|NO_DRT_ACCESS|CONFIG_GAP|OK|ERROR), REASON (string), FINDINGS (list of {severity, description, step}), REMEDIATION (list of strings, one per finding).'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Shield Advanced, DDoS protection, DRT, DDoS Response Team, Shield Standard, proactive engagement, health-based detection, Route 53 health check, CreateProtection, AssociateDRTRole, AssociateDRTLogBucket, EnableProactiveEngagement, EmergencyContactList, WAF Web ACL, L7 mitigation, CloudFront auto-protection, Elastic IP protection, cost protection, CreateSubscription, application layer automatic response
  tags: shield, security, ddos, drt, waf, cloudfront, route53, alb, eip, coverage, audit
---

# Shield Advanced Coverage Auditor

## Mindset

**One-line takeaway:** the verdict is always the **worst** finding across
all dimensions, ordered UNPROTECTED > NO_DRT_ACCESS > CONFIG_GAP > OK — and
two resources (CloudFront, Route 53) are **auto-protected** by Shield
Advanced, so flagging their absence from the Protections list is the most
common false positive.

Shield Advanced is the paid tier of AWS Shield (Standard is free, L3/L4
only). The coverage audit answers one question: **is every internet-facing
resource in this account getting the full Shield Advanced value?** Three
dimensions define "full value":

- **Coverage** — every ALB/NLB/CLB and EIP-backed EC2 instance has an
  explicit Protection (CloudFront and Route 53 are auto-protected).
- **DRT access** — the DDoS Response Team can assume a role AND read access
  logs to create targeted WAF mitigations during an attack.
- **Detection + engagement** — health-based detection is wired so Shield
  sees L7 application-layer attacks, and proactive engagement is enabled so
  the DRT calls you before you call them.

A resource with Shield Standard only is behind the first line of defence but
NOT behind Shield Advanced's enhanced detection, DRT manual mitigation, or
cost-protection credits. That gap is what this auditor catches.

## Quick-start — the audit in 7 steps

For agents that need the high-level flow before reading the detail:

1. **Subscription gate** — INACTIVE = UNPROTECTED, stop.
2. **Coverage** — every ALB/NLB/CLB/EIP must have a Protection with matching `ResourceArn`. CloudFront + Route 53 are auto-protected (do NOT flag).
3. **DRT access** — no RoleArn = NO_DRT_ACCESS. RoleArn but no LogBuckets = CONFIG_GAP.
4. **Health-based detection** — each explicit Protection needs `HealthCheckIds`. Empty = CONFIG_GAP.
5. **Proactive engagement** — ENABLED + populated contacts = OK. Anything else = CONFIG_GAP.
6. **WAF + automatic response** — each ALB Protection needs a WAF Web ACL; verify Application Layer Automatic Response is enabled on critical ALBs.
7. **Aggregate** — worst verdict wins: UNPROTECTED > NO_DRT_ACCESS > CONFIG_GAP > OK.

Paginate `ListProtections` to completion (100/page cap). Audit each region independently. Full threshold table, expert gotchas, and edge cases follow.

## Quick reference — verdict thresholds

| Condition | Verdict | Rule |
|---|---|---|
| Any ALB/NLB/CLB/EIP not in Protections list | **UNPROTECTED** | Step 2 |
| Subscription state INACTIVE (no active Shield Advanced) | **UNPROTECTED** | Step 1 |
| DRT RoleArn absent (DRT cannot act on your behalf) | **NO_DRT_ACCESS** | Step 3a |
| Protection exists but HealthCheckIds empty (L7 blind) | **CONFIG_GAP** | Step 4 |
| DRT role present but LogBuckets empty (DRT blind to logs) | **CONFIG_GAP** | Step 3b |
| Proactive engagement DISABLED | **CONFIG_GAP** | Step 5 |
| Proactive engagement ENABLED but EmergencyContactList empty | **CONFIG_GAP** | Step 5 |
| ALB protection has no WAF Web ACL (L3/L4 only) | **CONFIG_GAP** | Step 6 |
| ALB has WAF but Application Layer Automatic Response disabled | **CONFIG_GAP** (advisory) | Step 6b |
| All resources covered + DRT role+logs + health checks + proactive + WAF + auto-response | **OK** | Step 7 |
| CloudFront distribution or Route 53 zone NOT in Protections list | **OK** (auto-protected — do NOT flag) | Step 0a |

See the ordered steps below for edge cases. Deep Shield Advanced internals
(DRT workflow, cost-protection eligibility, automatic L7 response) are in
the [Deep reference](#deep-reference-shield-advanced-internals) section.

## Pre-flight: subscription gate (run before coverage classification)

Before evaluating protections, classify the subscription state. Several
states **short-circuit** the audit — misclassifying them produces false
positives that erode trust.

**Live-account pre-flight (skip if doing offline config-doc audit):**
1. Verify the caller can run `shield:ListProtections` and
   `shield:DescribeDRTAccess` — most read-only auditor roles CAN, but
   `shield:AssociateDRTRole` (remediation) requires write access. Surface
   this BEFORE the operator approves a change.
2. Snapshot `aws shield list-protections` and
   `aws wafv2 list-web-acls --scope regional` (and `--scope cloudfront` for
   global ACLs) BEFORE any edit — protections and Web ACL associations are
   not versioned; a backup is the only rollback.
3. Confirm the region: Shield Advanced is a global service for CloudFront
   and Route 53, but ALB/NLB/CLB/EIP protections are regional. Audit each
   region independently — a clean us-east-1 does NOT imply clean eu-west-1.

| Attribute | Value | Effect on audit |
|---|---|---|
| `SubscriptionState` | `ACTIVE` | Proceed with full audit. |
| `SubscriptionState` | `INACTIVE` | **No active Shield Advanced.** No protections, no DRT, no auto-protection for CloudFront/Route 53. Emit UNPROTECTED (Step 1). Do NOT proceed to Steps 2-6 — every resource is behind Shield Standard only. |
| Resource type | `CLOUDFRONT` | **Auto-protected.** Do NOT require an entry in the Protections list. Flagging absence is a false positive (Step 0a). |
| Resource type | `ROUTE53_HOSTEDZONE` | **Auto-protected.** Same as CloudFront. |
| Resource type | `ELASTIC_IP_ALLOCATION` | **Explicit protection required.** Check Protections list for matching EIP allocation ARN. |
| Resource type | `APPLICATION_LB` / `NETWORK_LB` / `CLASSIC_LB` | **Explicit protection required.** Check Protections list for matching LB ARN. |
| Resource type | `EC2_INSTANCE` (private IP only) | **Not internet-facing.** Skip — cannot be DDoS-attacked from the internet. |

**If the input configuration is malformed** (missing SubscriptionState,
Protections not a list, DRT config absent entirely), output:

```text
SCOPE: <account-id>
VERDICT: ERROR
REASON: Shield Advanced configuration snapshot is incomplete or malformed — cannot classify.
REMEDIATION: Re-fetch with aws shield get-subscription-state, aws shield list-protections, and aws shield describe-drt-access.
```

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious behaviors that change classification

These behaviors cause false positives or silent failures if ignored. Each
is explained in depth in [Deep reference: Shield Advanced
internals](#deep-reference-shield-advanced-internals); the one-liner here
is the classification-impacting summary.

- **CloudFront + Route 53 are AUTO-PROTECTED** (re:Invent 2023). Flagging
  their absence from the Protections list is the #1 false positive.
- **DRT needs BOTH a role AND log-bucket access.** No role = NO_DRT_ACCESS.
  Role but no log bucket = CONFIG_GAP (blind, not helpless).
- **Proactive engagement needs EnableProactiveEngagement AND a populated
  EmergencyContactList.** ENABLED with empty contacts = CONFIG_GAP.
- **Health-based detection is PER-PROTECTION.** Missing = CONFIG_GAP and
  disqualifies cost-protection credits.
- **WAF Web ACL is required for L7 mitigation.** ALB Protection without
  WAF = CONFIG_GAP (L3/L4 only).
- **Application Layer Automatic Response** (2023 GA) auto-tunes WAF rules
  without DRT — verify it on critical ALBs (requires WAF Web ACL).
- **`ListProtections` caps at 100/page** — paginate with `NextToken` or
  silently miss Protections on page 2+.
- **Match on `ResourceArn`, never `Name`** — Name is not unique; ARN is.
- **DRT role trust policy needs `service-role.shield.amazonaws.com`** —
  `shield.amazonaws.com` fails silently at incident time.
- **`AssociateHealthCheck` is write-only** — verify associations via
  `DescribeProtection`, not `route53 list-health-checks`.
- **EIP Protection uses allocation ID** (`eipalloc-xxx`), not public IP.
- **Subscription auto-renews** — 1-year term, non-prorated, silent renewal.

### Step 1: Subscription gate (highest priority — no subscription = no coverage)

If `SubscriptionState` is `INACTIVE`:

- **UNPROTECTED.** No active Shield Advanced means zero enhanced
  protections across the entire account. CloudFront and Route 53 fall back
  to Shield Standard (L3/L4 only). ALB/NLB/CLB/EIP have no Protection
  objects. DRT access is moot. This is the first check because every
  downstream dimension depends on an active subscription.

Emit UNPROTECTED and STOP — do not proceed to Steps 2-6 for an account
without a subscription. The remediation is `aws shield create-subscription`
(which starts the 1-year commitment — flag this in the confirmation gate).

### Step 2: Resource coverage classification

For each internet-facing resource in the inventory, classify coverage:

| Resource type | Coverage rule | If missing from Protections |
|---|---|---|
| CloudFront distribution | **AUTO_PROTECTED** (Step 0a) | OK — do NOT flag |
| Route 53 hosted zone | **AUTO_PROTECTED** (Step 0a) | OK — do NOT flag |
| ALB (Application Load Balancer) | Needs explicit Protection with matching ResourceArn | **UNPROTECTED** |
| NLB (Network Load Balancer) | Needs explicit Protection | **UNPROTECTED** |
| CLB (Classic Load Balancer) | Needs explicit Protection | **UNPROTECTED** |
| Elastic IP (associated with EC2) | Needs explicit Protection with EIP allocation ARN | **UNPROTECTED** |
| EC2 instance (private IP only) | Not internet-facing | Skip — not in scope |

If ANY ALB/NLB/CLB/EIP is NOT in the Protections list → worst verdict so
far is **UNPROTECTED**.

**Matching rule:** a Protection covers a resource if the Protection's
`ResourceArn` matches the resource's ARN exactly. Partial matches (same
name, different ARN) do NOT count — re-created resources get new ARNs. When
in doubt, `aws shield describe-protection --protection-id <id>` returns the
exact `ResourceArn`.

### Step 3: DRT access evaluation

Evaluate DRT configuration for full incident-response capability. The
**critical distinction** is: NO_DRT_ACCESS means the DRT has NO role and
CANNOT ACT AT ALL; CONFIG_GAP means the DRT HAS a role and CAN act, but is
missing log-bucket access (blind to attack patterns). If the DRT has a
role, it is NEVER NO_DRT_ACCESS — even without a log bucket, the DRT can
still assume the role and create WAF rules.

**Decision branch (apply first):**
1. Is `RoleArn` present (not null)? If NO → **NO_DRT_ACCESS** (regardless
   of LogBuckets — without a role the DRT cannot act; a log bucket alone is
   non-functional). STOP.
2. If RoleArn IS present: Are `LogBuckets` populated? If NO →
   **CONFIG_GAP** (partial DRT — the DRT can act but is blind to log-level
   attack patterns). If YES → **OK** (full DRT capability).

| DRT state | Verdict | Reason |
|---|---|---|
| RoleArn absent (null) | **NO_DRT_ACCESS** | DRT has NO role — cannot assume anything, cannot act at all. No manual mitigation is possible during an attack. LogBuckets are irrelevant without a role. |
| RoleArn present + LogBuckets empty | **CONFIG_GAP** | DRT HAS a role and CAN act (create WAF rules, mitigate attacks) but is BLIND to attack patterns in access logs (ALB/CloudFront logs). This is PARTIAL DRT, NOT no-DRT — the DRT can still mitigate, just less effectively. |
| RoleArn present + LogBuckets populated | **OK** (this dimension) | Full DRT capability — can act AND analyze logs. |

**Severity rationale:** NO_DRT_ACCESS is reserved for the case where the
DRT has NO role at all — the DRT cannot assume anything and the entire
manual mitigation path is lost. This is fundamentally different from
CONFIG_GAP (role present, log bucket absent), where the DRT CAN still
create WAF rules and mitigate attacks — it just lacks log visibility. The
difference is "cannot help at all" (NO_DRT_ACCESS) vs "can help but blind"
(CONFIG_GAP).

### Step 4: Health-based detection evaluation

For each explicit Protection (ALB/NLB/CLB/EIP — NOT CloudFront/Route 53
auto-protections), check `HealthCheckIds`:

- **HealthCheckIds populated** → OK for this protection. Shield can detect
  L7 application-layer degradation (increased latency, 5xx rate) via the
  Route 53 health check and correlate it with traffic spikes.
- **HealthCheckIds empty** → **CONFIG_GAP** for this protection. Shield
  relies only on L3/L4 volumetric thresholds. Slow-and-low L7 attacks
  (HTTP flood without bandwidth spike) go undetected. This also
  disqualifies the resource from cost-protection credits.

If ANY protection lacks a health check → CONFIG_GAP (at minimum).

**Expert note:** CloudFront and Route 53 auto-protections do NOT support
per-resource health check association via `AssociateHealthCheck`. They use
Shield's built-in health detection. Do NOT flag CloudFront/Route 53 for
missing HealthCheckIds — that is a false positive.

### Step 5: Proactive engagement evaluation

Evaluate whether the DRT will proactively contact you during a suspected
event:

| Proactive engagement state | EmergencyContactList | Verdict |
|---|---|---|
| ENABLED | Populated (>= 1 contact) | OK (this dimension) |
| ENABLED | Empty | **CONFIG_GAP** — DRT cannot reach you |
| DISABLED | Populated | **CONFIG_GAP** — DRT will not proactively engage |
| DISABLED | Empty | **CONFIG_GAP** — no proactive engagement AND no contacts |

**Severity rationale:** Proactive engagement is the difference between the
DRT calling you within minutes of a detected event versus you noticing the
outage hours later and opening a support case. Both DISABLED and
ENABLED-without-contacts produce the same operational gap.

### Step 6: WAF L7 integration evaluation

For each ALB protection (ALB is the primary L7 resource; NLB/CLB are
L4/Layer-balanced):

- **ALB has associated WAF Web ACL** (`WebACLArn` populated) → OK. The DRT
  can inject rate-based rules and managed-rule-group updates during an L7
  attack.
- **ALB has NO WAF Web ACL** → **CONFIG_GAP**. Shield Advanced L7
  mitigation works THROUGH WAF — without a Web ACL, the DRT cannot create
  L7 mitigations for that ALB. L3/L4 volumetric protection still applies,
  but L7 attacks (HTTP flood, slowloris) are not mitigated.

NLB and CLB do not support WAF association — do NOT flag them for missing
WAF. WAF applies to ALB, API Gateway, AppSync, CloudFront, and
Cognito (regional resources). For Shield Advanced coverage, the WAF check
is ALB-specific (and CloudFront, but CloudFront is auto-protected and its
WAF is a separate audit dimension).

### Step 6b: Application Layer Automatic Response evaluation

For each ALB Protection with a WAF Web ACL, check whether Application
Layer Automatic Response is enabled:

- **Automatic Response ENABLED** (`EnableApplicationLayerAutomaticResponse`
  called) → OK. Shield automatically creates and tunes WAF rate-based
  rules without waiting for DRT manual intervention, reducing L7 attack
  response time from minutes to seconds.
- **Automatic Response NOT enabled** → **CONFIG_GAP** (advisory). The
  protection still works via DRT manual mitigation (Step 3) and always-on
  L3/L4 detections, but the faster automated path is dormant. Surface as
  a lower-priority finding — not every ALB needs automatic response, but
  critical internet-facing ALBs should have it.

**Expert note:** Automatic Response requires a WAF Web ACL on the
protection. An ALB with automatic response enabled but no Web ACL is a
hard CONFIG_GAP — the feature has nowhere to inject rules. This is
distinct from Step 6 (missing WAF entirely, which blocks all L7
mitigation).

### Step 7: Aggregation — worst verdict wins

The final verdict is the **maximum severity** across all steps, where
UNPROTECTED > NO_DRT_ACCESS > CONFIG_GAP > OK:

```text
verdict = max(coverage_verdict, drt_verdict, health_verdict, engagement_verdict, waf_verdict, auto_response_verdict)
```

If no findings (all dimensions OK), the verdict is **OK**.

## Output format (per account / scope)

```text
SCOPE: <account-id or "global + <region>">
VERDICT: UNPROTECTED | NO_DRT_ACCESS | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and step number>
FINDINGS:
  - [UNPROTECTED] <resource> not in Protections list (Step 2)
  - [NO_DRT_ACCESS] DRT RoleArn absent (Step 3)
  - [CONFIG_GAP] No health check on <protection> (Step 4)
  - [OK] CloudFront distributions auto-protected (Step 0a)
REMEDIATION: <specific action per finding, or "None required" if OK>
```

**Pagination loop (mandatory for large accounts):** `ListProtections`
returns at most 100 Protections per call. Drain ALL pages before
classifying coverage:

```text
protections = []
token = None
loop:
  resp = shield list-protections [--next-token token]
  protections += resp.Protections
  token = resp.NextToken
  if token is None: break
```

A first-page-only read will FALSELY report page-2+ resources as
UNPROTECTED. Always confirm `NextToken` is null before proceeding to
Step 2.

**Multi-region aggregation:** ALB/NLB/CLB/EIP Protections are regional.
Run the full audit (Steps 1-7) per region and emit one FINDINGS block per
region. The aggregate account-level verdict is the worst across all
regions. CloudFront/Route 53 auto-protection is global — check it once.
```text
ACCOUNT-LEVEL VERDICT: worst(us-east-1, eu-west-1, ap-southeast-2, ...)
```

### Worked example — ALB protected but no DRT access, no health check

```text
SCOPE: account 111111111111 (us-east-1)
VERDICT: NO_DRT_ACCESS
REASON: ALB app/prod-alb is explicitly protected but the DRT has no
associated role (Step 3) — the DRT cannot create custom WAF mitigations
during a live attack. A missing health check compounds the L7 detection gap.
FINDINGS:
  - [OK] ALB app/prod-alb is in Protections list (Step 2)
  - [NO_DRT_ACCESS] DRT RoleArn absent, LogBuckets empty (Step 3)
  - [CONFIG_GAP] Protection p-abc has no HealthCheckIds (Step 4)
  - [OK] Proactive engagement ENABLED with 2 emergency contacts (Step 5)
  - [OK] ALB has WAF Web ACL associated (Step 6)
REMEDIATION:
  1. Create the DRT IAM role and associate it:
     aws shield associate-drt-role --role-arn arn:aws:iam::111111111111:role/AWSShieldDRTAccessRole
  2. Associate the DRT log bucket (ALB access logs):
     aws shield associate-drt-log-bucket --log-bucket shield-drt-alb-logs
  3. Associate a Route 53 health check with the protection:
     aws shield associate-health-check --protection-id p-abc --health-check-arn arn:aws:route53:::healthcheck/hc-prod-alb
```

## Edge-case handling

- **Partially populated Protections list.** If the Protections list has
  some but not all ALBs, classify each missing ALB as UNPROTECTED and each
  present ALB as OK. Do NOT classify the entire account as UNPROTECTED if
  only one ALB is missing — enumerate per-resource findings so the operator
  can prioritize.

- **EC2 instance without EIP.** An EC2 instance with only a private IP
  cannot be DDoS-attacked from the internet. Do NOT flag it as UNPROTECTED.
  Only EC2 instances with an associated EIP (public IP) are in scope.

- **Resource re-created with a new ARN.** If an ALB was deleted and
  re-created (e.g., via Terraform destroy/apply), its ARN changed. The old
  Protection still references the old ARN and is now a stale entry. The
  new ALB is UNPROTECTED. Flag the stale Protection AND the missing
  coverage. Remediation: delete the stale Protection, create a new one
  for the new ARN.

- **Global Accelerator.** Global Accelerator is protected by Shield
  Advanced at the accelerator level. An accelerator without explicit
  Protection is UNPROTECTED. Treat like ALB — check the Protections list
  for the accelerator ARN.

- **CloudFront distribution in a different account.** Shield Advanced
  auto-protection applies per-account. A CloudFront distribution in account
  A is auto-protected by account A's Shield Advanced subscription, NOT by
  account B's. If auditing across accounts (Organizations), verify each
  account has an active subscription.

- **DRT role deleted outside Shield.** If the IAM role referenced by
  `AssociateDRTRole` was deleted directly in IAM (not via Shield), the DRT
  access state is stale — `DescribeDRTAccess` may still return the old
  RoleArn. The DRT cannot assume a deleted role. Treat as NO_DRT_ACCESS
  and re-associate a valid role.

- **Empty Protections list with only CloudFront/Route 53.** If the only
  internet-facing resources are CloudFront distributions and Route 53
  hosted zones, the Protections list can be legitimately empty (both are
  auto-protected). Do NOT flag an empty Protections list as UNPROTECTED if
  no ALB/NLB/CLB/EIP resources exist.

## Anti-Patterns — NEVER

- NEVER flag a CloudFront distribution or Route 53 hosted zone as
  UNPROTECTED because it is absent from the Protections list. These
  resources are **auto-protected** by Shield Advanced (re:Invent 2023).
  The Protections list only contains resources requiring explicit
  protection (ALB, NLB, CLB, EIP, Global Accelerator). Flagging
  CloudFront/Route 53 is the single most common Shield Advanced false
  positive.

- NEVER treat a CONFIG_GAP as worse than NO_DRT_ACCESS. The ordering is
  UNPROTECTED > NO_DRT_ACCESS > CONFIG_GAP > OK. A missing health check
  (CONFIG_GAP) does not outrank a missing DRT role (NO_DRT_ACCESS). The
  DRT's ability to manually intervene during an attack is more valuable
  than health-based detection automation.

- NEVER flag an EC2 instance with only a private IP as UNPROTECTED. It is
  not internet-facing and cannot be DDoS-attacked from outside the VPC.
  Only EC2 instances with an associated EIP (public IP) are in scope.

- NEVER recommend `CreateSubscription` (enabling Shield Advanced) without
  explaining the 1-year, non-cancellable, non-prorated commitment. The
  monthly fee applies regardless of how many resources you protect. This
  is a financial one-way door — surface it in the confirmation gate.

- NEVER treat an NLB or CLB missing a WAF Web ACL as a CONFIG_GAP. WAF
  applies to ALB (layer 7), CloudFront, API Gateway, AppSync, and Cognito.
  NLB (layer 4) and CLB (legacy layer 4/7 hybrid) do not support WAF
  association in the same way. Only flag ALB for missing WAF under Step 6.

- NEVER assume DRT access is present just because the subscription is
  active. DRT access is configured SEPARATELY via `AssociateDRTRole` and
  `AssociateDRTLogBucket`. An active subscription with no DRT role means
  the DRT cannot help you during an attack — this is NO_DRT_ACCESS, not
  OK.

- NEVER classify "DRT RoleArn present + LogBuckets empty" as
  NO_DRT_ACCESS. This is the most common DRT misclassification.
  NO_DRT_ACCESS means the DRT has NO role and CANNOT ACT AT ALL. A DRT
  WITH a role but WITHOUT a log bucket CAN still assume the role, create
  WAF rules, and mitigate attacks — it is simply blind to log-level attack
  patterns. This is CONFIG_GAP (partial DRT), not NO_DRT_ACCESS. The
  distinction is critical: "cannot help at all" (NO_DRT_ACCESS, no role)
  vs "can help but blind" (CONFIG_GAP, role present, no logs).

- NEVER treat `EnableProactiveEngagement` as sufficient on its own. It
  requires a populated `EmergencyContactList`. ENABLED without contacts is
  a CONFIG_GAP — the DRT has no one to call. Always check both.

- NEVER flag a Protection for missing HealthCheckIds if the protected
  resource is CloudFront or Route 53. These auto-protected resources do
  not use per-resource `AssociateHealthCheck` — they use Shield's built-in
  health detection. Flagging them is a false positive.

- NEVER treat Shield Standard as equivalent to Shield Advanced. Shield
  Standard is free, L3/L4 only, no DRT, no health-based detection, no WAF
  integration, no cost protection. An account on Shield Standard only is
  UNPROTECTED for L7 and has no manual mitigation path.

- NEVER recommend removing a Protection as remediation without confirming
  the resource is being decommissioned. Removing a Protection drops the
  resource to Shield Standard (L3/L4 only) immediately — there is no
  grace period. This is a destructive action.

- NEVER assume cost-protection credits apply automatically. They require
  health-based detection AND (for L7) a WAF Web ACL to be configured on
  the affected resource. Without these, scaling costs from a DDoS attack
  are borne by the customer.

- NEVER overlook stale Protections referencing deleted resources. A
  Protection whose `ResourceArn` points to a deleted ALB is actively
  dangerous, not just dead weight: it inflates the apparent coverage
  count (dashboards show "10 Protections" but only 8 are live), it
  silently fails during incident response because the DRT attempts to
  mitigate a non-existent resource and wastes the critical first minutes
  of an attack, and it masks the UNPROTECTED status of the re-created
  resource. Always cross-reference Protections against the live resource
  inventory and delete stale entries.

- NEVER leave a stale Protection in place after resource recreation. When
  an ALB/EIP is deleted and re-created (e.g., Terraform destroy/apply),
  the old Protection still references the dead ARN. The operator assumes
  coverage exists because the Protection name matches — but the live
  resource is UNPROTECTED. The remediation is a two-step sequence: (1)
  `DeleteProtection` on the stale entry, then (2) `CreateProtection` on
  the new ARN. Skipping step 1 leaves orphaned Protections that pollute
  future audits.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`CreateSubscription`, `CreateProtection`, `DeleteProtection`,
  `AssociateDRTRole`, `AssociateDRTLogBucket`, `EnableProactiveEngagement`),
  the auditor MUST emit:
  `CONFIRM: About to <action> in account <account>. This affects
  <consequence>. Proceed? (yes/no)`
  Do NOT execute the CLI command until the operator confirms.

- **CreateSubscription is a financial commitment.** Explicitly state:
  "This starts a 1-year, non-cancellable, non-prorated commitment. The
  monthly fee applies regardless of the number of protected resources."
  Do NOT auto-execute — require explicit operator approval.

- **DeleteProtection drops coverage immediately.** There is no grace
  period. Confirm the resource is being decommissioned before removing a
  Protection. Capture the Protection ID for rollback:
  `aws shield describe-protection --protection-id <id>` BEFORE deletion.

- **AssociateDRTRole grants cross-service access.** The DRT role must have
  a trust policy allowing `service-role.shield.amazonaws.com` to assume it.
  Verify the role exists and has the correct trust policy BEFORE
  associating — an invalid role ARN makes DRT access non-functional.

- **Regional vs global scope.** ALB/NLB/CLB/EIP protections are regional.
  CloudFront/Route 53 are global. When remediating across regions, apply
  `CreateProtection` in EACH region independently — a protection in
  us-east-1 does NOT cover the same-named ALB in eu-west-1.

- Prefer additive changes (add a Protection, associate a health check) over
  destructive changes (delete a Protection) — additive changes are
  reversible and do not risk dropping coverage.

## Remediation guidance

**Remediation ordering principle:** always resolve UNPROTECTED findings
first (add Protections), then NO_DRT_ACCESS (associate DRT role), then
CONFIG_GAP (health checks, proactive engagement, WAF). This ordering
ensures resources are covered before optimizing detection and engagement.

### For UNPROTECTED — resource not in Protections list (Step 2)

1. Create a Protection for the resource:
   `aws shield create-protection --name <name> --resource-arn <arn>`
2. For ALB, also verify a WAF Web ACL is associated (Step 6).
3. For EIP-backed EC2, the resource ARN is the EIP allocation:
   `arn:aws:ec2:<region>:<account>:elastic-ip/eipalloc-xxx`.
4. Verify: `aws shield describe-protection --protection-id <id>`.

### For UNPROTECTED — no active subscription (Step 1)

1. Subscribe:
   `aws shield create-subscription`
2. This starts the 1-year commitment. Confirm intent before executing.
3. After subscribing, proceed to create Protections for all ALB/NLB/CLB/EIP.

### For NO_DRT_ACCESS — DRT RoleArn absent (Step 3)

1. Create the DRT IAM role with a trust policy allowing
   `service-role.shield.amazonaws.com` to assume it. The role needs
   permissions to read WAF Web ACLs and create rate-based rules.
2. Associate the role:
   `aws shield associate-drt-role --role-arn <role-arn>`
3. Then associate the log bucket:
   `aws shield associate-drt-log-bucket --log-bucket <bucket-name>`
4. Verify: `aws shield describe-drt-access`.

### For CONFIG_GAP — DRT role present but no log bucket (Step 3)

1. Ensure ALB access logs are enabled and delivered to an S3 bucket.
2. Associate the bucket:
   `aws shield associate-drt-log-bucket --log-bucket <bucket-name>`

### For CONFIG_GAP — no health check on protection (Step 4)

1. Create a Route 53 health check for the resource endpoint:
   `aws route53 create-health-check --caller-reference <ref> --health-check-config file://hc-config.json`
2. Associate it with the Shield protection:
   `aws shield associate-health-check --protection-id <id> --health-check-arn <hc-arn>`

### For CONFIG_GAP — proactive engagement disabled or contacts empty (Step 5)

1. Populate the emergency contact list:
   `aws shield update-emergency-contact-list --emergency-contact-list '[{"EmailAddress":"oncall@example.com","PhoneNumber":"+1234567890","ContactNotes":"24/7 NOC"}]'`
2. Enable proactive engagement:
   `aws shield enable-proactive-engagement`

### For CONFIG_GAP — ALB has no WAF Web ACL (Step 6)

1. Create or identify a WAFv2 Web ACL for the ALB.
2. Associate it:
   `aws wafv2 associate-web-acl --web-acl-arn <acl-arn> --resource-arn <alb-arn>`
3. Optionally enable Application Layer Automatic Response:
   `aws shield enable-application-layer-automatic-response --protection-id <id> --web-acl-arn <acl-arn>`

### For OK

1. No remediation required for the current posture.
2. Recommend periodic re-audit after infrastructure changes (new ALBs, EIPs,
   or CloudFront distributions may be added without Shield coverage).
3. Review `aws shield list-attacks` for recent events and verify mitigation
   effectiveness.

## Deep reference: Shield Advanced internals

### Coverage model — auto vs explicit

Shield Advanced protection operates in two modes:

1. **Auto-protection (CloudFront, Route 53):** Once subscribed, ALL
   distributions and hosted zones are protected automatically. The
   `ListProtections` API does NOT list these — they are implicit. There is
   no `CreateProtection` call for these resource types; the API rejects it.

2. **Explicit protection (ALB, NLB, CLB, EIP, Global Accelerator):** Each
   resource must be individually added via `CreateProtection`. The
   `ListProtections` API returns these. Coverage gaps occur when resources
   are created without adding a Protection.

### Non-obvious classification gotchas — detailed

The one-liners in Step 0 summarize these; the full operational detail is
here for agents that need the reasoning behind each classification call.

- **DRT role trust policy principal.** The IAM role passed to
  `AssociateDRTRole` must have a trust policy allowing
  `service-role.shield.amazonaws.com` — not `shield.amazonaws.com`. The
  Shield API does NOT validate the trust policy on association; it
  accepts the role ARN silently. The failure surfaces only when the DRT
  attempts `sts:AssumeRole` during a live attack and receives
  `AccessDenied`. This is a silent NO_DRT_ACCESS that
  `DescribeDRTAccess` reports as healthy (it returns the RoleArn).

- **`AssociateHealthCheck` is write-only.** There is no Shield API to
  list which health checks are associated with which Protections. You
  MUST call `DescribeProtection` per Protection and read
  `HealthCheckIds`. `route53 list-health-checks` lists all health checks
  but does not indicate Shield associations. An auditor that assumes
  "a health check exists in Route 53, therefore the protection is
  covered" will produce false OK verdicts.

- **EIP Protection uses the allocation ID.** The `ResourceArn` for an EIP
  is `arn:aws:ec2:<region>:<account>:elastic-ip/eipalloc-xxx`. Using the
  public IP or EC2 instance ARN fails silently — `CreateProtection`
  accepts the string but the protection references a non-existent
  resource. The DRT cannot mitigate a resource that doesn't resolve.
  Verify via `aws ec2 describe-addresses` before creating.

- **Cost-protection credits require health checks AND WAF.** Without
  health-based detection, Shield cannot demonstrate to the cost-protection
  team that the scaling was caused by a detected DDoS event. Without WAF
  on an L7 attack, there is no mitigation record. Both are gating
  conditions for credit approval — their absence is a financial risk,
  not just a detection gap.

- **Subscription auto-renewal trap.** `CreateSubscription` starts a
  1-year term that auto-renews unless explicitly cancelled before the
  renewal date. There is no proration. An account subscribed for a
  one-time event (product launch, election night) that forgets to cancel
  will be billed silently for year 2. The confirmation gate must surface
  this.

- **`DescribeDRTAccess` can return a stale RoleArn.** If the IAM role
  referenced by `AssociateDRTRole` was deleted directly in IAM (not via
  `DisassociateDRTRole`), the Shield API may still return the old
  RoleArn. The DRT cannot assume a deleted role. This is a silent
  NO_DRT_ACCESS — cross-reference the RoleArn against live IAM roles
  using `iam get-role`.

- **TAG-based Protection grouping is not coverage.** Shield Advanced has
  no native resource-group or tag-based protection. Each Protection is a
  1:1 mapping to a single `ResourceArn`. An operator who assumes "all
  resources tagged `shield=protected` are covered" will miss any
  resource without an explicit Protection entry. Do not infer coverage
  from tags.

### DRT incident-response workflow

During a suspected DDoS event:
1. Shield Advanced always-on detections trigger (L3/L4 volumetric).
2. If health-based detection is configured, L7 degradation also triggers.
3. The DRT is notified automatically.
4. If proactive engagement is ENABLED, the DRT calls the emergency contacts.
5. The DRT assumes the associated IAM role and creates WAF rate-based rules
   in the resource's Web ACL.
6. If no DRT role is associated, the DRT cannot act — you must self-mitigate.
7. If no log bucket is associated, the DRT operates blind to log-level
   attack patterns.

### Cost-protection eligibility

Shield Advanced credits the cost of auto-scaling triggered by a DDoS
attack, subject to:
- The affected resource must have an active Protection.
- Health-based detection must be configured (Route 53 health check
  associated).
- For L7 attacks, a WAF Web ACL must be associated.
- The attack must be confirmed by AWS as a DDoS event.

Without health checks and WAF, cost-protection credits may be denied.

### Subscription lifecycle

- `CreateSubscription` starts a 1-year term. The monthly fee is charged
  from day one.
- The subscription auto-renews at the end of the term unless cancelled.
- There is no proration — cancelling mid-term does not refund remaining
  months.
- `DeleteSubscription` is available but does not refund. Protections,
  DRT access, and health-check associations persist but become
  non-functional (Shield Standard takes over).

## Recent AWS features (2024-2026)

- **Automatic application layer DDoS mitigation (2023 GA, 2024 enhanced):**
  Shield Advanced can now automatically create and tune WAF rules per-protection
  without DRT manual intervention, via
  `EnableApplicationLayerAutomaticResponse`. Auditors should verify that
  critical ALB protections have automatic response enabled — it reduces
  response time for known L7 attack patterns from minutes to seconds.
  Note: this requires a WAF Web ACL to be associated with the protection.

- **CloudFront and Route 53 automatic protection (re:Invent 2023):**
  All CloudFront distributions and Route 53 hosted zones are now
  auto-protected by Shield Advanced at no additional per-resource cost.
  Auditors must NOT flag these resources as UNPROTECTED for absence from
  the Protections list — this is the most common false positive.

- **Enhanced DRT visibility (2024-2025):** The DRT console now provides
  real-time attack visibility and mitigation tracking. Auditors should
  verify that the DRT has both role and log-bucket access to take full
  advantage of enhanced visibility features.

- **Shield Advanced health-check integration improvements (2024):**
  Improved correlation between Route 53 health checks and Shield Advanced
  detections, reducing false-negative L7 detection. Auditors should verify
  health checks are associated with all critical explicit protections.

- **Proactive engagement workflow updates (2024-2025):** Enhanced
  notification routing and multi-contact support. Auditors should verify
  the emergency contact list is current — stale contacts defeat proactive
  engagement.

## AWS documentation

- **AWS Shield Advanced Developer Guide** — https://docs.aws.amazon.com/waf/latest/developerguide/shield-chapter.html
- **AWS Shield API Reference** — https://docs.aws.amazon.com/waf/latest/APIReference/sourceshield.html
- **AWS CLI Shield Reference** — https://docs.aws.amazon.com/cli/latest/reference/shield/
- **AWS Shield Security** — https://docs.aws.amazon.com/waf/latest/developerguide/shield-security.html
- **DDoS Response Team (DRT)** — https://docs.aws.amazon.com/waf/latest/developerguide/ddos-overview.html
- **Shield Advanced getting started** — https://docs.aws.amazon.com/waf/latest/developerguide/getting-started-ddos.html

## Domain

AWS CloudOps / DDoS Protection & Shield Advanced Coverage Security.
