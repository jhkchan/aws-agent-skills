# Advanced patterns — network-firewall-rule-auditor

Expert Network Firewall behaviors, edge-case catalog, and recent AWS features, moved verbatim from SKILL.md (load on demand).

## Step 0: Expert knowledge — non-obvious Network Firewall behaviors

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

- **`describe-firewall` does NOT return the policy body.** The response
  carries `FirewallPolicyArn` (a reference) and `SubnetMappings`, but NOT the
  ruleset. An auditor who calls only `describe-firewall` and treats the
  response as the audit surface will silently produce an empty audit. Always
  follow with `describe-firewall-policy --firewall-policy-arn <arn>` and
  `describe-rule-group` per attached group; this is the #1 script bug in
  community Network Firewall tooling.

- **A Suricata `pass` rule is absolute, even under `drop_strict`.** The
  stateful default only governs traffic that NO rule matched. A matching
  `pass` rule short-circuits evaluation for that flow — the default never
  runs. Operators frequently tighten the default to `drop_strict` and assume
  it overrides a stale `pass`; it does not. Remove or scope the `pass` rule;
  the default is not a safety net.

- **TLS inspection scope (`ServerCertificateConfiguration.Scopes`) controls
  WHICH TLS flows are decrypted, not just whether.** An over-narrow scope
  (e.g., a single spoke subnet CIDR) silently leaves most HTTPS traffic
  uninspected — the TLS config exists and the policy references it, but the
  bulk of flows bypass decryption. Verify the scope covers EVERY workload
  subnet the firewall is supposed to protect, not just that the ARN is
  attached.

- **`StatefulEngineOptions.RuleOrder` at the policy level overrides per-group
  `RuleOrder`.** If the policy sets `STRICT_ORDER` globally, changing an
  individual stateful rule group to `DEFAULT_ACTION_ORDER` has no effect —
  the policy enforces strict order globally. Always check `StatefulEngineOptions`
  before diagnosing shadowing issues; per-group settings can be silently
  overridden and produce misleading audit results.

- **Stateless rules referencing a managed prefix list silently no-match if the
  prefix list is missing, in another Region, or owned by another account.**
  `update-rule-group` accepts the reference without warning; the rule simply
  never matches traffic. AWS does NOT surface this in the API response — the
  only signal is `MatchedPackets` staying at zero for that rule. Treat any
  `Source.PrefixListId` / `Destination.PrefixListId` reference as suspect
  until the prefix list is confirmed resolvable in the firewall's account and
  Region.

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

## Changelog — Recent AWS features (2024-2026)

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
