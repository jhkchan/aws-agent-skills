# End-to-end usage scenario: directconnect-auditor

A walkthrough showing the skill auditing a Direct Connect topology that has
two connections at the same location (SINGLE_CONNECTION — pseudo-diversity)
plus a public VIF missing BGP MD5 auth (CONFIG_GAP — route-hijack vector),
demonstrating worst-finding aggregation, the location-diversity rule, and
the destructive VIF re-creation workflow.

## Input (user prompt)

> We just brought up our second Direct Connect connection for redundancy.
> Both terminate at Equinix SE2 (location code EqSE2). Production hybrid
> apps depend on this link — give me the verdict before we declare
> cutover complete.

```json
[
  {
    "connectionId": "dxcon-prod-primary",
    "connectionName": "prod-primary",
    "connectionState": "available",
    "bandwidth": "10Gbps",
    "location": "EqSE2",
    "lagId": null,
    "connectionMode": "standard",
    "macSecCapable": true,
    "encryptionMode": "must_encrypt"
  },
  {
    "connectionId": "dxcon-prod-backup",
    "connectionName": "prod-backup",
    "connectionState": "available",
    "bandwidth": "10Gbps",
    "location": "EqSE2",
    "lagId": null,
    "connectionMode": "standard",
    "macSecCapable": true,
    "encryptionMode": "must_encrypt"
  }
]
```

```json
[
  {
    "virtualInterfaceId": "dxvif-public-app",
    "virtualInterfaceType": "public",
    "connectionId": "dxcon-prod-primary",
    "vlan": 200,
    "customerAddress": "203.0.113.10/30",
    "amazonAddress": "203.0.113.9/30",
    "advertisedPrefixes": ["203.0.113.0/24"],
    "bgpPeers": [{"asn": 65000, "bgpStatus": "up", "authKey": null}]
  }
]
```

BGP peer authoritative state (describe-bgp-peers):

```json
[
  {
    "virtualInterfaceId": "dxvif-public-app",
    "bgpPeerId": "bgp-public-1",
    "asn": 65000,
    "bgpStatus": "up",
    "authKeyState": "never-configured-at-creation"
  }
]
```

## Skill output

```text
CONNECTION: dxcon-prod-primary
VERDICT: SINGLE_CONNECTION
REASON: Both connections terminate at location EqSE2 — pseudo-diversity, no
facility resilience. A single facility event (power, cooling, fibre-cut on
the meet-me-room) takes both down (Step 1). The public VIF is also missing
BGP MD5 auth (Step 3a), which would be CONFIG_GAP if redundancy were
addressed first.
FINDINGS:
  - [HIGH] Both available diversity units share location EqSE2 — count is 2
    but distinct-location count is 1; facility-level event takes both down
    (Step 1)
  - [MEDIUM] Public VIF dxvif-public-app has never had BGP MD5 configured
    (authKeyState: never-configured-at-creation); advertised prefix
    203.0.113.0/24 is a route-hijack vector (Step 3a)
  - [OK] MACSec must_encrypt enforced on both connections (Step 2)
REMEDIATION:
  1. CRITICAL PRIORITY — Provision a third connection at a DIFFERENT DX
     location (e.g., EqDC2, EqDA1). Migrate the backup VIF onto it. AWS
     Resilient Hybrid Architecture reference pattern: primary LAG +
     diverse standalone backup at a non-adjacent facility. Lead time:
     2-6 weeks (partner cross-connect + LOA issuance).
     aws directconnect create-connection --location EqDC2 \
       --bandwidth 10Gbps --connection-name dxcon-prod-dr
  2. Provision a replacement public VIF with --auth-key:
     aws directconnect create-public-virtual-interface \
       --connection-id dxcon-prod-primary \
       --new-public-virtual-interface-allocation file://vif-spec.json
     (vif-spec.json must include authKey)
  3. Once BGP is up on the new VIF, migrate routes via AS-path prepending,
     then delete the old VIF:
     aws directconnect delete-virtual-interface \
       --virtual-interface-id dxvif-public-app
  4. If a new connection is not feasible this quarter, add an IPsec VPN
     overlay (transit-gateway IPsec or site-to-site) as a backup path.
```

## What the skill caught that a generic assistant misses

1. **"Two connections" is not the same as "diverse".** A generic
   assistant sees two connections and declares redundancy achieved. The
   skill reads the `location` field on each — both are `EqSE2`, meaning
   both cross-connect into the same Equinix facility. The redundancy unit
   for facility-level events is the **location**, not the connection
   count.

2. **BGP MD5 on the public VIF is a route-hijack defence, not a
   minor config issue.** A generic assistant sees `bgpStatus: up` and
   moves on. The skill checks the authoritative `authKeyState` from
   `describe-bgp-peers` (not the write-only `bgpAuthKey: null` from
   describe-virtual-interfaces) and flags the public VIF as a
   route-hijack vector — any on-path attacker can inject more-specific
   routes for 203.0.113.0/24.

3. **Severity ordering is enforced.** The redundancy finding (HIGH)
   outranks the BGP finding (MEDIUM), so the verdict is SINGLE_CONNECTION,
   not CONFIG_GAP. This matches the operator's triage order: fix the
   bigger failure domain first, then the secondary issue.

4. **The remediation includes lead time and the destructive VIF
   re-creation workflow.** Generic advice says "enable BGP auth." The
   skill explains that BGP auth cannot be added in-place — the VIF must
   be re-created, with a cutover step (AS-path prepend the old VIF to
   lower local-pref, then withdraw).

## Slash-command invocation

```
/aws:audit-directconnect-topology
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit our Direct Connect topology before we declare cutover"
```

The orchestrator emits
`[Phase: Audit | Skills routed: directconnect-auditor]` and hands off
to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "audit this Direct Connect topology for redundancy"
# [Phase: Audit | Skills routed: directconnect-auditor]
```

## Live-account follow-up (optional, requires AWS CLI)

After remediating the topology, validate the posture:

```bash
# Verify diverse locations across available connections
aws directconnect describe-connections --profile default --output json | \
  jq '.connections[] | select(.connectionState == "available") |
      {id: .connectionId, location: .location, lagId: .lagId}'

# Confirm MACSec enforcement on each capable connection
aws directconnect describe-connections --profile default --output json | \
  jq '.connections[] | select(.macSecCapable == true) |
      {id: .connectionId, encryptionMode: .encryptionMode}'

# Verify BGP auth state per VIF (authoritative — describe-virtual-interfaces
# bgpAuthKey is write-only and always null)
aws directconnect describe-bgp-peers --virtual-interface-id dxvif-public-app \
  --profile default --output json
```

Then monitor CloudWatch `ConnectionState` (down) and
`ConnectionEncryption` (drop below negotiated S-Tag count) for early
warning of silent MACSec downgrade.
