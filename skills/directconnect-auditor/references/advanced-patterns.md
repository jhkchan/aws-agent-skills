# Advanced Patterns (load on demand) — Direct Connect Auditor

Step 0 expert-knowledge deep dive, per-verdict remediation playbooks, metadata-gate and edge-case field tables, and Recent AWS features moved verbatim from SKILL.md.
The classification steps, severity matrix, output contract, primary worked example, and NEVER list remain in SKILL.md.

---

## Step 0: Expert knowledge — non-obvious DX behaviours that change classification (moved from SKILL.md)

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
  `--max-results` with pagination where available. **Cross-account
  `bgpPeers[].authKey` is silently redacted** in the interface-owner view
  (returned as null without an error flag) — only the connection owner
  sees the authoritative key state. Treat a hosted-VIF null authKey as
  "unverifiable, assume partner role", never as "auth absent".

- **DX billing is port-based, not usage-based — a `down` connection still
  bills at full port rate.** This is the #1 DX cost trap: an organisation
  that provisions a 10 Gbps primary, fails over to a backup, and leaves
  the primary `down` for weeks continues to pay for both. Deleting a hosted
  VIF does not stop the underlying port billing either — only
  `delete-connection` stops port charges (after the partner cross-connect
  is physically removed, which can lag by weeks). Flag a `down` but billed
  connection as CONFIG_GAP (LOW) with the cost implication; the
  remediation is `delete-connection` once the failover is verified stable,
  not "wait for it to recover".

- **MACSec CAK/CKN rotation is a two-step overlap, not a swap.**
  `update-connection --encryption-mode must_encrypt` accepts two AWS-side
  key slots. Rotating keys by removing the old key first and adding the new
  key second drops MACSec negotiation for 30-60 seconds (one MKA hello
  interval cycle) — which on a `must_encrypt` link drops ALL traffic. The
  correct rotation is: (1) add the new CAK/CKN pair via
  `update-connection`, (2) configure the CE with both pairs, (3) verify
  MACSec still negotiated with `describe-connections | jq
  .connections[].macSecKeys`, (4) then remove the old pair. Skipping the
  overlap is a silent outage.

- **`locationCode` maps to an AWS-side patch panel, not to a physical
  building.** Some colocation campuses host multiple DX `locationCode`s in
  the same building or in adjacent buildings sharing one meet-me-room,
  common riser, or fibre entry pit. Two connections at distinct
  `locationCode`s can collapse to one physical failure domain if both
  cross-connects traverse the same meet-me-room or building entry. The
  auditor cannot verify this from the API alone — flag any topology where
  both `locationCode`s share a campus prefix (e.g., `EqSE2` + `EqSE3` at
  the same Equinix campus) as CONFIG_GAP (LOW) with a note to confirm
  diverse meet-me-room and diverse building entry with the colo provider.
  Do NOT raise SINGLE_CONNECTION on the campus-prefix heuristic alone —
  the AWS-side patch panels are genuinely diverse even when buildings
  share a meet-me-room.

- **`Describe*` Direct Connect API calls are NOT logged to CloudTrail by
  default.** CloudTrail for Direct Connect captures write events
  (`Create*`, `Delete*`, `Update*`, `Associate*`) but `describe-*` is a
  read event and only appears if CloudTrail data-event logging is
  explicitly enabled for the Direct Connect service — which is off by
  default. Relying on CloudTrail for "who audited DX" or "what topology
  was observed" misses every read. For compliance evidence, capture
  `describe-connections` / `describe-bgp-peers` JSON output to an S3
  bucket with a bucket policy — the API response is the audit record, not
  CloudTrail.

---

## Remediation guidance — per-verdict playbooks (moved from SKILL.md)

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

---

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **MACsec GA on more locations and device types (2024):** MACsec link encryption is now available on additional DX locations and MAC-capable devices. Auditors should re-check whether connections that previously could not enable MACsec now support it — the location list has expanded significantly.
- **CloudWatch monitoring for Direct Connect (2024):** Enhanced CloudWatch metrics for DX connections including per-VIF metrics and connection health insights. Auditors should verify that CloudWatch alarms are configured on connection state changes and BGP flap events.
- **Direct Connect Gateway enhancements (2024-2025):** Improved DX Gateway with support for more VIFs and transit VIF integration. No new audit-surface fields, but auditors should verify that transit gateway associations use the correct allowed prefixes.

---

## Reference — Metadata gate (moved from SKILL.md)

Per-attribute short-circuit table. Apply before Step 1 — misclassifying any of
these produces false positives that erode trust.

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

---

## Reference — Edge-case field handling (moved from SKILL.md)

Resolves ambiguity in Step 3 when fields are absent, redacted, or
cross-account-truncated.

| Field scenario | Interpretation | Action |
|---|---|---|
| `authKeyState: configured` (or input shows auth key was supplied at VIF creation) | BGP MD5 is set | OK for this check; do not flag. |
| `authKeyState: never-configured` (or field absent AND no auth key in creation input) on a **public VIF** | BGP MD5 was never set | CONFIG_GAP (MEDIUM) — route-hijack vector. Remediate via VIF re-creation with `--auth-key`. |
| `authKeyState: never-configured` on a **private/transit VIF** | No MD5 on a scoped VIF | CONFIG_GAP (LOW) — lower risk than public but still recommended. |
| `bgpPeers` array missing entirely from a VIF JSON | No BGP session defined — VIF is non-functional or data is incomplete | CONFIG_GAP (MEDIUM). Emit: `VIF <id> has no bgpPeers array — BGP state unverifiable. Re-fetch with describe-bgp-peers.` Do NOT assume auth is absent; the field may be missing due to truncated API output. |
| `bgpPeers` array present but empty `[]` | VIF exists but no BGP sessions configured | CONFIG_GAP (MEDIUM). A VIF without peers carries no traffic. Flag for operator review. |
| `authKeyState` field absent from input JSON (offline mode) | Cannot determine auth state from describe-virtual-interfaces alone | Infer from `bgpPeers[].authKey` presence in the input; if that is also absent, emit CONFIG_GAP (LOW) with note: `Auth state unverifiable from provided JSON — run describe-bgp-peers for authoritative check.` |
