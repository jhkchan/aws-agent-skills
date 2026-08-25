---
name: directconnect-auditor
description: Audits AWS Direct Connect (DX) topology for resilience and security posture — physical-layer redundancy (2+ connections at diverse DX locations, not the same POP), MACSec link encryption on capable hardware, BGP peer authentication (especially on public VIFs where route hijack is trivial), virtual-interface redundancy across diverse connections via a Direct Connect Gateway, and LOA-CFA provisioning state. Emits a deterministic verdict (SINGLE_CONNECTION | NO_ENCRYPTION | CONFIG_GAP | OK) per topology with enumerated findings and specific CLI remediation. Use when reviewing Direct Connect connections, checking for single-path failure risk, validating MACSec enforcement, auditing BGP auth on public VIFs, or hardening hybrid-network posture before production cutover.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline topology classification from describe-connections / describe-virtual-interfaces JSON output. Live-account audits use aws directconnect describe-connections, describe-virtual-interfaces, describe-lags, describe-connection-loa, and describe-bgp-peers (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Networking
  verdict_shape: SINGLE_CONNECTION | NO_ENCRYPTION | CONFIG_GAP | OK
  when_to_use: Reviewing Direct Connect topology before production cutover, checking for single-path or single-facility failure risk, validating MACSec enforcement on capable hardware, auditing BGP peer auth on public VIFs (route-hijack defence), confirming LOA-CFA issuance for connections stuck in requested, or hardening hybrid-network resilience across regions.
  activation_triggers: audit this Direct Connect connection, is my DX redundant, MACSec check Direct Connect, BGP auth public VIF, LOA stuck pending, diverse location Direct Connect, single path failure risk DX, route hijack public VIF, LAG redundancy audit, Direct Connect Gateway failover
  invocation_schema: 'Input: either (a) describe-connections + describe-virtual-interfaces JSON (optionally paired with describe-lags and describe-connection-loa output), OR (b) a connection-id or LAG-id for live-account audit. Output: deterministic CONNECTION/VERDICT/REASON/FINDINGS/REMEDIATION block per topology, where VERDICT ∈ {SINGLE_CONNECTION, NO_ENCRYPTION, CONFIG_GAP, OK, ERROR}.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Direct Connect, DX, MACSec, BGP, virtual interface, private VIF, public VIF, transit VIF, LOA-CFA, redundancy, diverse location, Link Aggregation Group, LAG, Direct Connect Gateway, DXGW, route hijack, BGP MD5, hybrid networking, link encryption, 802.1AE, transit gateway, hybrid DC
  tags: directconnect, networking, macsec, bgp, redundancy, encryption, loa, audit
---

# Direct Connect Auditor

## Quick start

Verdict is the worst finding across four ordered dimensions:
`SINGLE_CONNECTION > NO_ENCRYPTION > CONFIG_GAP > OK`. Run them in order,
stop at the first non-OK verdict.

1. **Redundancy:** 2+ diversity units (a LAG counts as ONE unit) at **distinct
   `locationCode`s** — else `SINGLE_CONNECTION`. Two connections at the same
   POP are pseudo-diversity.
2. **MACSec:** dedicated, MACSec-capable connection with `encryptionMode`
   `no_encrypt` or `should_encrypt` — `NO_ENCRYPTION`. Skip hosted connections
   (hardware-ineligible).
3. **BGP / LOA / VIF:** public VIF without MD5, private ASN on public VIF, BGP
   `down` on `available`, LOA stuck `requested` >5 business days, single VIF
   on a single connection — `CONFIG_GAP`.
4. **OK:** all four dimensions pass.

The full severity matrix, per-field edge-case resolution, and the pre-flight
metadata gate live in the **Reference** section at the end of this document.
Expert knowledge deltas and the canonical checklist are inline below.

## Critical rules — read first

Four invariants that change the verdict if missed; each is expanded with full
context in the referenced section below.

- **Confirmation gate mandatory** before any state-changing CLI — DX is
  physical-layer, a mistake drops all hybrid traffic (Pre-flight safety
  checks).
- **Diversity is `locationCode`-based, not count-based** — two connections at
  the same POP are pseudo-diversity, a LAG is one unit (Step 1).
- **`bgpAuthKey` is write-only (always null), `should_encrypt` silently
  downgrades to plaintext, hosted connections cannot run MACSec** — these
  three produce the most false positives (Steps 0, 2, 3a).
- **BGP auth requires VIF re-creation, provisioning takes weeks** — never
  auto-execute remediation (Step 3a, Pre-flight safety checks).

## Mindset

**One-line takeaway:** the verdict is always the **worst** finding across four
ordered dimensions, and the single most common misclassification is treating
"two connections" as redundancy without checking they terminate at **different
DX locations** — two cross-connects into the same POP fall together in any
facility-level event (power, cooling, fibre-cut on the building's meet-me-room).

Direct Connect is a **physical-layer** service: a fibre cross-connect from a
customer cage (or partner cage) into an AWS DX patch panel at a colocation
facility. Everything above layer-2 rides on that physical path.
- **A single connection is a single point of failure** for the entire hybrid
  network, regardless of how many VIFs ride on it. LAG within one facility
  adds interface resilience but not facility resilience.
- **MACSec (IEEE 802.1AE)** is link-level encryption. When `encryptionMode` is
  `should_encrypt` instead of `must_encrypt`, the link falls back to plaintext
  the moment a MACSec peer fails to negotiate — silent downgrade, no CloudWatch
  alarm by default.
- **BGP on a public VIF without MD5 auth is a route-hijack vector.** The public
  Internet routing ecosystem treats the advertised prefix as authoritative; a
  missing `bgpAuthKey` on a public VIF lets any peer that compromises the
  session inject more-specific routes that attract traffic.
- **A Direct Connect Gateway is the unit of multi-region VIF failover.** A VIF
  attached to a single Virtual Private Gateway is pinned to one VPC and one
  region — failover requires a second VIF on a second, diverse connection.

## Quick reference — severity thresholds

Apply the steps in order. The verdict is the **worst** finding, where
`SINGLE_CONNECTION > NO_ENCRYPTION > CONFIG_GAP > OK`. The full condition →
verdict → step matrix is in **Reference — Severity matrix** at the end of
this document.

## Pre-flight: connection metadata gate

Several attributes **short-circuit** the audit — misclassifying them produces
false positives. The full per-attribute and per-field resolution tables are in
**Reference — Metadata gate** and **Reference — Edge-case field handling** at
the end of this document. The short list every auditor must apply before
stepping into Step 1:

- `lagId` set → connection is a LAG **member**, not standalone; audit the LAG.
- `bandwidth` `1Gbps`/`2Gbps`/`5Gbps`/`50-500Mbps` → hosted connection,
  MACSec not supported (hardware gate, not a posture gap).
- `connectionMode: transit` → APN-partner-owned port; MACSec is the partner's
  responsibility, flag `macSecCapable: false` as N/A.
- `hasLogicalRedundancy: yes` → LAG-level port redundancy **inside one
  location**, NOT facility diversity.
- `connectionState: down` → physical link down; treat as CONFIG_GAP if any
  other path is available, SINGLE_CONNECTION if this is the only path.

Live-account pagination note and canonical enumeration commands (unfiltered describe-connections / describe-virtual-interfaces / describe-lags; no NextToken, cross-account truncation at 1,000) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load it before fetching live-account topology.

Malformed-topology ERROR-verdict output block (invalid JSON, missing connectionId, missing virtualInterfaceId) moved verbatim to [references/error-handling.md](references/error-handling.md).
Load it when the input JSON fails the malformed gate in the Canonical checklist.

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious DX behaviours that change classification

Step 0 expert knowledge — all nineteen non-obvious DX behaviours (same-POP pseudo-diversity, LAG as one unit, hosted-connection MACSec gate, should_encrypt silent downgrade, write-only bgpAuthKey, public-VIF MD5, private-ASN filtering, MTU 9001 public-VIF cap, VIF redundancy via diverse connections, DXGW multi-region lift, LOA-CFA time bounds, ConnectionState authority, 30-association DXGW limit, asynchronous DXGW route propagation, BGP graceful restart, cross-account assumed-role enumeration, port-based billing of down connections, MACSec CAK/CKN overlap rotation, locationCode vs physical building) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load it before classifying any non-trivial topology.

### Step 1: Redundancy audit (SINGLE_CONNECTION — highest priority)

For each LAG (from `describe-lags`) and each standalone connection (not a LAG
member), enumerate the **diversity unit**:

1. **Build the diversity set.** For each LAG, the diversity unit is the LAG
   itself (location = LAG's `locationCode`, ignore member locations — they are
   identical). For each standalone connection, the unit is the connection
   itself with its own `locationCode`. Count diversity units, NOT individual
   connections.

2. **Check state.** Only count diversity units in `available` state (or LAGs
   with `lagState: available`). Units in `requested`/`pending`/`down` are not
   carrying production traffic; flag them as separate CONFIG_GAP findings but
   exclude from the redundancy count.

3. **Group by `locationCode`.** Two diversity units at the same location are
   **not diverse** — they share facility risk.

4. **Verdict:**
   - **<2 available diversity units at distinct locations** →
     **SINGLE_CONNECTION** (HIGH). The topology has a single failure domain
     for the entire hybrid network.
   - **2+ available diversity units, but all share one location** →
     **SINGLE_CONNECTION** (HIGH). Pseudo-diversity — same-facility risk.
   - **2+ available diversity units at ≥2 distinct locations** → proceed to
     Step 2.

**Special case — single LAG at one location, single standalone at another:**
this IS diverse (2 distinct locations). A common design is "primary LAG +
diverse standalone backup" — exactly the AWS Resilient Hybrid Architecture
reference pattern.

### Step 2: MACSec encryption audit (NO_ENCRYPTION)

For each **diversity unit** that passed Step 1:

1. **Gate on hardware eligibility.** Skip MACSec audit for:
   - Hosted connections (`bandwidth: 1Gbps`, `2Gbps`, `5Gbps`, or sub-1Gbps).
   - Any connection where `macSecCapable: false` AND `bandwidth` is a hosted
     tier — capability is a hardware constraint.
   - `connectionMode: transit` (partner-owned port; MACSec is the partner's
     responsibility).

2. **Check `macSecCapable`.** If `true`, MACSec is supported at this location
   and bandwidth. If `false` on a dedicated 10/100 Gbps connection, the
   location is not MACSec-enabled — flag as CONFIG_GAP (consider IPsec overlay
   or relocation to a MACSec-capable POP), not NO_ENCRYPTION.

3. **Check `encryptionMode`** for each `macSecCapable: true` connection:
   - `must_encrypt` → OK for this dimension.
   - `should_encrypt` → **NO_ENCRYPTION** (HIGH). Silent-downgrade capable.
     A misconfigured CE drops MACSec without operator action.
   - `no_encrypt` → **NO_ENCRYPTION** (HIGH). MACSec disabled on capable
     hardware.

4. **Verdict:** any single connection triggering NO_ENCRYPTION makes the
   topology NO_ENCRYPTION (the cleartext path is the weakest link).

### Step 3: BGP / LOA / VIF audit (CONFIG_GAP)

Run these only if Step 1 and Step 2 passed.

#### Step 3a: BGP auth on public VIFs

For each VIF with `virtualInterfaceType: public`:
- Check the authoritative BGP peer state (from `describe-bgp-peers`, or the
  input's explicit `authKeyState` / `authKey`-at-creation marker). **Do NOT
  use the `bgpAuthKey: null` field from describe-virtual-interfaces — it is
  write-only and always null** (Step 0). If auth was never configured
  (`authKeyState: never-configured-at-creation`, or no auth key supplied in
  the original create-VIF call) → **CONFIG_GAP** (MEDIUM). Public prefix
  advertisement without BGP auth is a route-hijack vector.
- Check `customerPeerAsn`: if it falls in the private ASN range
  (64512-65534 or 4200000000-4294967294) on a public VIF, AWS will filter
  the routes → **CONFIG_GAP** (MEDIUM). Routes are silently dropped.
- Check `mtu`: if `9001` on a public VIF → **CONFIG_GAP** (LOW). AWS caps
  at 1500; jumbo fragments.

For each VIF (any type) with `bgpPeers[].bgpStatus: down` on an
`available` connection → **CONFIG_GAP** (MEDIUM). BGP session down on an
available link is a control-plane outage.

#### Step 3b: VIF redundancy

For each private/transit VIF:
- If only one VIF exists in the topology, and it rides on a single
  connection (even if the connection is a diverse-location pair), there is
  no VIF-level failover → **CONFIG_GAP** (MEDIUM). One VIF on one
  connection is a control-plane single point of failure.
- If two VIFs exist but both ride the same connection, same failure domain
  → **CONFIG_GAP** (MEDIUM).
- If two VIFs ride diverse connections but neither is attached to a DXGW,
  failover is regional-only (each VIF is pinned to one VGW) → CONFIG_GAP
  (LOW). Multi-region failover requires a DXGW.

#### Step 3c: LOA-CFA provisioning state

For each connection in `connectionState: requested`:
- If held in `requested` for >5 business days without a retrievable LOA-CFA
  (`describe-connection-loa --connection-id <id>` returns an error or empty
  response), the partner cannot cross-connect → **CONFIG_GAP** (MEDIUM).
  This is a provisioning blocker.

For each connection in `connectionState: pending` for >10 business days:
- The cross-connect is in progress; >10 business days suggests a partner
  delay → **CONFIG_GAP** (LOW).

### Step 4: Aggregation — worst finding wins

```text
verdict = max(all_redundancy_findings,
              all_encryption_findings,
              all_config_gap_findings,
              OK)
```

Priority: SINGLE_CONNECTION > NO_ENCRYPTION > CONFIG_GAP > OK.

## Canonical checklist (run in this order)

A single sequential list the auditor follows top-to-bottom for every topology.
Each step either sets the verdict (worst-so-far wins) or moves on.

1. **Fetch (no `--connection-id` filter):**
   `describe-connections` → `describe-virtual-interfaces` → `describe-lags`.
   If a public VIF is present, also `describe-bgp-peers --virtual-interface-id`
   per VIF (the authoritative authKey source).
2. **Malformed JSON gate:** invalid JSON, missing `connectionId`, or missing
   `virtualInterfaceId` → emit `VERDICT: ERROR` and stop.
3. **Metadata gate (per Reference — Metadata gate):** classify each connection
   as LAG-member / hosted / dedicated, and each `connectionState`.
4. **Step 1 — Redundancy:** group diversity units by `locationCode`.
   Verdict moves to `SINGLE_CONNECTION` if <2 units at distinct codes.
5. **Step 2 — MACSec:** for each dedicated MACSec-capable unit, check
   `encryptionMode`. Verdict moves to `NO_ENCRYPTION` on `no_encrypt` or
   `should_encrypt`.
6. **Step 3a — BGP auth (public VIFs):** never use the write-only
   `bgpAuthKey`; use `authKeyState` from `describe-bgp-peers`. Missing auth
   on a public VIF → verdict moves to `CONFIG_GAP`.
7. **Step 3b — BGP session state:** any `bgpStatus: down` on an `available`
   connection → `CONFIG_GAP`.
8. **Step 3c — LOA:** `requested` >5 business days with no LOA-CFA, or
   `pending` >10 business days → `CONFIG_GAP`.
9. **Step 3d — VIF redundancy:** single VIF on a single connection, or two
   VIFs without a DXGW attachment → `CONFIG_GAP`.
10. **Step 4 — Aggregate:** worst-so-far wins. If nothing fired, emit `OK`.

## Output format (per topology)

```text
CONNECTION: <primary connection-id or LAG-id>
VERDICT: SINGLE_CONNECTION | NO_ENCRYPTION | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its step number>
FINDINGS:
  - [HIGH] <finding description (Step N)>
  - [MEDIUM] <finding description (Step N)>
  - [OK] <dimension that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Failure handling — partial API failures and missing fields

Partial API failure and missing-field fallback table (describe-bgp-peers throttling, empty peers array, absent offline fields, LOA errors, mid-stream truncation) moved verbatim to [references/error-handling.md](references/error-handling.md).
Load it when any describe-* call fails or a required field is absent.

**Single-summary rule:** emit exactly ONE `CONNECTION / VERDICT / REASON /
FINDINGS / REMEDIATION` block per topology. Do not split findings across
multiple blocks — aggregate into one `FINDINGS:` list, ordered
`[HIGH] → [MEDIUM] → [LOW] → [OK]`.

### Worked example — pseudo-diversity with BGP gap

```text
CONNECTION: dxcon-primary (LAG dxlag-prod)
VERDICT: SINGLE_CONNECTION
REASON: Both diversity units (LAG dxlag-prod at EqSE2, standalone dxcon-backup
at EqSE2) share location EqSE2 — facility-level event takes both down (Step 1).
BGP peer on VIF dxvif-public-prod is missing bgpAuthKey (Step 3a, would be
CONFIG_GAP if redundancy were addressed).
FINDINGS:
  - [HIGH] Both connections terminate at location EqSE2 — pseudo-diversity, no
    facility resilience (Step 1)
  - [MEDIUM] Public VIF dxvif-public-prod has no BGP MD5 auth — route-hijack
    vector (Step 3a)
  - [OK] MACSec must_encrypt enabled on both capable connections
REMEDIATION:
  1. Provision a third connection at a different DX location (e.g., EqDC2 or
     any location with a different facility code). Migrate the backup VIF
     there.
  2. Add BGP MD5: re-create the public VIF with --auth-key, or migrate to a
     new VIF with auth. Existing VIFs cannot have auth added in-place.
```

### Worked example — malformed topology (ERROR)

Worked example — malformed topology (ERROR) moved verbatim to [references/worked-examples.md](references/worked-examples.md); the primary pseudo-diversity worked example stays inline.
Load it when exercising the ERROR path.

## Anti-Patterns — NEVER

- NEVER treat "two connections" as redundant without comparing `locationCode`.
  Two connections at `EqSE2` are one fibre-cut away from simultaneous failure.
  The diversity check is **location-based**, not count-based.

- NEVER count LAG members as independent diversity units. A LAG is one logical
  connection at one location; member links share the AWS patch panel and
  facility. Count the LAG, not the members.

- NEVER flag `macSecCapable: false` on a **hosted connection** (1Gbps / 2Gbps
  / 5Gbps / sub-1Gbps partner offerings) as NO_ENCRYPTION. MACSec is a
  hardware-feature gate — hosted connections physically cannot run 802.1AE.
  The remediation is IPsec, not "enable MACSec."

- NEVER flag `bgpAuthKey: null` from `describe-virtual-interfaces` as missing
  auth. The field is write-only — AWS returns null for every existing VIF
  regardless of configuration. Use `describe-bgp-peers --virtual-interface-id
  <id>` for the authoritative peer state, or infer from the input's
  `bgpPeers[].authKey` if supplied.

- NEVER treat `encryptionMode: should_encrypt` as equivalent to
  `must_encrypt`. `should_encrypt` permits silent downgrade to plaintext when
  the peer fails to negotiate MACSec — it is operationally cleartext-capable.
  Classify as NO_ENCRYPTION.

- NEVER assume `hasLogicalRedundancy: yes` means facility diversity. It
  indicates LAG-level port redundancy **within one location**. The flag is
  AWS-populated, not a guarantee of POP-level resilience.

- NEVER conclude a connection is `available` from CloudWatch metrics alone.
  `ConnectionState` is the authoritative state; throughput metrics can lag
  or persist briefly after a flap. Always cross-reference the
  `connectionState` field from `describe-connections`.

- NEVER recommend deleting a hosted connection to "enable MACSec." Hosted
  connections are partner-billed and have contract terms; the MACSec gap is
  remediated via IPsec overlay (transit-gateway IPsec, site-to-site VPN) or
  by procuring a dedicated port — not by deleting the hosted connection.

- NEVER recommend BGP MD5 remediation as "add the key to the existing VIF."
  BGP auth cannot be modified in-place; the VIF must be re-created (or a new
  VIF provisioned and the old one decommissioned after traffic cutover).
  Always include the cutover step in the remediation.

- NEVER flag a public VIF with a private ASN (64512-65534) as a security
  issue — it is a **routing-acceptance** issue. AWS silently filters the
  routes; the prefix is not advertised. The remediation is to obtain a
  public ASN from a RIR or use the AWS-provided ASN if eligible.

- NEVER overlook a public VIF without BGP auth. Public prefix advertisement
  without MD5 is a route-hijack vector — a more-specific prefix from a
  spoofed peer attracts traffic from the global Internet. This is
  CONFIG_GAP at minimum; CRITICAL-tier concern for any prefix in the global
  routing table.

- NEVER assume a DXGW propagates VIF failover automatically without
  route-table configuration. The DXGW has its own route table; VIF failover
  depends on AS-path prepending or local-pref tuning on the CE side.
  Flag missing route-pref config as CONFIG_GAP (LOW).

- NEVER assume a DXGW association is active immediately after creation.
  `create-direct-connect-gateway-association` is asynchronous; the route
  table on the VGW/TGW side does not update until the association reaches
  `associated` state. Emit `describe-direct-connect-gateway-attachments`
  and verify state before declaring failover ready. A VIF riding on a
  `pending` association has no route propagation — traffic black-holes.

- NEVER leave an old VIF active after re-creating it for BGP auth or MACSec
  remediation. Two VIFs advertising the same prefix from the same connection
  cause route oscillation and unpredictable path selection. After the new
  VIF is verified up and routes are migrated, the old VIF MUST be deleted
  (`delete-virtual-interface`) — or at minimum its BGP session shut — before
  declaring the remediation complete. Forgetting this step is the #1 cause
  of post-remediation asymmetric routing.

- NEVER treat `directconnect describe-virtual-interfaces` (no filter) and
  `describe-virtual-interfaces --connection-id <id>` as equivalent. The
  filtered call misses VIFs whose underlying connection was swapped during
  a maintenance event or a VIF migration — the VIF retains its original
  `virtualInterfaceId` but its `connectionId` now points at the new
  connection. The filtered listing silently returns nothing for that VIF,
  producing a false "no VIFs here" verdict. The unfiltered call is the
  only complete listing. Always use the unfiltered form for audit, then
  correlate by `connectionId` in post-processing.

- NEVER flag a connection in `requested` for fewer than 5 business days as a
  LOA blocker. AWS SLA for LOA issuance is 72 hours; partner-side cross-
  connect adds 2 business days. Allow 5 business days before raising.

## Pre-flight safety checks (run before any remediation CLI)

Pre-flight safety checks (CONFIRM gate, VIF re-creation backup, MACSec both-ends readiness, weeks-long provisioning lead time, DXGW global-vs-regional scope, non-disruptive BGP re-key via VIF migration) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load them before emitting or executing any remediation CLI.

## Remediation guidance

Full per-verdict remediation playbooks with CLI (SINGLE_CONNECTION diverse-location provisioning, NO_ENCRYPTION MACSec/IPsec, CONFIG_GAP BGP auth via VIF re-creation / LOA re-request / DXGW failover, OK monitoring recommendations) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load the matching playbook once the verdict is decided.

## Recent AWS features (2024-2026)

Recent AWS features (2024-2026) — MACsec GA expansion, enhanced CloudWatch DX metrics, DX Gateway enhancements — moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load it when re-checking previously non-MACsec-capable connections.

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — Step 0 expert-knowledge deep dive, per-verdict remediation playbooks, metadata-gate and edge-case field tables, Recent AWS features (2024-2026) moved from SKILL.md
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — canonical enumeration/pagination commands and pre-flight safety checks moved from SKILL.md
- [references/error-handling.md](references/error-handling.md) — malformed-topology ERROR block and partial API failure fallback table moved from SKILL.md
- [references/worked-examples.md](references/worked-examples.md) — malformed-topology (ERROR) worked example moved from SKILL.md; the primary pseudo-diversity example stays in SKILL.md

## Domain

AWS CloudOps / Hybrid Networking Resilience & Compliance.

## Reference — Severity matrix

Full condition → verdict → step mapping. Apply in order; the verdict is the
**worst** finding, where `SINGLE_CONNECTION > NO_ENCRYPTION > CONFIG_GAP > OK`.

| Condition | Verdict | Step |
|---|---|---|
| <2 connections at **diverse** DX locations (`locationCode`) | **SINGLE_CONNECTION** | 1 |
| LAG with all member connections at the same `locationCode` | **SINGLE_CONNECTION** | 1 |
| 2 connections at the same `locationCode` (pseudo-diversity) | **SINGLE_CONNECTION** | 1 |
| Dedicated connection, `macSecCapable: true`, `encryptionMode: no_encrypt` | **NO_ENCRYPTION** | 2 |
| Dedicated connection, `macSecCapable: true`, `encryptionMode: should_encrypt` | **NO_ENCRYPTION** | 2 (silent-downgrade risk) |
| Public VIF with no `bgpAuthKey` set (use `authKeyState`, not the write-only field) | **CONFIG_GAP** | 3a |
| BGP peer `bgpStatus: down` on an `available` connection | **CONFIG_GAP** | 3b |
| Connection `state: requested` >5 business days with no LOA-CFA | **CONFIG_GAP** | 3c |
| Single private VIF on a single connection (no DXGW failover) | **CONFIG_GAP** | 3d |
| 2+ diverse connections, MACSec `must_encrypt` (or N/A hosted), BGP auth on all public VIFs, valid LOA or `available` | **OK** | 4 |

## Reference — Metadata gate

Full per-attribute metadata-gate table (lagId, connectionMode, bandwidth tiers, location, hasLogicalRedundancy, connectionState transitions) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md); the short list above stays inline.
Load it when a pre-flight attribute is set and ambiguous.

## Reference — Edge-case field handling

Edge-case field-handling table (authKeyState variants, missing or empty bgpPeers array, absent authKeyState in offline JSON) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load it when Step 3 fields are absent, redacted, or truncated.

## AWS documentation

- **AWS Direct Connect User Guide** — https://docs.aws.amazon.com/directconnect/latest/UserGuide/Welcome.html
- **Direct Connect Security** — https://docs.aws.amazon.com/directconnect/latest/UserGuide/security.html
- **Direct Connect API Reference** — https://docs.aws.amazon.com/directconnect/latest/APIReference/
- **AWS CLI Command Reference (directconnect)** — https://docs.aws.amazon.com/cli/latest/reference/directconnect/
- **MACsec for Direct Connect** — https://docs.aws.amazon.com/directconnect/latest/UserGuide/direct-connect-macsec.html
