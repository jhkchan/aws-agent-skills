---
description: Audit a Direct Connect topology for single-path failure risk, MACSec encryption gaps, BGP auth on public VIFs (route-hijack defence), VIF redundancy via DXGW, and LOA-CFA provisioning state.
nl_triggers:
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
  - "hybrid network resilience"
  - "DX encryption mode"
  - "should_encrypt vs must_encrypt"
  - "BGP MD5 public prefix"
routes_to: directconnect-auditor
---

# /aws:audit-directconnect-topology

Activate the `directconnect-auditor` skill and audit one or more Direct
Connect connections, VIFs, and LAGs for resilience and security posture.

## What it does

Reads `describe-connections` + `describe-virtual-interfaces` JSON output
(optionally `describe-lags`, `describe-connection-loa`, `describe-bgp-peers`)
and applies the ordered classification logic:

1. Pre-flight metadata gate — short-circuit hosted-connection MACSec N/A,
   LAG-member diversity roll-up, and `connectionState` interpretation.
2. Redundancy audit — count diversity units at distinct `locationCode`s;
   same-POP pairs are pseudo-diversity (SINGLE_CONNECTION).
3. MACSec audit — gate on hardware eligibility, flag `should_encrypt` and
   `no_encrypt` on capable dedicated hardware as NO_ENCRYPTION.
4. BGP / LOA / VIF audit — public VIF without MD5 (route-hijack vector),
   private ASN on public VIF, jumbo MTU on public VIF, BGP down on
   available, stale LOA on `requested` connections, single-VIF-on-single-
   connection gaps.
5. Aggregation — worst finding wins
   (SINGLE_CONNECTION > NO_ENCRYPTION > CONFIG_GAP > OK).

Emits a deterministic VERDICT per topology:

```text
CONNECTION: <primary connection-id or LAG-id>
VERDICT: SINGLE_CONNECTION | NO_ENCRYPTION | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its step number>
FINDINGS:
  - [HIGH] <finding description (Step N)>
  - [MEDIUM] <finding description (Step N)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste Direct Connect topology JSON and ask any of:

- "audit this Direct Connect topology"
- "is my hybrid network redundant?"
- "is MACSec enforced on my DX connections?"
- "does my public VIF have BGP auth?"
- "is my LOA stuck in requested?"
- "do my two DX connections count as diverse?"

A bare connection-id or LAG-id + any audit verb ("audit this DX",
"check redundancy") also routes here via the orchestrator.

## Inputs

- `describe-connections` JSON (one or more connections).
- `describe-virtual-interfaces` JSON (filtered or unfiltered).
- For full audit: `describe-lags`, `describe-bgp-peers`,
  `describe-direct-connect-gateways`, and `describe-connection-loa` output.
- For offline audit: any topology JSON containing `connectionId`,
  `connectionState`, `bandwidth`, `location`, `lagId`, `macSecCapable`,
  `encryptionMode`, and a VIF list with `virtualInterfaceType` and BGP
  peer state.

## Outputs

- One VERDICT block per topology (multiple findings aggregate to the
  worst verdict per the ordering SINGLE_CONNECTION > NO_ENCRYPTION >
  CONFIG_GAP > OK).
- Enumerated FINDINGS list with per-finding severity and step citation.
- Specific remediation: provision diverse-location connection, switch to
  `must_encrypt`, re-create public VIF with `--auth-key`, open AWS Support
  case for stale LOA, attach VIFs to DXGW for multi-region failover.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for Direct Connect / hybrid networking).
- `/aws:audit-eks-cluster` for EKS control-plane exposure that may ride on
  Direct Connect for hybrid clusters.
- `/aws:audit-transit-gateway` (when available) for TGW route-table audit
  on the AWS side of the DXGW attachment.
