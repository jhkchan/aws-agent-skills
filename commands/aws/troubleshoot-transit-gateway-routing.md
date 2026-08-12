---
name: troubleshoot-transit-gateway-routing
description: >-
  Slash command for the transit-gateway-routing-troubleshooter skill.
  Diagnoses Transit Gateway routing failures: route table association
  vs propagation, static route priority (static beats propagated),
  overlapping CIDR across attachments, peering non-transitivity,
  VPN/Direct Connect gateway routing, multicast domain membership,
  TGW flow logs gaps, VPC default route 0.0/0 pointing at TGW, TGW
  attachment in wrong subnet/AZ, cross-VPC security group references
  (not supported through TGW), DNS resolution across TGW, appliance
  mode forcing traffic through an inspection VPC, and blackhole route
  detection. Emits ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA with the
  failing layer and the verifying probe.
skill: transit-gateway-routing-troubleshooter
family: Networking
task_type: troubleshoot
verdict_shape: "ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA"
---

# /aws:troubleshoot-transit-gateway-routing

Invoke the `transit-gateway-routing-troubleshooter` skill to diagnose
a Transit Gateway routing failure.

## When to use

- A VPC attached to a TGW cannot reach another VPC attached to the
  same TGW (traffic leaves source but never arrives at destination).
- Traffic through the TGW reaches the WRONG target VPC (static route
  override or overlapping CIDR).
- TGW peering between two TGWs (same region or cross-region) does not
  forward traffic in one or both directions.
- A stateful inspection VPC drops cross-AZ flows intermittently
  (appliance mode disabled).
- VPN or Direct Connect advertises routes into the TGW but VPC
  instances cannot reach on-prem.
- Multicast sender succeeds but receivers see nothing (multicast
  domain membership gap).
- Cross-VPC DNS hostname resolution fails across TGW-attached VPCs.
- A VPC route table default route `0.0.0.0/0` is pointing at the TGW
  instead of the IGW, blackholing internet-bound traffic.
- A cross-VPC security group reference (peer VPC's SG as a source
  rule) is not allowing traffic through the TGW.

## Invocation

```
/aws:troubleshoot-transit-gateway-routing <description of the TGW routing scenario>
```

The skill will:

1. Identify the symptom category (one-way blackhole, wrong target,
   peering non-transitive, appliance mode, VPN/DX, multicast, DNS,
   flow logs, cross-VPC SG).
2. Request the mandatory context: TGW ID, source VPC + CIDR,
   destination VPC + CIDR, attachment IDs, and whether peering, VPN,
   or Direct Connect is involved.
3. Walk the diagnostic tree in symptom order: association →
   propagation → return path → static-route priority → overlapping
   CIDR → peering transitivity → appliance mode → VPN/DX → multicast
   → DNS → flow logs → cross-VPC SG.
4. Apply the static-vs-propagated priority rule before any
   "re-add the attachment" advice — this is the most common
   misdiagnosis.
5. Verify the return path (destination VPC's route table) before
   declaring a forward-path root cause.
6. Emit the standard VERDICT block with the failing probe and
   remediation command.

## Output shape

```text
TARGET: <tgw-id, source-attachment, destination-attachment>
VERDICT: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
REASON: <1-2 sentences naming the failed layer and the failing probe>
LAYER: <TGW_ROUTE_TABLE_ASSOCIATION | TGW_ROUTE_TABLE_PROPAGATION |
        TGW_STATIC_ROUTE_PRIORITY | TGW_OVERLAPPING_CIDR |
        TGW_PEERING_NON_TRANSITIVE | TGW_VPN_DX_ROUTING |
        TGW_MULTICAST_DOMAIN | TGW_FLOW_LOGS |
        VPC_DEFAULT_ROUTE_TGW | TGW_ATTACHMENT_WRONG_SUBNET |
        TGW_SG_CROSS_VPC | TGW_DNS_RESOLUTION |
        TGW_APPLIANCE_MODE | TGW_BLACKHOLE_ROUTE | UNKNOWN>
EVIDENCE:
  - <layer>: <failing probe and its output>
REMEDIATION: <specific CLI command + verification command>
```

## Pre-flight

The skill requires the TGW ID, the source and destination VPC IDs
(or attachment IDs), and the observed packet-flow symptom to apply
the symptom-to-layer triage. If these are not available, the skill
emits `INSUFFICIENT_DATA` with the list of required inputs.

## References

- Skill: `skills/transit-gateway-routing-troubleshooter/SKILL.md`
- Reference: `skills/transit-gateway-routing-troubleshooter/references/tgw-routing-reference.md`
- Reference: `skills/transit-gateway-routing-troubleshooter/references/tgw-attachment-and-appliance-mode.md`
- AWS docs: https://docs.aws.amazon.com/vpc/latest/tgw/
