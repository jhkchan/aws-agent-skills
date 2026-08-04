---
description: Audit a Network Manager (Cloud WAN) core network for detached attachments, permissive resource and segment policies, CIDR overlap across VPC attachments, and configuration gaps (LATEST vs LIVE policy mismatch, missing edge locations).
nl_triggers:
  - "audit this core network"
  - "check Cloud WAN attachment status"
  - "CIDR overlap in core network"
  - "segment isolation check"
  - "core network resource policy"
  - "LATEST vs LIVE policy"
  - "detached VPC attachment"
  - "core network audit"
  - "Cloud WAN audit"
  - "networkmanager audit"
  - "permissive core network policy"
  - "cross-account core network"
  - "core network segment policy"
  - "attachment status check"
  - "network function group"
routes_to: networkmanager-core-network-auditor
---

# /aws:audit-networkmanager-core-network

Activate the `networkmanager-core-network-auditor` skill and audit one or
more Cloud WAN core network configurations for security and operational
exposure.

## What it does

Reads a core network policy document, attachment list, and resource
policy, then applies the ordered classification logic:

1. Attachment status — DETACHED or REJECTED attachments are active
   outages (traffic broken right now).
2. CIDR overlap — overlapping CIDRs across attachments cause silent
   misrouting (Cloud WAN does not validate overlaps at creation).
3. Resource policy — Principal "*" or cross-account without conditions
   allows route injection.
4. Segment policy — open share-with lists or default-segment misuse
   breaks isolation between network segments.
5. Configuration gap — LATEST != LIVE policy generation, nonexistent
   segment references, missing edge locations.
6. Aggregation — worst finding wins (DETACHED_ATTACHMENT > CIDR_OVERLAP
   > PERMISSIVE_POLICY > CONFIG_GAP > OK).

Emits a deterministic VERDICT per core network:

```text
CORE_NETWORK: <core-network-id>
VERDICT: DETACHED_ATTACHMENT | PERMISSIVE_POLICY | CIDR_OVERLAP | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and step>
FINDINGS:
  - [DETACHED_ATTACHMENT] <finding description (Step N)>
  - [CIDR_OVERLAP] <finding description (Step N)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste a core network configuration and ask any of:

- "audit this Cloud WAN core network"
- "check for detached VPC attachments"
- "do these CIDRs overlap?"
- "is my segment policy isolated?"
- "is the resource policy too permissive?"
- "is LATEST the same as LIVE?"

A core network ID or ARN plus any audit verb ("audit this core
network", "check attachment status") also routes here.

## Inputs

- A core network policy document (segment-actions, attachment-policies).
- Attachment list: AttachmentId, AttachmentType, State,
  AttachmentStatus, EdgeLocation, Segment, Cidrs per attachment.
- Resource policy (JSON).
- Policy generation metadata: LATEST and LIVE generation numbers.
- For multi-network sweeps: provide metadata for each core network
  independently.

## Outputs

- One VERDICT block per core network (multiple findings aggregate to
  the worst severity).
- Enumerated FINDINGS list with per-finding verdict and step citation.
- Specific remediation: re-attach via policy, re-IP overlapping CIDRs,
  tighten resource policy, restrict segment share-with, deploy change
  sets.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for Network Manager / Cloud WAN security).
- `/aws:audit-ec2-security-groups` for VPC-level security group auditing
  on instances behind core network attachments.
