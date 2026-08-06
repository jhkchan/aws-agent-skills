---
name: network-firewall-rule-auditor
description: >-
  Audits AWS Network Firewall configurations for permissive stateful and
  stateless rules, missing TLS inspection, firewall-subnet routing gaps that
  bypass inspection, rule-group evaluation-order shadowing, and logging
  blind spots. Emits a deterministic verdict (PERMISSIVE_RULE |
  NO_TLS_INSPECTION | ROUTING_GAP | CONFIG_GAP | OK) per firewall with
  enumerated findings and specific CLI remediation. Use when reviewing
  Network Firewall policies, checking for wildcard pass rules, validating
  TLS inspection coverage, auditing firewall route tables, or verifying
  rule-group evaluation order before production deployment.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline policy-document classification.
  Live-account audits use aws network-firewall describe-firewall,
  describe-firewall-policy, describe-rule-group, describe-logging-configuration,
  describe-tls-inspection-config, and aws ec2 describe-route-tables (AWS CLI v2,
  SSO or key-based credentials).
keywords:
  - Network Firewall
  - stateful rules
  - stateless rules
  - Suricata
  - TLS inspection
  - firewall routing
  - rule group
  - StatelessDefaultActions
  - StatelessFragmentDefaultActions
  - StatefulDefaultActions
  - drop_strict
  - forward_to_sfe
  - HOME_NET
  - fragment bypass
  - shadowed rule
  - STRICT_ORDER
  - SNI
  - network firewall audit
  - intrusion prevention
tags: [network-firewall, security, stateful-rules, stateless-rules, tls-inspection, routing, suricata, audit]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Security
  verdict_shape: "PERMISSIVE_RULE | NO_TLS_INSPECTION | ROUTING_GAP | CONFIG_GAP | OK"
  when_to_use: >-
    Reviewing a Network Firewall policy before production deployment, checking
    for permissive stateful or stateless rules, validating TLS inspection
    coverage, auditing firewall subnet route tables for traffic-bypass gaps,
    verifying rule-group evaluation order, or hardening intrusion-prevention
    posture across a VPC.
  activation_triggers:
    - "audit this network firewall"
    - "check firewall rules"
    - "permissive firewall policy"
    - "is TLS inspection enabled"
    - "firewall routing gap"
    - "rule group evaluation order"
    - "stateless default actions"
    - "fragment bypass firewall"
    - "shadowed Suricata rules"
    - "HOME_NET misconfiguration"
  invocation_schema: >-
    Input: either (a) a Network Firewall policy JSON (stateful + stateless rule
    groups, default actions), optionally paired with route-table data and TLS
    config, OR (b) a firewall-arn/name for live-account audit.
    Output: deterministic FIREWALL/VERDICT/REASON/FINDINGS/REMEDIATION block per
    firewall, where VERDICT ∈ {PERMISSIVE_RULE, NO_TLS_INSPECTION, ROUTING_GAP,
    CONFIG_GAP, OK, ERROR}.
---

# Network Firewall Rule Auditor

## Mindset

**One-line takeaway:** a perfectly authored rule group is worthless if the
route table sends traffic around the firewall, if fragments bypass the
stateless engine, or if TLS inspection is absent — always audit the data
path BEFORE the rules.

AWS Network Firewall is a managed stateful network inspection service
deployed inside dedicated firewall subnets. Three properties make it unlike
SGs or NACLs:

1. **Routing is the enforcement gate.** Unlike a security group (always
   attached to an ENI), a Network Firewall only inspects traffic that the
   VPC route tables actually route through its ENIs. A route-table typo
   silently disables the entire firewall. This is ROUTING_GAP — the most
   operationally dangerous verdict because it produces a false sense of
   security.

2. **Two engines, two rule languages.** Stateless rules (5-tuple match,
   first-match-wins per group) and stateful rules (Suricata-compatible,
   flow-aware) are separate evaluation pipelines with different action
   vocabularies. The `StatelessDefaultActions` on the policy must include
   `aws:forward_to_sfe` to hand unmatched traffic to the stateful engine —
   if it is `aws:pass`, the stateful engine is effectively dead.

3. **TLS inspection is opt-in and domain rules are not enough.** Without a
   `TLSInspectionConfiguration`, stateful domain-list rules still match SNI
   in the ClientHello (plaintext) but Suricata `content` / payload matching
   is blind to all TLS traffic. Most modern traffic is HTTPS — a payload rule
   without TLS inspection is dead code.

## Quick reference — verdict thresholds

| Condition | Verdict | Step |
|---|---|---|
| Route table for a workload subnet does not route 0.0.0.0/0 (or a covered CIDR) through a firewall ENI | **ROUTING_GAP** | 1 |
| Return path (egress from firewall subnet) missing or asymmetric | **ROUTING_GAP** | 1 |
| `StatelessDefaultActions` is `aws:pass` (not `aws:forward_to_sfe`) | **PERMISSIVE_RULE** | 2 |
| `StatelessFragmentDefaultActions` is `aws:pass` (fragment bypass) | **PERMISSIVE_RULE** | 2 |
| `StatefulDefaultActions` is `aws:alert_strict` / `alert_established` (alert only, never blocks) | **PERMISSIVE_RULE** | 3 |
| Suricata `pass ip any any -> any any` or wildcard pass rule | **PERMISSIVE_RULE** | 4 |
| Stateless rule with all-wildcard 5-tuple + `aws:pass` action | **PERMISSIVE_RULE** | 4 |
| `STRICT_ORDER` group with a broad `pass` before a narrow `drop` (shadowed drop) | **PERMISSIVE_RULE** | 5 |
| `STRICT_ORDER` group with a `drop` before a `pass` (dead pass — functional bug) | **CONFIG_GAP** | 5 |
| `TLSInspectionConfigurationArn` absent + stateful rules use `content`/payload matching | **NO_TLS_INSPECTION** | 6 |
| Domain-list rule with `Targets: [HTTP_HOST]` only (HTTPS traffic never matches) | **CONFIG_GAP** | 6 |
| No logging configuration / `FlowLogs` + `AlertLogs` both disabled | **CONFIG_GAP** | 7 |
| All dimensions clean (scoped rules, drop defaults, TLS on, routing valid, logging on) | **OK** | 8 |

See the ordered steps below for edge cases. Deep Suricata and routing
internals are in the [Expert edge cases](#expert-edge-cases) section.

**Verdict priority (worst finding wins on aggregation):**
`PERMISSIVE_RULE > ROUTING_GAP > NO_TLS_INSPECTION > CONFIG_GAP > OK`

## Pre-flight: firewall metadata gate (run before rule classification)

| Attribute | Value | Effect on audit |
|---|---|---|
| `FirewallStatus` | `DELETING` | Firewall is being torn down — rules are irrelevant. VERDICT: `OK` with a note. |
| `FirewallPolicyResponse.FirewallPolicyStatus` | `DELETING` | Policy is mid-deletion. Flag as CONFIG_GAP — the policy is not in steady state. |
| `EncryptionConfiguration.Type` | unset / `NONE` | Firewall does not use customer-managed KMS for its own config. Note as CONFIG_GAP (defense-in-depth). |
| `SubnetMappings` | single AZ only | Single-AZ firewall — no AZ redundancy. Note as CONFIG_GAP (availability risk, not a security verdict driver). |
| `DeleteProtection` | `false` | Firewall can be deleted without unprotecting. Note in REMEDIATION. |

**If the policy JSON is malformed** (invalid JSON, missing `StatefulRuleGroups`
or `StatelessRuleGroupReferences`), output:

```text
FIREWALL: <name>
VERDICT: ERROR
REASON: Firewall policy document is malformed or missing required fields — cannot classify.
REMEDIATION: Re-fetch with `aws network-firewall describe-firewall-policy --firewall-policy-arn <arn> --output json`.
```

**Pagination note:** `describe-rule-group` is per-group; there is no list
shortcut that returns rule bodies. When auditing a live account, iterate
`list-rule-groups --type STATEFUL --scope MANAGED` and `--scope CUSTOMER`
(paged via `--starting-token`), then call `describe-rule-group` per ARN. A
policy can reference more rule groups than the first page reveals.

## Process — Classification logic (apply every step, aggregate worst)

### Step 0: Expert knowledge — non-obvious Network Firewall behaviors

These behaviors change a verdict if ignored:

- **`HOME_NET` is set automatically to the VPC CIDR and is NOT API-editable.**
  Suricata rules referencing `$HOME_NET` match the firewall's VPC. A peered
  VPC's CIDR is NOT in `$HOME_NET` — it is `$EXTERNAL_NET`. A rule like
  `drop tcp $EXTERNAL_NET any -> $HOME_NET 22` treats peered-VPC SSH as
  hostile, which may be unintended.

- **Stateless `aws:pass` STOPS evaluation of that rule group only.** It does
  not skip the stateful engine — the `StatelessDefaultActions` controls
  whether unmatched traffic reaches stateful. But if a stateless rule with
  `aws:pass` MATCHES, that traffic does NOT get a second chance at stateful
  inspection unless the default action also forwards. This is subtle:
  `aws:pass` in a stateless rule means "this rule group is done with this
  packet", not "allow this packet everywhere".

- **Fragments cannot be statefully inspected.** The stateful engine needs
  full packets to reconstruct flows. `StatelessFragmentDefaultActions:
  [aws:pass]` lets all fragments bypass BOTH engines — an attacker fragments
  malicious traffic and evades every stateful rule. This is why fragment-pass
  is PERMISSIVE_RULE, not CONFIG_GAP.

- **`drop_established` (the default) grandfatheres existing flows.** When a
  new `drop` rule is added, flows already established before the rule change
  continue uninterrupted until they end. `drop_strict` evaluates every packet
  independently — new drop rules take effect immediately. Auditors cannot tell
  from the policy alone which flows are established; flag `drop_established`
  as CONFIG_GAP for incident-response contexts (the rule may not be blocking
  what you think).

- **Suricata `alert` does NOT block, even under `drop_strict`.** `alert`
  logs and continues; only `drop` / `reject` block. Operators frequently
  assume alert rules are "blocking in detect mode" — they are not. If a rule's
  intent is "block and log", the action must be `drop`, not `alert`.

- **`reject` reveals the firewall's presence.** Suricata `reject` sends a
  TCP RST (or ICMP unreachable for UDP). Active attackers can infer a firewall
  is inline. `drop` is silent. For internet-facing firewalls, prefer `drop`.

- **Domain-list `Targets` determines which traffic a domain rule can match.**
  `TLS_SNI` matches the ClientHello SNI (HTTPS). `HTTP_HOST` matches the Host
  header (plaintext HTTP only). A rule with `Targets: [HTTP_HOST]` matching
  domain `evil.example` NEVER fires on HTTPS traffic — most modern traffic.
  This is a silent functional defect (CONFIG_GAP), not a security exposure.

- **`STRICT_ORDER` shadows rules; `DEFAULT_ACTION_ORDER` does not.** In
  `STRICT_ORDER`, the first matching rule's action is final — a broad `pass`
  at the top of the group makes every later `drop` unreachable for that
  traffic. In `DEFAULT_ACTION_ORDER`, all rules are evaluated and the most
  severe action wins (drop > reject > pass > alert). Mixing a strict-order
  pass-before-drop is PERMISSIVE_RULE because the intended block is dead.

- **`aws:forward_to_sfe` is the only stateless action that reaches stateful.**
  `aws:pass` and `aws:drop` are terminal for the stateless pipeline. If the
  `StatelessDefaultActions` is `aws:pass`, NO traffic ever reaches the stateful
  engine — every stateful rule group is dead code. This is PERMISSIVE_RULE.

- **Rule-group `Capacity` is fixed at creation and consumed per rule type.**
  A stateful domain rule consumes more capacity than a stateless 5-tuple rule.
  A group at capacity cannot absorb new rules without recreation — an auditor
  proposing additive rules must check `ConsumedCapacity` vs `Capacity`.

- **`UpdateToken` changes on every write.** Optimistic concurrency: if two
  operators edit concurrently, one gets `InvalidTokenException`. Always
  re-fetch the token immediately before each mutation; a token cached minutes
  ago may be stale.

- **A policy can attach to multiple firewalls.** Editing a shared policy
  affects ALL attached firewalls simultaneously. Before remediation, enumerate
  `aws network-firewall list-firewalls --firewall-policy-arn <arn>` to
  understand blast radius.

- **`StreamExceptionPolicy` controls fail-open vs fail-closed on stream
  errors.** When the stateful engine cannot reassemble a TCP stream
  (out-of-order segments, corrupted state), this policy setting determines
  the outcome: `REJECT` (default) drops the flow (fail-closed); `CONTINUE`
  passes it (fail-open). Verify it is `REJECT` — `CONTINUE` is a silent
  bypass vector (attacker induces stream errors to evade stateful rules).

- **Network Firewall does NOT inspect TGW east-west traffic unless the TGW
  route tables explicitly steer it.** In a Transit Gateway inspection
  topology, the TGW route table is a SEPARATE routing layer from VPC route
  tables. A ROUTING_GAP at the TGW level is invisible if the auditor only
  checks VPC route tables.

### Step 1: Routing topology (ROUTING_GAP)

The firewall is only effective if traffic actually traverses its ENIs. For
each workload subnet behind the firewall, verify:

1. The subnet's route table has a default route (`0.0.0.0/0`, or the
   protected CIDR) whose target is a firewall ENI in the same AZ
   (`vpc-ec2-eni-...`), NOT the IGW or NAT gateway directly.
2. The firewall subnet's route table has a default route to the IGW (egress)
   or NAT gateway.
3. BOTH directions traverse the firewall (symmetric routing). An asymmetric
   path (request through firewall, return direct) prevents the stateful
   engine from tracking the flow — rules fire incorrectly or not at all.
4. In a multi-AZ deployment, each AZ has its own firewall ENI and the route
   table for each AZ points to the ENI in that AZ. A single route table
   pointing all AZs to one ENI creates cross-AZ inspection traffic that
   degrades performance and fails during AZ outages.

**If any route table check fails → ROUTING_GAP.** This is evaluated first
because it invalidates all downstream rule analysis — if traffic does not
reach the firewall, the rules are irrelevant.

### Step 2: Stateless default actions (PERMISSIVE_RULE)

Extract `StatelessDefaultActions` and `StatelessFragmentDefaultActions` from
the policy:

- **`StatelessDefaultActions: [aws:pass]`** → **PERMISSIVE_RULE**. All
  non-matching traffic bypasses the stateful engine. Every stateful rule
  group is dead code. The correct default is `[aws:forward_to_sfe]`.
- **`StatelessFragmentDefaultActions: [aws:pass]`** → **PERMISSIVE_RULE**.
  IP fragments bypass both engines — fragmentation evades every rule. The
  correct default is `[aws:forward_to_sfe]` or `[aws:drop]`.
- **`StatelessDefaultActions: [aws:drop]`** → **PERMISSIVE_RULE** if the
  intent is inspection (stateful rules never see traffic). This is only
  acceptable for an explicit deny-all posture — flag and let the operator
  confirm. If `aws:forward_to_sfe` is present alongside, traffic reaches
  stateful: OK for this dimension.

### Step 3: Stateful default actions (PERMISSIVE_RULE)

Extract `StatefulDefaultActions`:

- **`aws:alert_strict` / `aws:alert_established`** → **PERMISSIVE_RULE**.
  The firewall logs non-matching traffic but NEVER blocks it — it is an IDS,
  not an IPS. For a security enforcement posture, this is a fail-open
  configuration.
- **`aws:drop_strict`** → OK. Every packet is evaluated independently; new
  drop rules take effect immediately. Recommended for enforcement.
- **`aws:drop_established`** → OK for steady state, but flag as a note:
  flows established before a new drop rule was added continue uninterrupted.
  For incident response, this is a gap — switch to `drop_strict`.

### Step 4: Permissive rule detection (PERMISSIVE_RULE)

For each stateful rule group, inspect the Suricata rules (or domain list):

- **Wildcard pass:** `pass ip any any -> any any` (or `pass tcp any any ->
  any any`, `pass udp any any -> any any`) → **PERMISSIVE_RULE**. This passes
  all traffic of that protocol, overriding all drop rules in
  `DEFAULT_ACTION_ORDER` and shadowing later drops in `STRICT_ORDER`.
- **Broad HOME_NET pass:** `pass ip $HOME_NET any -> $EXTERNAL_NET any` passes
  all outbound traffic. Depending on posture, this may be intentional
  (egress monitoring) but it nullifies egress drop rules. Flag as
  PERMISSIVE_RULE unless the group's stated intent is "egress allow with
  selective blocks" AND those blocks are ordered before the pass in STRICT_ORDER.
- **Domain-list `Action: ALLOW`** on a broad domain (e.g., `*.com`, `*`) →
  **PERMISSIVE_RULE**. A wildcard-domain allow passes all matching HTTPS
  traffic regardless of payload.

For each stateless rule group, inspect the 5-tuple rules:

- **All-wildcard 5-tuple + `aws:pass`:** source `0.0.0.0/0`, destination
  `0.0.0.0/0`, ports `ANY`, protocol `ANY`, action `aws:pass` →
  **PERMISSIVE_RULE**. This is the stateless equivalent of a wildcard pass.

### Step 5: Rule-group evaluation order (PERMISSIVE_RULE | CONFIG_GAP)

For each stateful rule group with `RuleOrder: STRICT_ORDER`:

- If a broad `pass` rule precedes a narrow `drop` rule covering overlapping
  traffic → **PERMISSIVE_RULE** (the drop is shadowed — traffic passes).
- If a broad `drop` precedes a narrow `pass` → **CONFIG_GAP** (the pass is
  dead — intended allow is broken; functional bug, not a security exposure).
- Domain-list groups are evaluated by the list's match semantics, not
  STRICT_ORDER — this check does not apply.

For `DEFAULT_ACTION_ORDER` groups, all rules are evaluated and the most
severe action wins. Shadowing does not occur. If the group's `RuleOrder` is
unset, the default is `STRICT_ORDER` — assume strict when absent.

### Step 6: TLS inspection (NO_TLS_INSPECTION | CONFIG_GAP)

Check `FirewallPolicy.TLSInspectionConfigurationArn`:

- **Absent (null/empty) + stateful rules use `content`/payload matching** →
  **NO_TLS_INSPECTION**. Payload rules cannot match TLS traffic — most modern
  flows. Domain-list rules still match SNI (plaintext), so SNI-based domain
  rules are NOT affected. This finding only fires when payload rules exist.
- **Absent + ONLY domain-list (SNI) rules** → OK for TLS (SNI does not need
  decryption). Note in REMEDIATION: "enable TLS inspection for deeper
  coverage".
- **Present + payload rules** → OK for this dimension. Note: verify the TLS
  certificate authority is trusted by clients and the cert is not expired
  (operational check).
- **Domain-list rule with `Targets: [HTTP_HOST]` only** → **CONFIG_GAP**.
  HTTPS traffic (the majority) never matches — the rule is dead for its
  likely intent. Add `TLS_SNI` to targets.

### Step 7: Logging and observability (CONFIG_GAP)

Check `DescribeLoggingConfiguration`:

- **No logging configuration** (empty response) → **CONFIG_GAP**. Firewall
  decisions are invisible — no alert log, no flow log. Incident response and
  tuning are impossible without logs.
- **`AlertLogs` enabled but `FlowLogs` disabled** → **CONFIG_GAP** (minor).
  Alerts capture rule matches but not baseline traffic. Enable both for full
  visibility.
- **Both enabled** → OK for this dimension.

### Step 8: Aggregation — worst finding wins

Collect all findings from Steps 1-7. The final verdict is the highest-priority
verdict across all findings:

```text
verdict = max(all_findings, key=lambda f: PRIORITY[f.verdict])
# PRIORITY: PERMISSIVE_RULE=5, ROUTING_GAP=4, NO_TLS_INSPECTION=3, CONFIG_GAP=2, OK=1
```

If no findings, verdict is **OK**.

## Output format (per firewall)

```text
FIREWALL: <name>
VERDICT: PERMISSIVE_RULE | NO_TLS_INSPECTION | ROUTING_GAP | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its step number>
FINDINGS:
  - [PERMISSIVE_RULE] <finding description (Step N)>
  - [CONFIG_GAP] <finding description (Step N)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — wildcard pass + missing TLS

```text
FIREWALL: fw-prod-edge
VERDICT: PERMISSIVE_RULE
REASON: Stateful rule group "allow-baseline" contains `pass ip any any ->
any any` which passes all IP traffic (Step 4). TLS inspection is also absent,
making payload rules blind to HTTPS (Step 6).
FINDINGS:
  - [PERMISSIVE_RULE] Wildcard pass rule `pass ip any any -> any any` in group
    allow-baseline overrides all drop rules (Step 4)
  - [NO_TLS_INSPECTION] No TLSInspectionConfigurationArn on policy; 3 stateful
    content-matching rules cannot match TLS traffic (Step 6)
REMEDIATION:
  1. Remove or scope the wildcard pass rule to specific CIDRs/ports.
  2. Create and attach a TLS inspection configuration:
     aws network-firewall create-tls-inspection-config ...
     aws network-firewall associate-tls-inspection-config ...
```

## Expert edge cases

### The `forward_to_sfe` default is the stateful engine's lifeline

A policy with `StatelessDefaultActions: [aws:pass]` looks normal to an
operator skimming the console — "pass" sounds safe. But it means NO traffic
reaches the stateful engine. The stateful rule groups (Suricata rules,
domain lists) are entirely dead code. This is the single most dangerous
misconfiguration because the console shows healthy rule groups that do
nothing. Always verify the default includes `aws:forward_to_sfe`.

### Asymmetric routing silently breaks stateful tracking

The stateful engine tracks flows by seeing both directions. If outbound
traffic goes through the firewall but the return path comes directly (e.g.,
a peered VPC returns via a transit gateway that bypasses the firewall), the
stateful engine sees only half the flow. Rules that depend on flow state
(session tracking, established-flow exceptions) misfire. This is NOT a
PERMISSIVE_RULE — it is a ROUTING_GAP because the root cause is the route
table, not the rules.

### `drop_established` in incident response

During incident response, an operator adds a `drop` rule for a C2 domain.
With `StatefulDefaultActions: [aws:drop_established]`, existing connections
to that domain continue until the flow ends naturally — the C2 channel stays
open. Switch to `aws:drop_strict` during IR to ensure new rules take effect
immediately on every packet. After the incident, `drop_established` is
acceptable for steady state (avoids disrupting legitimate long-lived flows).

### Suricata `rev` and rule staleness

Suricata rules have a `rev` (revision) number. Managed rule groups update
revisions over time. A custom rule with `rev:1` that was written months ago
may be stale — the threat signature has evolved. This is not a verdict
driver but should be noted in REMEDIATION for custom stateful rules with low
revision numbers.

### Capacity exhaustion blocks remediation

When proposing additive rules (e.g., adding a new `drop` rule), check
`ConsumedCapacity` vs `Capacity` on the rule group. If the group is at
capacity, the `update-rule-group` call fails with `InsufficientCapacity`. The
remediation is to create a new rule group with higher capacity and
re-attach — this requires a policy update and affects all attached firewalls.

### Multi-firewall policy blast radius

A policy shared across firewalls (e.g., a shared inspection VPC serving
multiple spoke VPCs) means a rule change affects ALL firewalls. Before any
remediation, enumerate `list-firewalls --firewall-policy-arn <arn>`. A
rule that is safe for one VPC may block legitimate traffic in another. This
is why the pre-flight safety gate requires confirming the blast radius.

### TLS inspection certificate chain

TLS inspection uses a CA certificate that signs on-the-fly server certs. If
the CA is not trusted by clients (corporate trust store, browser), TLS
handshakes fail — the firewall breaks connectivity. Additionally, the CA
cert has an expiry; an expired cert silently breaks TLS inspection. Verify
cert validity and trust distribution before enabling. This is an operational
prerequisite, not a verdict driver.

### Managed rule group versioning

AWS-managed stateful rule groups (ThreatSignatures) update independently.
A firewall policy references a specific managed group, but the group's
content changes over time. An audit snapshot may be stale by the time it is
reviewed. Note the managed group's version in the output for traceability.

## Anti-Patterns — NEVER

- NEVER assume traffic reaches the firewall just because the firewall exists.
  Verify the route table. A firewall with perfect rules and a bypass route is
  equivalent to no firewall.

- NEVER classify `StatelessDefaultActions: [aws:pass]` as OK. Without
  `aws:forward_to_sfe`, the stateful engine never sees traffic. Every
  stateful rule group is dead code. This is PERMISSIVE_RULE.

- NEVER classify `StatelessFragmentDefaultActions: [aws:pass]` as OK.
  Fragments bypass both engines. Attackers fragment traffic to evade rules.
  This is PERMISSIVE_RULE.

- NEVER treat Suricata `alert` as a blocking action. `alert` logs only — the
  traffic continues. Only `drop` and `reject` block. If the intent is
  enforcement, the action must be `drop`.

- NEVER ignore `STRICT_ORDER` rule shadowing. A broad `pass` before a narrow
  `drop` in a strict-order group makes the drop unreachable. The traffic
  passes — this is PERMISSIVE_RULE, not a cosmetic ordering issue.

- NEVER assume domain-list rules need TLS inspection. SNI matching works
  without decryption (the ClientHello is plaintext). Only Suricata `content`
  / payload rules require TLS inspection. Conflating the two produces false
  NO_TLS_INSPECTION findings.

- NEVER recommend `reject` for internet-facing firewalls without noting the
  information-disclosure trade-off. `reject` sends TCP RST / ICMP unreachable,
  revealing an inline firewall. `drop` is silent.

- NEVER edit a shared firewall policy without enumerating attached firewalls.
  `list-firewalls --firewall-policy-arn <arn>` reveals the blast radius. A
  rule change on a shared policy affects every attached firewall
  simultaneously.

- NEVER trust `drop_established` during incident response. Existing flows
  survive new drop rules. Switch to `drop_strict` for IR to ensure immediate
  enforcement.

- NEVER classify `StatefulDefaultActions: [aws:alert_strict]` as OK for an
  enforcement firewall. Alert-only is IDS mode — the firewall detects but
  never blocks. This is PERMISSIVE_RULE for enforcement postures.

- NEVER assume `HOME_NET` includes peered VPCs. It is set to the firewall's
  VPC CIDR only. Peered VPCs are `$EXTERNAL_NET`. Rules referencing
  `$EXTERNAL_NET` may flag peered-VPC traffic as hostile.

- NEVER propose additive rules without checking `ConsumedCapacity` vs
  `Capacity`. A group at capacity rejects new rules — the remediation command
  fails silently in automation.

- NEVER cache `UpdateToken` across mutations. The token changes on every
  write. A stale token produces `InvalidTokenException`. Re-fetch before each
  mutation.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`update-firewall-policy`, `update-rule-group`,
  `associate-tls-inspection-config`, `update-logging-configuration`,
  `replace-route`), emit:
  `CONFIRM: About to <action> on firewall <name> / policy <arn>. This
  affects <consequence> and <N> attached firewall(s). Proceed? (yes/no)`
  Do NOT execute until the operator confirms.
- **Blast-radius enumeration.** Before editing a policy, run:
  `aws network-firewall list-firewalls --firewall-policy-arn <arn>` and
  report the count. A shared policy change affects every attached firewall.
- **Backup the current policy:**
  `aws network-firewall describe-firewall-policy --firewall-policy-arn <arn> --output json > /tmp/<name>-policy-backup-$(date +%s).json`
  BEFORE any modification. Policy changes are not versioned — there is no
  automatic rollback.
- **Re-fetch `UpdateToken` immediately before each mutation.** Do not reuse a
  token from a prior call.
- **Route-table changes affect live traffic.** `replace-route` on a production
  route table can cause instantaneous traffic disruption. Always test in a
  staging VPC first and apply during a maintenance window.
- For PERMISSIVE_RULE findings (wildcard pass, fragment bypass), treat as
  high-priority — the firewall is actively configured to allow traffic that
  should be inspected or blocked. Remediate before the next change window.
- Prefer additive changes (add a `drop` rule, change a default action to
  include `forward_to_sfe`) over destructive changes (remove a `pass` rule
  that may be load-bearing for a workload you did not anticipate).

## Remediation guidance

**Ordering principle:** always prefer additive changes over destructive
changes. Add a `drop` rule before removing a `pass` rule — the drop takes
effect immediately while you investigate what the pass was protecting.

### For PERMISSIVE_RULE — stateless default pass

1. Change the default to forward to stateful:
   `aws network-firewall update-firewall-policy --firewall-policy-arn <arn> --firewall-policy '{"StatelessDefaultActions":["aws:forward_to_sfe"],...}'`
2. Verify the stateful engine now sees traffic via CloudWatch metrics
   (`DroppedPackets`, `PassedPackets`) — `PassedPackets` should drop as
   stateful rules begin evaluating.

### For PERMISSIVE_RULE — fragment default pass

1. Change fragment default to forward or drop:
   `aws network-firewall update-firewall-policy --firewall-policy-arn <arn> --firewall-policy '{"StatelessFragmentDefaultActions":["aws:forward_to_sfe"],...}'`
2. Verify no legitimate fragmented traffic breaks (some legacy protocols
   fragment; test in staging first).

### For PERMISSIVE_RULE — wildcard stateful pass

1. Remove or scope the wildcard pass rule. If the rule was intended to allow
   baseline traffic, replace `pass ip any any -> any any` with scoped CIDRs
   and ports.
2. If the rule group is `STRICT_ORDER`, ensure any `drop` rules are ordered
   BEFORE surviving `pass` rules.

### For PERMISSIVE_RULE — alert-only stateful default

1. Change to enforcement:
   `aws network-firewall update-firewall-policy --firewall-policy-arn <arn> --firewall-policy '{"StatefulDefaultActions":["aws:drop_strict"],...}'`
2. Monitor `DroppedPackets` for a spike — the transition from alert to drop
   may block previously-tolerated traffic.

### For ROUTING_GAP

1. Fix the route table for the affected subnet:
   `aws ec2 replace-route --route-table-id <rtb-id> --destination-cidr-block 0.0.0.0/0 --vpc-endpoint-eni-id <firewall-eni-id>`
   (or `--network-interface-id <eni-id>` depending on the ENI type).
2. Verify symmetric routing: check the return path route table also points
   through the firewall.
3. In multi-AZ, ensure each AZ's route table points to the ENI in that AZ.

### For NO_TLS_INSPECTION

1. Create a TLS inspection config with a CA certificate:
   `aws network-firewall create-tls-inspection-config --tls-inspection-config-name <name> --certificates ...`
2. Associate it with the policy:
   `aws network-firewall update-firewall-policy --firewall-policy-arn <arn> --firewall-policy '{"TLSInspectionConfigurationArn":"<arn>",...}'`
3. Distribute the CA cert to client trust stores BEFORE enabling, or TLS
   handshakes will fail.

### For CONFIG_GAP — missing logging

1. Enable both alert and flow logs:
   `aws network-firewall update-logging-configuration --firewall-arn <arn> --logging-configuration '{"LogDestinationConfigs":[{"LogType":"ALERT","LogDestinationType":"CloudWatchLogs","LogDestination":{"logGroup":"fw-alerts"}},{"LogType":"FLOW","LogDestinationType":"CloudWatchLogs","LogDestination":{"logGroup":"fw-flow"}}]}'`

### For CONFIG_GAP — shadowed dead pass rule

1. Reorder the rule group so `drop` rules precede `pass` rules for
   overlapping traffic (in STRICT_ORDER groups).
2. Update the rule group:
   `aws network-firewall update-rule-group --rule-group-arn <arn> --rule-group '{...reordered...}' --type STATEFUL --update-token <token>`

### For OK

1. No remediation required for the current posture.
2. Recommend verifying `drop_strict` vs `drop_established` matches the
   operational context (steady state vs incident response).
3. Recommend periodic review of managed rule group versions and custom rule
   `rev` numbers.

## Error handling during remediation

| Error | Cause | Action |
|---|---|---|
| `InsufficientCapacityException` | Rule group `ConsumedCapacity` would exceed `Capacity` after the proposed additive rule | Create a new rule group with higher capacity, migrate rules, re-attach to policy. Do NOT delete the old group until the new one is verified. |
| `InvalidTokenException` | `UpdateToken` was stale (another write occurred between fetch and mutation) | Re-fetch with `describe-firewall-policy` / `describe-rule-group`, retry the mutation with the fresh token. Never cache tokens across calls. |
| `AccessDeniedException` on `update-*` | The auditor's IAM role lacks `network-firewall:UpdateFirewallPolicy` or `UpdateRuleGroup` | Verify IAM permissions BEFORE emitting remediation CLI — surface the missing action to the operator rather than letting the command fail at runtime. |
| `InvalidOperationException` | Attempting to modify an AWS-managed rule group (`Type: MANAGED`) | Managed groups are not customer-editable. Detach the managed group and create a custom replacement if different behavior is needed. |
| `ThrottlingException` | Rate-limited on `describe-rule-group` during bulk audit (pagination) | Implement exponential backoff. `describe-rule-group` is per-group; batching does not help — serialize with retry. |

## Recent AWS features (2024-2026)

- **Suricata 6 compatibility (2024):** Network Firewall updated its Suricata
  engine to version 6, adding support for new protocol parsers and detection
  keywords. Auditors should verify custom rules use Suricata 6-compatible
  syntax — rules written for Suricata 5 may behave differently.
- **TLS inspection GA enhancements (2024-2025):** TLS inspection configuration
  now supports certificate revocation checking (OCSP stapling) and improved
  visibility into inspection failures. Auditors should verify the TLS
  inspection config's certificate authority is not expired and the OCSP
  responder is reachable.
- **Managed domain list expansion (2024-2025):** AWS expanded managed stateful
  domain lists (e.g., `AWSManagedRulesBotNetControlList`,
  `AWSManagedRulesThreatSignaturesIpReputationList`). Auditors should verify
  managed lists are attached and not accidentally removed during policy edits.
- **CloudWatch metrics enhancement (2024):** New per-rule-group metrics
  (`DroppedPackets`, `PassedPackets` per rule group) for granular visibility.
  Auditors should verify CloudWatch alarms are configured on key metrics.
- **Firewall policy versioning visibility (2025):** Improved
  `DescribeFirewallPolicy` response includes `LastModifiedTime`. Auditors
  should flag policies not modified in > 90 days for rule freshness review.

## Domain

AWS CloudOps / Network Security & Intrusion Prevention.

## AWS documentation

- **AWS Network Firewall Developer Guide** — https://docs.aws.amazon.com/network-firewall/latest/developerguide/
- **Network Firewall security chapter** — https://docs.aws.amazon.com/network-firewall/latest/developerguide/security.html
- **Network Firewall API Reference** — https://docs.aws.amazon.com/network-firewall/latest/APIReference/
- **AWS CLI Network Firewall reference** — https://docs.aws.amazon.com/cli/latest/reference/network-firewall/
- **Suricata rule syntax (AWS-managed engine)** — https://docs.aws.amazon.com/network-firewall/latest/developerguide/suricata-rule-evaluation.html
- **TLS inspection configuration** — https://docs.aws.amazon.com/network-firewall/latest/developerguide/tls-inspection.html
