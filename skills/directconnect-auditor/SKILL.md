---
name: directconnect-auditor
description: >-
  Audits AWS Direct Connect (DX) topology for resilience and security posture —
  physical-layer redundancy (2+ connections at diverse DX locations, not the
  same POP), MACSec link encryption on capable hardware, BGP peer
  authentication (especially on public VIFs where route hijack is trivial),
  virtual-interface redundancy across diverse connections via a Direct Connect
  Gateway, and LOA-CFA provisioning state. Emits a deterministic verdict
  (SINGLE_CONNECTION | NO_ENCRYPTION | CONFIG_GAP | OK) per topology with
  enumerated findings and specific CLI remediation. Use when reviewing Direct
  Connect connections, checking for single-path failure risk, validating MACSec
  enforcement, auditing BGP auth on public VIFs, or hardening hybrid-network
  posture before production cutover.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline topology classification from
  describe-connections / describe-virtual-interfaces JSON output. Live-account
  audits use aws directconnect describe-connections,
  describe-virtual-interfaces, describe-lags, describe-connection-loa, and
  describe-bgp-peers (AWS CLI v2, SSO or key-based credentials).
keywords:
  - Direct Connect
  - DX
  - MACSec
  - BGP
  - virtual interface
  - private VIF
  - public VIF
  - transit VIF
  - LOA-CFA
  - redundancy
  - diverse location
  - Link Aggregation Group
  - LAG
  - Direct Connect Gateway
  - DXGW
  - route hijack
  - BGP MD5
  - hybrid networking
  - link encryption
  - 802.1AE
  - transit gateway
  - hybrid DC
tags: [directconnect, networking, macsec, bgp, redundancy, encryption, loa, audit]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Networking
  verdict_shape: "SINGLE_CONNECTION | NO_ENCRYPTION | CONFIG_GAP | OK"
  when_to_use: >-
    Reviewing Direct Connect topology before production cutover, checking for
    single-path or single-facility failure risk, validating MACSec enforcement
    on capable hardware, auditing BGP peer auth on public VIFs (route-hijack
    defence), confirming LOA-CFA issuance for connections stuck in requested,
    or hardening hybrid-network resilience across regions.
  activation_triggers:
    - "audit this Direct Connect connection"
    - "is my DX redundant"
    - "MACSec check Direct Connect"
    - "BGP auth public VIF"
    - "LOA stuck pending"
    - "diverse location Direct Connect"
    - "single path failure risk DX"
    - "route hijack public VIF"
    - "LAG redundancy audit"
    - "Direct Connect Gateway failover"
  invocation_schema: >-
    Input: either (a) describe-connections + describe-virtual-interfaces JSON
    (optionally paired with describe-lags and describe-connection-loa output),
    OR (b) a connection-id or LAG-id for live-account audit. Output:
    deterministic CONNECTION/VERDICT/REASON/FINDINGS/REMEDIATION block per
    topology, where VERDICT ∈ {SINGLE_CONNECTION, NO_ENCRYPTION, CONFIG_GAP,
    OK, ERROR}.
---

# Direct Connect Auditor

## Quick start

Audit any Direct Connect topology in four ordered dimensions; the verdict is
the worst finding, ordered SINGLE_CONNECTION > NO_ENCRYPTION > CONFIG_GAP > OK.

1. **Redundancy (Step 1):** count diversity units (LAG = 1 unit) at **distinct
   `locationCode`s**. Two connections at the same POP are pseudo-diversity →
   SINGLE_CONNECTION.
2. **MACSec (Step 2):** for each MACSec-capable dedicated connection, check
   `encryptionMode`. `no_encrypt` or `should_encrypt` → NO_ENCRYPTION. Skip
   hosted connections (hardware-ineligible).
3. **BGP / LOA / VIF (Step 3):** public VIF without MD5 (use
   `authKeyState`, never the write-only `bgpAuthKey: null`), private ASN on
   public VIF, jumbo MTU on public VIF, BGP down on available, LOA stuck on
   `requested` >5 business days, single VIF on single connection → CONFIG_GAP.
4. **OK (Step 4):** 2+ diverse connections, MACSec `must_encrypt` (or N/A
   hosted), BGP auth on all public VIFs, redundant VIFs via DXGW.

For the full severity matrix, expert knowledge deltas, and per-verdict
remediation, see the sections below.

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

| Condition | Verdict | Rule |
|---|---|---|
| <2 connections at **diverse** DX locations (`locationCode`) | **SINGLE_CONNECTION** | Step 1 |
| LAG with all member connections at the same `locationCode` | **SINGLE_CONNECTION** | Step 1 |
| 2 connections at the same `locationCode` (pseudo-diversity) | **SINGLE_CONNECTION** | Step 1 |
| Dedicated connection, `macSecCapable: true`, `encryptionMode: no_encrypt` | **NO_ENCRYPTION** | Step 2 |
| Dedicated connection, `macSecCapable: true`, `encryptionMode: should_encrypt` | **NO_ENCRYPTION** | Step 2 (silent-downgrade risk) |
| Public VIF with no `bgpAuthKey` set | **CONFIG_GAP** | Step 3a |
| BGP peer `bgpStatus: down` on an `available` connection | **CONFIG_GAP** | Step 3b |
| Connection `state: requested` >5 business days with no LOA-CFA | **CONFIG_GAP** | Step 3c |
| Single private VIF on a single connection (no DXGW failover) | **CONFIG_GAP** | Step 3d |
| 2+ diverse connections, MACSec `must_encrypt` (or N/A hosted), BGP auth on all public VIFs, valid LOA or `available` | **OK** | Step 4 |

Apply the steps in order. The verdict is the **worst** finding, where
SINGLE_CONNECTION > NO_ENCRYPTION > CONFIG_GAP > OK.

## Pre-flight: connection metadata gate

Several attributes **short-circuit** the audit — misclassifying them produces
false positives that erode trust.

**Live-account pagination note:** `aws directconnect describe-connections`
returns at most 1 connection per call by default; use
`aws directconnect describe-connections` (plural, no `--connection-id`) to
list every connection in the account. For VIFs,
`describe-virtual-interfaces` without `--connection-id` is the only way to
catch every VIF — filtering by connection misses VIFs whose underlying
connection was swapped. Always drain pagination; DX has no `NextToken` for
these calls but cross-account listings do truncate at 1,000 objects.

| Attribute | Value | Effect on audit |
|---|---|---|
| `lagId` | set | Connection is a LAG **member**, not standalone. Audit the LAG (`describe-lags --lag-id <id>`) — the LAG is the redundancy unit, not the member. Member `locationCode` is identical to the LAG's; counting members as diverse connections is a false positive. |
| `connectionMode` | `transit` | Hosted-VIF connection from an APN partner. The partner owns the physical port; customer sees VIFs only. MACSec capability is set by the partner — flag `macSecCapable: false` as N/A, not a finding. |
| `bandwidth` | `1Gbps`, `2Gbps`, `5Gbps` | Hosted connection — **MACSec not supported.** Do NOT flag `encryptionMode: no_encrypt`; it is a hardware limit, not a posture choice. |
| `bandwidth` | `50Mbps`, `100Mbps`, `200Mbps`, `300Mbps`, `400Mbps`, `500Mbps` | Hosted connection (sub-1Gbps partner resold). Same MACSec N/A rule. |
| `bandwidth` | `10Gbps`, `100Gbps` dedicated | MACSec-capable **if** the location is MACSec-enabled. Audit encryption. |
| `location` | e.g. `EqSE2` | The location/POP code. Drives the diversity check (Step 1). Two connections at the same code share facility risk. |
| `hasLogicalRedundancy` | `yes` | AWS-populated flag for port-level LAG redundancy inside one location. **Does NOT imply location diversity.** A `yes` here is LAG-level, not facility-level. |
| `connectionState` | `requested` | Provisioning not started. Trigger LOA check (Step 3c). |
| `connectionState` | `pending` | LOA issued; cross-connect in progress. Outage if held >10 business days. |
| `connectionState` | `available` | Physical link up — proceed with full audit. |
| `connectionState` | `down` | Physical link down. Treat as CONFIG_GAP if other connections are available (traffic should have failed over); SINGLE_CONNECTION if this is the only path. |

**Edge-case field handling (resolves ambiguity in Step 3):**

| Field scenario | Interpretation | Action |
|---|---|---|
| `authKeyState: configured` (or input shows auth key was supplied at VIF creation) | BGP MD5 is set | OK for this check; do not flag. |
| `authKeyState: never-configured` (or field absent AND no auth key in creation input) on a **public VIF** | BGP MD5 was never set | CONFIG_GAP (MEDIUM) — route-hijack vector. Remediate via VIF re-creation with `--auth-key`. |
| `authKeyState: never-configured` on a **private/transit VIF** | No MD5 on a scoped VIF | CONFIG_GAP (LOW) — lower risk than public but still recommended. |
| `bgpPeers` array missing entirely from a VIF JSON | No BGP session defined — VIF is non-functional or data is incomplete | CONFIG_GAP (MEDIUM). Emit: `VIF <id> has no bgpPeers array — BGP state unverifiable. Re-fetch with describe-bgp-peers.` Do NOT assume auth is absent; the field may be missing due to truncated API output. |
| `bgpPeers` array present but empty `[]` | VIF exists but no BGP sessions configured | CONFIG_GAP (MEDIUM). A VIF without peers carries no traffic. Flag for operator review. |
| `authKeyState` field absent from input JSON (offline mode) | Cannot determine auth state from describe-virtual-interfaces alone | Infer from `bgpPeers[].authKey` presence in the input; if that is also absent, emit CONFIG_GAP (LOW) with note: `Auth state unverifiable from provided JSON — run describe-bgp-peers for authoritative check.` |

**If the topology JSON is malformed** (invalid JSON, missing `connectionId` on
a connection, missing `virtualInterfaceId` on a VIF), output:

```text
CONNECTION: <connection-id or unknown>
VERDICT: ERROR
REASON: Direct Connect topology JSON is malformed or missing required fields — cannot classify.
REMEDIATION: Re-fetch with aws directconnect describe-connections --output json and re-audit.
```

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious DX behaviours that change classification

These are the deltas a senior network engineer knows and a generalist misses:

- **Two connections at the same DX location are NOT diverse.** AWS publishes
  location codes per facility (e.g., `EqSE2` = Equinix SE2). Two connections
  into `EqSE2` share power, cooling, the meet-me-room, and the AWS patch panel.
  A single facility event takes both down. The diversity check MUST compare
  `location` codes, not connection counts. This is the #1 false-positive
  source for DX auditors.

- **A LAG is one logical connection at one location.** A LAG bundles N
  physical links via 802.3ad link aggregation into a single logical port. All
  members share the LAG's `locationCode` and the AWS-side patch panel. A
  LAG with 4 members is resilient to **port failure** but not to **facility
  failure**. The redundancy unit for facility diversity is the **LAG**, not
  the member.

- **Hosted connections cannot run MACSec.** Only dedicated connections at 10
  Gbps or 100 Gbps, terminated at MACSec-capable locations, support 802.1AE.
  A hosted connection (`bandwidth: 1Gbps`, `2Gbps`, `5Gbps`, or any sub-1Gbps
  partner offering) reporting `macSecCapable: false` is hardware-constrained,
  not a posture gap. Do NOT raise NO_ENCRYPTION on hosted connections — use
  IPsec (e.g., transit-gateway IPsec or a VPN overlay) for those.

- **`encryptionMode: should_encrypt` is operationally plaintext-capable.**
  AWS exposes three modes: `must_encrypt` (MACSec enforced — link drops if
  peer cannot negotiate), `should_encrypt` (MACSec preferred — falls back to
  plaintext if peer does not respond), `no_encrypt` (MACSec disabled). The
  `should_encrypt` mode is a silent-downgrade risk: a misconfigured CE router
  or a partner-side issue drops traffic to cleartext with no CloudWatch alarm
  unless `ConnectionEncryption` metric monitoring is set up. Treat as
  NO_ENCRYPTION for verdict purposes.

- **`bgpAuthKey` is write-only.** `describe-virtual-interfaces` returns
  `bgpAuthKey: null` for every existing VIF regardless of whether auth was
  configured at creation. **Do NOT flag a null `bgpAuthKey` as missing auth.**
  The authoritative check is `describe-bgp-peers --virtual-interface-id <id>`,
  whose response includes the configured auth key state via the peer config.
  For offline JSON, infer from the input's `bgpPeers` block; if the input
  shows the auth key was supplied at creation, the VIF has auth.

- **Public VIFs require BGP MD5 auth — route-hijack defence.** A public VIF
  advertises customer-owned public prefixes into the AWS backbone; without
  BGP MD5, any on-path attacker can spoof the peer and inject more-specific
  routes (classic BGP hijack). Treat a public VIF with no MD5 as CONFIG_GAP
  at minimum; CRITICAL-tier finding if the prefix is in the global routing
  table. Private VIFs are scoped to a VGW/DXGW and are lower (but not zero)
  risk.

- **Private ASN on a public VIF is filtered.** A customer ASN in the private
  range (64512-65534 for 2-byte, 4200000000-4294967294 for 4-byte) cannot
  advertise public prefixes via a public VIF — AWS route acceptance filters
  them. A public VIF with `customerPeerAsn: 64512` is a CONFIG_GAP: the
  routes you think you are advertising are silently dropped.

- **MTU 9001 is private-VIF only.** A jumbo MTU on a public VIF is capped at
  1500 by AWS; setting 9001 fragments outbound packets and inflates CloudWatch
  `ConnectionPpsEgress` without throughput gain. Treat as CONFIG_GAP.

- **VIF redundancy requires diverse connections, not just multiple VIFs.** Two
  private VIFs on the same underlying connection share the same failure
  domain. True failover requires one VIF per diverse connection, ideally via
  a DXGW so both VIFs advertise the same prefix set into the same route table.

- **A DXGW lifts the VIF-attached-VGW limitation.** Without a DXGW, a private
  VIF attaches to one VGW in one region — single-region. A DXGW allows a
  VIF to advertise prefixes into multiple VGWs across regions and (with
  Transit Gateway integration) into multiple TGWs. For multi-region HA, the
  DXGW is mandatory; without it, the design is regional-only.

- **LOA-CFA is per-connection and time-bounded.** `describe-connection-loa`
  returns the LOA-CFA (Letter of Authorization — Connecting Facility
  Assignment) as base64 PDF. A connection in `requested` state for >5
  business days without an LOA-CFA is a provisioning blocker — the partner
  cannot cross-connect. The LOA is valid for 60 days from issuance; an
  unsigned/expired LOA on a `pending` connection is a cross-connect blocker.

- **CloudWatch `ConnectionState` is authoritative; metrics lag.** When
  `connectionState: down` but `ConnectionBpsEgress: 0` persists, the link is
  down — do not wait for throughput metrics to confirm. The
  `ConnectionEncryption` metric tracks the count of MACSec-secured links; a
  drop below the negotiated S-Tag count on a `must_encrypt` LAG indicates
  MACSec degradation even when the LAG is `available`.

- **`directconnect-gateway` association limit is 30.** A DXGW supports up to
  30 VGW or TGW associations globally. HA designs that exceed this need
  multiple DXGWs; do not flag a high count as a posture issue per se, but
  flag if it limits failover paths.

- **DXGW route propagation is asynchronous — verify state before declaring
  failover ready.** `associate-direct-connect-gateway` returns immediately
  but the route table on the VGW/TGW side does not update until the
  association reaches `associated` state. A VIF riding a `pending`
  association has no route propagation — traffic black-holes. Always verify
  with `aws directconnect describe-direct-connect-gateway-attachments
  --direct-connect-gateway-id <id>` and confirm every attachment shows
  `attachmentState: associated` and `state: available` before declaring the
  topology production-ready. A `pending` or `available`-but-not-`associated`
  attachment is a silent CONFIG_GAP.

- **BGP graceful restart masks a down session.** When a BGP peer has
  `bgpStatus: down` but graceful restart (GR) is negotiated, the forwarding
  table retains stale routes for up to the restart-timeout (typically 120s
  for DX). A `down` peer with GR active may still forward traffic — briefly.
  Do NOT classify a GR-active down peer as healthy; classify it as
  CONFIG_GAP (MEDIUM) with a note that forwarding is grace-period-dependent.
  The authoritative check is `describe-bgp-peers` — if `bgpStatus: down` and
  the peer advertised GR capability, flag it but note the grace window.

- **Cross-account DX audits require assumed-role enumeration.** Hosted VIFs
  reside in the partner (APN) account; the end-customer account sees only
  the VIF, not the underlying connection's physical state. For a complete
  cross-account audit, assume the partner role (`sts assume-role`) and run
  `describe-connections` / `describe-lags` there, then correlate via
  `ownerAccount` on the hosted VIF. Without the partner-side view, MACSec
  and location diversity for hosted VIFs are unverifiable — flag as
  CONFIG_GAP (LOW) with a note that the partner account must be audited for
  full posture. Cross-account listings also truncate at 1,000 objects; use
  `--max-results` with pagination where available.

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

```text
CONNECTION: unknown
VERDICT: ERROR
REASON: Topology JSON is malformed — connection at index 2 is missing the
required `connectionId` field; cannot classify.
FINDINGS:
  - [ERROR] Connection at index 2 missing connectionId — skipped
REMEDIATION: Re-fetch with aws directconnect describe-connections --output json
and re-audit. If the issue persists, the API response was truncated mid-stream.
```

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
  filtered call misses VIFs whose underlying connection was swapped; the
  unfiltered call is the only complete listing. Always use the unfiltered
  form for audit.

- NEVER flag a connection in `requested` for fewer than 5 business days as a
  LOA blocker. AWS SLA for LOA issuance is 72 hours; partner-side cross-
  connect adds 2 business days. Allow 5 business days before raising.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (delete-connection, delete-virtual-interface, update-virtual-interface,
  associate-direct-connect-gateway, MACSec mode change), emit:
  `CONFIRM: About to <action> on <resource>. This affects <consequence>.
  Proceed? (yes/no)` — do NOT execute until the operator confirms. DX
  changes are physical-layer and affect all hybrid traffic.
- **Re-creating a VIF to add BGP auth is destructive.** Capture the current
  config first:
  `aws directconnect describe-virtual-interfaces --virtual-interface-id <id> --output json > /tmp/<id>-backup-$(date +%s).json`.
  VIF configs are not versioned; there is no undo without a backup.
- **MACSec mode change requires both ends.** Switching `no_encrypt` to
  `must_encrypt` requires the CE router to be MACSec-configured first;
  otherwise the link drops and ALL hybrid traffic fails. Confirm CE
  readiness before emitting `update-connection --encryption-mode must_encrypt`.
- **Provisioning a new diverse connection takes weeks.** Do NOT emit
  `create-connection` as an immediate remediation without surfacing the
  lead time. Partner cross-connects typically take 2-6 weeks; LOA issuance
  adds 3-5 business days. The remediation is correct but the operator must
  know the timeline.
- **Direct Connect Gateway creation is global but associations are regional.**
  `create-direct-connect-gateway` is a global call; associating a VGW is
  regional. A misconfigured association leaves the VIF unattached — verify
  with `describe-direct-connect-gateway-attachments` after creation.
- **BGP session re-key is non-disruptive if done via VIF migration.** Provision
  the new VIF with auth, verify BGP up, migrate routes via AS-path prepending,
  then delete the old VIF. Never delete the old VIF first.

## Remediation guidance

### For SINGLE_CONNECTION

1. Provision a new dedicated connection at a **different DX location**
   (different `locationCode`). The AWS Resilient Hybrid Architecture
   reference pattern: primary LAG + diverse standalone backup at a
   non-adjacent facility.
   ```bash
   aws directconnect create-connection --location EqDC2 --bandwidth 10Gbps \
     --connection-name dxcon-dr-backup
   ```
   Lead time: 2-6 weeks (partner cross-connect + LOA).
2. Migrate at least one VIF from the existing topology to the new connection.
   Prefer a DXGW-attached private VIF for multi-region failover.
3. If a new connection is not feasible (budget, geography), document the
   single-path risk and add IPsec VPN as a backup path over the public
   Internet (transit-gateway VPN or site-to-site).
4. Verify post-remediation:
   ```bash
   aws directconnect describe-connections --output json | \
     jq '.connections[] | {id: .connectionId, location: .location, state: .connectionState}'
   ```

### For NO_ENCRYPTION

1. Confirm the CE router supports MACSec (IEEE 802.1AE) and is configured for
   the AWS MACSec keys. Retrieve the AWS-side keys:
   ```bash
   aws directconnect describe-connections --connection-id <id> --output json | \
     jq '.connections[].macSecKeys'
   ```
   Two AWS-side keys are returned (CAK/CKN pairs); the CE must be configured
   with at least one.
2. Switch the encryption mode (CE must be MACSec-ready first):
   ```bash
   aws directconnect update-connection --connection-id <id> \
     --encryption-mode must_encrypt
   ```
3. For hosted connections that cannot run MACSec: deploy an IPsec overlay
   (transit-gateway IPsec, site-to-site VPN, or customer-managed IPsec on
   the CE). Treat the IPsec overlay as the encryption layer.
4. Verify:
   ```bash
   aws directconnect describe-connections --connection-id <id> --output json | \
     jq '.connections[] | {macSecCapable, encryptionMode}'
   ```

### For CONFIG_GAP

**BGP auth missing on public VIF:**
1. Provision a new public VIF with `--auth-key`:
   ```bash
   aws directconnect create-public-virtual-interface --connection-id <id> \
     --new-public-virtual-interface-allocation file://vif-spec.json
   ```
   `vif-spec.json` must include `authKey`.
2. Once BGP is up on the new VIF, migrate routes (AS-path prepend the old VIF
   to lower local-pref, then withdraw).
3. Delete the old VIF:
   ```bash
   aws directconnect delete-virtual-interface --virtual-interface-id <old-id>
   ```

**LOA stuck on `requested` connection:**
1. Re-request the LOA-CFA:
   ```bash
   aws directconnect describe-connection-loa --connection-id <id> \
     --output json > loa.json
   ```
2. If the call returns an error or empty, open an AWS Support case
   (Business / Enterprise) — LOA issuance is an AWS-side operation.
3. For `pending` connections >10 business days, contact the APN partner
   directly — the cross-connect is the partner's action.

**VIF redundancy gap:**
1. Provision a DXGW if not present:
   ```bash
   aws directconnect create-direct-connect-gateway \
     --direct-connect-gateway-name dxgw-prod --amazon-side-asn 64512
   ```
2. Provision a second VIF on the diverse connection:
   ```bash
   aws directconnect create-private-virtual-interface --connection-id <diverse-id> \
     --new-private-virtual-interface-allocation file://vif2-spec.json
   ```
3. Attach both VIFs to the DXGW and the appropriate VGW/TGW.
4. Verify failover via AS-path prepending tests before declaring production-ready.

### For OK

1. No remediation required for current posture.
2. Recommend CloudWatch alarms on `ConnectionState` (down) and
   `ConnectionEncryption` (drop below negotiated S-Tag count) — these catch
   silent MACSec downgrade.
3. Recommend a quarterly diversity review: new DX locations may have opened
   closer to your DC, enabling tighter RTOs.

## Domain

AWS CloudOps / Hybrid Networking Resilience & Compliance.
