---
name: network-firewall-rule-auditor
description: Audits AWS Network Firewall configurations for permissive stateful and stateless rules, missing TLS inspection, firewall-subnet routing gaps that bypass inspection, rule-group evaluation-order shadowing, and logging blind spots. Emits a deterministic verdict (PERMISSIVE_RULE | NO_TLS_INSPECTION | ROUTING_GAP | CONFIG_GAP | OK) per firewall with enumerated findings and specific CLI remediation. Use when reviewing Network Firewall policies, checking for wildcard pass rules, validating TLS inspection coverage, auditing firewall route tables, or verifying rule-group evaluation order before production deployment.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline policy-document classification. Live-account audits use aws network-firewall describe-firewall, describe-firewall-policy, describe-rule-group, describe-logging-configuration, describe-tls-inspection-config, and aws ec2 describe-route-tables (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Security
  verdict_shape: PERMISSIVE_RULE | NO_TLS_INSPECTION | ROUTING_GAP | CONFIG_GAP | OK
  when_to_use: Reviewing a Network Firewall policy before production deployment, checking for permissive stateful or stateless rules, validating TLS inspection coverage, auditing firewall subnet route tables for traffic-bypass gaps, verifying rule-group evaluation order, or hardening intrusion-prevention posture across a VPC.
  activation_triggers: audit this network firewall, check firewall rules, permissive firewall policy, is TLS inspection enabled, firewall routing gap, rule group evaluation order, stateless default actions, fragment bypass firewall, shadowed Suricata rules, HOME_NET misconfiguration
  invocation_schema: 'Input: either (a) a Network Firewall policy JSON (stateful + stateless rule groups, default actions), optionally paired with route-table data and TLS config, OR (b) a firewall-arn/name for live-account audit. Output: deterministic FIREWALL/VERDICT/REASON/FINDINGS/REMEDIATION block per firewall, where VERDICT ∈ {PERMISSIVE_RULE, NO_TLS_INSPECTION, ROUTING_GAP, CONFIG_GAP, OK, ERROR}.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Network Firewall, stateful rules, stateless rules, Suricata, TLS inspection, firewall routing, rule group, StatelessDefaultActions, StatelessFragmentDefaultActions, StatefulDefaultActions, drop_strict, forward_to_sfe, HOME_NET, fragment bypass, shadowed rule, STRICT_ORDER, SNI, network firewall audit, intrusion prevention
  tags: network-firewall, security, stateful-rules, stateless-rules, tls-inspection, routing, suricata, audit
---

# Network Firewall Rule Auditor

## Quick-start (TL;DR)

**Use this skill when** auditing an AWS Network Firewall — the managed VPC-level
stateful/stateless inspection service (Suricata + 5-tuple engines in dedicated
firewall subnets). **Do NOT use it for** security groups, NACLs, WAF web ACLs,
Route 53 Resolver Firewall, or non-AWS firewalls — those have different
evaluation models and verdict labels.

**Five possible verdicts** (worst finding wins on aggregation):
- **PERMISSIVE_RULE** — a rule or default action actively allows/bypasses
  traffic that should be inspected or blocked. Highest urgency.
- **ROUTING_GAP** — VPC or TGW route tables steer traffic around the firewall;
  rules are irrelevant.
- **NO_TLS_INSPECTION** — payload-matching stateful rules cannot match HTTPS
  without a decryption config.
- **CONFIG_GAP** — functional defect (dead pass rule, missing logging,
  alert-only default, missing `forward_to_sfe`).
- **OK** — all dimensions clean.

**Three highest-signal checks** (cover ~80% of real misconfigurations):
1. `StatelessDefaultActions` includes `aws:forward_to_sfe` — else every
   stateful rule group is dead code.
2. App-subnet route table points `0.0.0.0/0` at a firewall ENI, not the IGW.
3. No `pass ip any any -> any any` (Suricata) or all-wildcard 5-tuple +
   `aws:pass` (stateless) rule.

**Output contract:** emit one `FIREWALL / VERDICT / REASON / FINDINGS /
REMEDIATION` block per firewall. For multi-firewall inputs, emit one block per
firewall — do NOT merge findings across firewalls.

The full verdict matrix is in `Quick reference — verdict thresholds` below;
deep Suricata, routing, and API internals are in the **Reference** section at
the end.

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

→ Full Step-0 expert knowledge moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

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

### Multi-firewall inputs

When the input contains more than one firewall (e.g., a JSON array, a
spreadsheet export, or multiple ARNs), emit ONE verdict block per firewall.
Do NOT merge findings across firewalls — a shared policy is not a signal to
collapse verdicts. Process firewalls in input order; if two firewalls share a
policy, both still get independent blocks (the shared policy's defects appear
in each, with a `REMEDIATION` note flagging the blast radius).

For very large inputs (>20 firewalls), batch by VPC or account and warn the
operator that the run may exceed a single model response — emit a final
`VERDICT: ERROR` summary block with the count of unprocessed firewalls
rather than silently truncating.

### Pagination retry / backoff

→ Retry/backoff details moved verbatim to [references/error-handling.md](references/error-handling.md).

## Expert edge cases

→ Edge-case catalog moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

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

- NEVER pin to "the latest" AWS-managed rule group without recording the
  version. Managed groups (ThreatSignatures, domain lists) update
  independently; a passing audit today can fail tomorrow when the managed
  group adds rules that interact with custom rules. Capture the managed
  group's version / `LastModifiedTime` in the audit output for
  reproducibility, and flag managed-group version drift between audits.

- NEVER assume egress is inspected just because ingress is. Many policies
  scope rules tightly for inbound traffic but ship a `pass ip $HOME_NET any
  -> $EXTERNAL_NET any` baseline for outbound — data exfiltration and C2
  callbacks egress uninspected. Evaluate egress rules with the same rigor as
  ingress; a permissive egress baseline is PERMISSIVE_RULE, not OK.

## Pre-flight safety checks (run before any remediation CLI)

→ Pre-flight safety command gates moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).

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

→ API error table moved verbatim to [references/error-handling.md](references/error-handling.md).

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — Step-0 expert knowledge, expert edge cases, recent AWS features 2024-2026
- [references/error-handling.md](references/error-handling.md) — pagination retry/backoff, remediation API error table
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — pre-flight safety gates and backup CLI

## Domain

AWS CloudOps / Network Security & Intrusion Prevention.

## AWS documentation

- **AWS Network Firewall Developer Guide** — https://docs.aws.amazon.com/network-firewall/latest/developerguide/
- **Network Firewall security chapter** — https://docs.aws.amazon.com/network-firewall/latest/developerguide/security.html
- **Network Firewall API Reference** — https://docs.aws.amazon.com/network-firewall/latest/APIReference/
- **AWS CLI Network Firewall reference** — https://docs.aws.amazon.com/cli/latest/reference/network-firewall/
- **Suricata rule syntax (AWS-managed engine)** — https://docs.aws.amazon.com/network-firewall/latest/developerguide/suricata-rule-evaluation.html
- **TLS inspection configuration** — https://docs.aws.amazon.com/network-firewall/latest/developerguide/tls-inspection.html

## Changelog — Recent AWS features (2024-2026)

→ Recent AWS features moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
