---
name: networkmanager-core-network-auditor
description: >-
  Audits AWS Network Manager (Cloud WAN) core networks for detached
  attachments, permissive resource and segment policies, CIDR overlap
  across VPC attachments, and configuration gaps (LATEST vs LIVE policy
  mismatch, missing edge locations, orphaned segments). Emits a
  deterministic verdict (DETACHED_ATTACHMENT | PERMISSIVE_POLICY |
  CIDR_OVERLAP | CONFIG_GAP | OK) per core network with enumerated
  findings and specific CLI remediation. Use when reviewing Cloud WAN
  core network policies, checking attachment health, validating CIDR
  isolation between segments, auditing cross-account resource policies,
  or hardening core network posture before production deployment.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline policy-document classification.
  Live-account audits use aws networkmanager get-core-network,
  get-core-network-policy, list-attachments, and get-resource-policy
  (AWS CLI v2, SSO or key-based credentials).
keywords:
  - Network Manager
  - Cloud WAN
  - core network
  - attachment
  - DETACHED
  - resource policy
  - cross-account
  - CIDR overlap
  - segment policy
  - segment isolation
  - LATEST vs LIVE
  - policy generation
  - edge location
  - network function group
  - VPC attachment
  - transit gateway
  - routing
  - require-acceptance
  - core network audit
tags: [networkmanager, cloud-wan, networking, core-network, segment, cidr, attachment, audit]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Networking
  verdict_shape: "DETACHED_ATTACHMENT | PERMISSIVE_POLICY | CIDR_OVERLAP | CONFIG_GAP | OK"
  when_to_use: >-
    Reviewing a Cloud WAN core network policy before production deployment,
    checking for detached or rejected attachments, validating CIDR isolation
    between segments, auditing cross-account resource policies, inspecting
    segment routing for isolation gaps, or verifying that the LIVE policy
    matches the LATEST committed policy.
  activation_triggers:
    - "audit this core network"
    - "check Cloud WAN attachment status"
    - "CIDR overlap in core network"
    - "segment isolation check"
    - "core network resource policy"
    - "LATEST vs LIVE policy"
    - "detached VPC attachment"
    - "core network audit"
  invocation_schema: >-
    Input: either (a) a core network policy document plus attachment list
    and resource policy JSON, OR (b) a core-network-id for live-account
    audit. Output: deterministic CORE_NETWORK/VERDICT/REASON/FINDINGS/
    REMEDIATION block per core network, where VERDICT is one of
    DETACHED_ATTACHMENT, PERMISSIVE_POLICY, CIDR_OVERLAP, CONFIG_GAP, OK.
---

# Network Manager Core Network Auditor

## Mindset

**One-line takeaway:** the verdict is always the **worst** finding across
all dimensions, and a detached attachment is a **live outage** — not a
configuration risk but active traffic disruption happening right now.

Cloud WAN core networks are the global backbone layer above Transit
Gateway. Three behaviors make them dangerous when misconfigured:

- **AttachmentStatus vs State** — `State: AVAILABLE` means the resource
  exists; `AttachmentStatus: DETACHED` means traffic does not flow. Most
  operators only check State.
- **CIDR overlap is not validated** — Cloud WAN silently accepts
  overlapping CIDRs across attachments. The overlap manifests as
  ambiguous routing with no error, no warning.
- **LATEST policy is not LIVE policy** — a committed-but-not-deployed
  policy change means the running network may not match what you audited.

## Quick reference — verdict thresholds

| Condition | Verdict | Step |
|---|---|---|
| Any attachment `AttachmentStatus: DETACHED` or `REJECTED` | **DETACHED_ATTACHMENT** | Step 1 |
| CIDR ranges of two+ attachments overlap | **CIDR_OVERLAP** | Step 2 |
| `Principal: "*"` + `networkmanager:*` on resource policy, no condition | **PERMISSIVE_POLICY** | Step 3 |
| Cross-account principal on resource policy, no condition | **PERMISSIVE_POLICY** | Step 3 |
| Segment `share-with` includes segments it should isolate from | **PERMISSIVE_POLICY** | Step 4 |
| `require-acceptance: false` on cross-account-eligible segment | **PERMISSIVE_POLICY** | Step 4 |
| NFG `send-via`/`receive-from` includes both sides of an isolated segment pair | **PERMISSIVE_POLICY** | Step 4 |
| `LATEST` policy generation != `LIVE` generation | **CONFIG_GAP** | Step 5 |
| Attachment assigned to nonexistent segment | **CONFIG_GAP** | Step 5 |
| Attachment count >= 95 of 100-quota on core network | **CONFIG_GAP** | Step 5 |
| All ATTACHED, no overlap, same-account policy, isolated segments, LIVE=LATEST | **OK** | Step 6 |

## Pre-flight: core network metadata gate

Before evaluating the core network config, classify the core network itself.

| Attribute | Value | Effect on audit |
|---|---|---|
| `State` | `CREATING` / `UPDATING` | Core network is mid-change — policy may be in flux. Note but do not block audit. |
| `State` | `AVAILABLE` | Proceed with full audit. |
| `State` | `DELETING` | Core network being torn down. Flag as operational finding. |
| `OwnerAccountId` | Caller account | Proceed. |
| `OwnerAccountId` | Different account | Shared core network — resource policy is the cross-account gate. Do NOT skip it. |

**If the core network policy JSON is malformed** (invalid JSON, missing
`core-network-configuration`, missing `segments`), output:

```text
CORE_NETWORK: <core-network-id>
VERDICT: ERROR
REASON: Core network policy document is not valid JSON or is missing required fields — cannot classify.
REMEDIATION: Retrieve the canonical policy with `aws networkmanager get-core-network-policy --core-network-id <id> --policy-version LIVE --output json` and re-audit.
```

**Partially malformed config:** If the policy JSON parses but individual
attachments are missing required fields (`AttachmentStatus`, `Cidrs`,
`Segment`), classify each valid attachment normally and emit an ERROR
note per malformed one: "Attachment N is malformed (missing
AttachmentStatus) — skipped." Do NOT abort the entire audit when one
attachment is broken — the valid attachments may still produce a
DETACHED_ATTACHMENT finding.

**Multi-network sweep note (pagination):** `aws networkmanager
list-core-networks` returns at most 50 per page. Use `--starting-token`
to page through all networks. For each, also page `list-attachments`
(caps at 100/page). Always drain `NextToken` to completion — the last
page is where stale and detached attachments hide.

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious Network Manager behaviors

These behaviors are easy to misjudge without operational Cloud WAN
experience. Each changes a verdict if ignored:

- **State vs AttachmentStatus is the most dangerous confusion.** `State`
  tracks the resource lifecycle (`CREATING`, `AVAILABLE`, `UPDATING`,
  `DELETING`). `AttachmentStatus` tracks whether traffic flows
  (`ATTACHED`, `DETACHED`, `REJECTED`,
  `PENDING_ATTACHMENT_ACCEPTANCE`). An attachment can be
  `State: AVAILABLE` + `AttachmentStatus: DETACHED` — the resource
  exists but carries no traffic. Always check `AttachmentStatus`, not
  `State`.

- **CIDR overlap is not validated at attachment creation.** When you
  create a VPC attachment with CIDRs that overlap an existing attachment,
  Cloud WAN accepts it silently. The overlap creates ambiguous routes —
  traffic to an IP in the overlap range may go to either VPC depending
  on route-table evaluation order. There is no CloudTrail error, no
  CloudWatch alarm, no console warning.

- **LATEST is not LIVE.** `get-core-network-policy --policy-version
  LATEST` returns the most recent committed policy.
  `--policy-version LIVE` returns the currently deployed one. When they
  differ, changes are staged but NOT in effect —
  `ExecuteCoreNetworkChangeSet` deploys them (5-15 min for multi-edge
  networks). Auditing LATEST when LIVE is different produces a false
  sense of what the network is actually doing.

- **The "default" segment is globally connected.** Any attachment
  assigned to the built-in `default` segment shares routes with ALL
  other segments, including ones you intended to isolate. This is by
  design — the default segment is a catch-all for connectivity. Using it
  for production workloads silently breaks segmentation.

- **Attachment policy rules shadow in numeric order.** The
  `attachment-policies` section evaluates rules by `rule-number`
  ascending. The first match wins. A broad rule at position 1 (e.g.,
  condition `any`) shadows every subsequent rule — all attachments get
  assigned to that segment. Rules that should have priority must have
  lower rule-numbers.

- **Multi-CIDR VPCs advertise ALL CIDR blocks.** A VPC with primary CIDR
  `10.0.0.0/16` and secondary `10.1.0.0/16` advertises both to the core
  network. The secondary CIDR can overlap with another attachment even
  when the primary does not — always check every CIDR, not just the
  primary.

- **require-acceptance defaults to open.** When a segment's
  `require-acceptance` is `false` or absent, cross-account attachments
  to that segment auto-activate without approval. Any account the
  resource policy allows can inject routes into the core network
  immediately.

- **Resource policy is the cross-account gate.** `PutResourcePolicy` on
  a core network controls which accounts can create and modify
  attachments. `Principal: "*"` + `networkmanager:*` is the network
  equivalent of an open S3 bucket — any AWS account holder can inject
  routes.

- **Policy propagation is per-edge, not atomic.** Core network policy
  changes roll out edge-by-edge. During propagation (5-15 min), routing
  can be inconsistent — some edges enforce the new policy, others the
  old. This is why LATEST-to-LIVE matters and why mid-propagation audits
  may show transient mismatches.

- **Quotas to track:** 50 core networks per Region, 100 attachments per
  core network, 20 segments per core network, 50 edge locations per
  core network. These are soft limits (adjustable via quota increase)
  but a core network near the attachment cap may reject new VPC
  attachments silently. When an account is within 5 of the
  100-attachment cap, new cross-account attachments can fail with no
  explicit quota error — they enter `PENDING_ATTACHMENT_ACCEPTANCE`
  and then silently drop to `DETACHED` on the next edge poll. Treat
  `attachment-count >= 95` on a core network as a CONFIG_GAP finding
  regardless of current status.

- **Network Function Groups (NFGs) bypass segment share-with
  evaluation.** An attachment routed through a
  `network-function-groups` entry exchanges routes with ALL segments
  regardless of its segment's `share-with` list. NFGs exist for
  appliances (firewalls, SD-WAN) that must see all traffic — but an
  NFG whose `send-via` / `receive-from` covers a production segment
  silently voids the isolation you configured in Step 4. The
  segment-policy check does NOT catch NFG-bypassed isolation; you
  must enumerate every NFG's member segments separately and confirm
  none of them touch an isolated segment. An NFG that includes both
  `prod` and `non-prod` in `send-via` is the same verdict as an open
  `share-with`: **PERMISSIVE_POLICY**.

- **`isolate-attachments: true` flips intra-segment connectivity.**
  When a segment sets `isolate-attachments: true`, attachments
  WITHIN that segment CANNOT reach each other — only the segment's
  `share-with` targets are reachable from each attachment. This is
  the opposite of what most operators infer from the name: an
  "isolated" segment behaves like a hub where every spoke is alone.
  A `prod` segment with `isolate-attachments: true` and
  `share-with: ["shared-services"]` gives every prod VPC access to
  shared-services but NOT to other prod VPCs. Misreading this flag
  as "isolated from shared-services" inverts the PERMISSIVE_POLICY
  verdict. When the flag is absent, Cloud WAN treats it as `false`
  — intra-segment connectivity is allowed.

- **Core network change sets are one-way — there is no API
  rollback.** `ExecuteCoreNetworkChangeSet` deploys LATEST and
  supersedes the previous LIVE generation; the prior generation is
  queryable via `--policy-version <N>` but cannot be re-activated
  directly. To undo a bad deployment, you must commit a NEW policy
  generation that restores the prior text and survive another 5-15
  min propagation window. There is no `RollbackCoreNetworkChangeSet`
  API. This is why the LIVE backup captured in the safety section is
  not optional — it is the only recovery reference, because AWS does
  not retain a restorable snapshot of the prior runtime state.

### Step 1: Attachment status evaluation (DETACHED_ATTACHMENT)

For each attachment, check `AttachmentStatus`:

- **DETACHED** → **DETACHED_ATTACHMENT**. The attachment was removed
  from the core network via policy but the resource still exists.
  Traffic is broken RIGHT NOW for all resources in the attached VPC.
  This is an active outage, not a risk — the finding takes precedence
  over every other dimension because production workloads may be down.

- **REJECTED** → **DETACHED_ATTACHMENT**. The attachment was explicitly
  rejected (requires-acceptance was true and the core network owner
  declined). Traffic never connected. If the rejection was
  unintentional, the VPC's workloads are stranded.

- **PENDING_ATTACHMENT_ACCEPTANCE** → note as CONFIG_GAP finding (not
  DETACHED). The attachment is waiting for acceptance — traffic is not
  flowing, but this is expected when `require-acceptance: true`.

An attachment with `AttachmentStatus: ATTACHED` and `State: AVAILABLE`
passes this step. Note: `State: AVAILABLE` alone is insufficient — it
means the resource is healthy, not that it is connected.

### Step 2: CIDR overlap detection (CIDR_OVERLAP)

Collect all CIDR blocks from all attachments. For each pair of CIDRs
from DIFFERENT attachments, apply the overlap algorithm:

**Overlap detection algorithm (concrete):** For two CIDRs A/B and C/D
(where B and D are prefix lengths), convert each to a numeric range:
1. Compute the network address by zeroing host bits: `net = ip & mask`
   where `mask = (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF`.
2. Compute the broadcast address: `bcast = net | ~mask`.
3. CIDRs overlap if `A.net <= C.bcast AND C.net <= A.bcast` (range
   intersection test). This catches full containment (the common case:
   `10.0.0.0/16` contains `10.0.1.0/24`) and partial overlap
   (`10.0.0.0/23` overlaps `10.0.1.0/24`).
4. Identical CIDRs (`10.0.1.0/24` and `10.0.1.0/24`) always overlap —
   flag even within the same segment.

**Example:** `10.0.0.0/16` (range 10.0.0.0 - 10.0.255.255) vs
`10.0.1.0/24` (range 10.0.1.0 - 10.0.1.255). Since 10.0.0.0 <=
10.0.1.255 AND 10.0.1.0 <= 10.0.255.255, they overlap.

- Overlap **across segments** is the most dangerous — it creates
  inter-VPC routing ambiguity that violates segmentation boundaries.
  Traffic destined for `10.0.1.5` may route to either segment.
- Overlap **within the same segment** is still a finding — multiple VPCs
  in the same segment advertising overlapping CIDRs cause intra-segment
  routing ambiguity.
- **Multi-CIDR VPCs:** a VPC with `[10.0.0.0/16, 10.1.0.0/16]`
  advertises BOTH. Check every CIDR from every attachment — the
  secondary CIDR may overlap even when the primary does not.

Report the overlapping pair, their attachment IDs, segments, and the
overlapping CIDR range. If no overlaps exist, this step passes.

### Step 3: Resource policy evaluation (PERMISSIVE_POLICY)

Examine the resource policy attached to the core network. Classify the
principal scope of each `Allow` statement:

- **WILDCARD_PRINCIPAL** — `Principal: "*"` or `{"AWS": "*"}`. Any AWS
  account holder can invoke the listed actions. Combined with
  `networkmanager:*` or `CreateAttachment`, this is a route-injection
  vector. → **PERMISSIVE_POLICY**.

- **CROSS_ACCOUNT** — Principal ARN's 12-digit account ID differs from
  the core network's `OwnerAccountId`. Without a restrictive condition
  (`aws:SourceAccount`, `aws:SourceArn`), the external account can
  modify attachments. → **PERMISSIVE_POLICY**.

- **SAME_ACCOUNT** — All principals share the `OwnerAccountId`. This
  includes the root principal
  (`arn:aws:iam::ACCOUNT:root` + `networkmanager:*`), which is the
  **normal root-of-trust delegation** — do NOT flag it.

A WILDCARD or CROSS_ACCOUNT principal with a STRONG condition
(`aws:SourceAccount`, `aws:SourceArn`) narrows exposure — note the
finding as informational but do NOT produce PERMISSIVE_POLICY unless
the condition is absent or WEAK.

### Step 4: Segment policy evaluation (PERMISSIVE_POLICY)

Examine the `segment-actions` in the core network policy:

- **Open share-with** — a segment whose `share-with` list includes ALL
  other segments has no isolation. Example: segment `prod` with
  `share-with: ["prod", "non-prod", "shared-services"]` shares routes
  with every segment. If `prod` and `non-prod` should be isolated, this
  is a **PERMISSIVE_POLICY** finding.

- **Default segment misuse** — the built-in `default` segment shares
  routes with all segments by definition. Any attachment assigned to
  `default` has global connectivity. Flag as **PERMISSIVE_POLICY** if
  `default` is used for anything other than a deliberate catch-all.

- **require-acceptance false on cross-account-eligible segment** — if
  any segment allows cross-account attachments (the resource policy
  permits it) and `require-acceptance` is false or absent, external
  accounts can auto-inject routes. → **PERMISSIVE_POLICY**.

Isolation check: for each pair of segments that should be isolated
(e.g., `prod` vs `non-prod`), verify NEITHER segment's `share-with`
list includes the other. If either side shares, isolation is broken.

**Network Function Group bypass detection:** After the segment
share-with check, enumerate every entry in `network-function-groups`.
For each NFG, collect its `send-via` and `receive-from` member
segments. If an NFG's member set includes both sides of a segment
pair that should be isolated (e.g., `prod` + `non-prod`), the NFG
bridges the isolation boundary — emit **PERMISSIVE_POLICY** with
the finding: "NFG `<name>` send-via includes `<seg-a>` and
`<seg-b>`, bypassing segment isolation." This check is required
because NFG route exchange ignores `share-with` lists entirely —
an NFG with an overly broad member set silently voids every
isolation rule that passed above.

### Step 5: Configuration gap evaluation (CONFIG_GAP)

Check for operational misconfigurations that do not cause immediate
traffic disruption but create risk:

- **LATEST != LIVE policy generation** — the committed policy (`LATEST`)
  differs from the deployed policy (`LIVE`). Changes are staged but not
  in effect. The running network may not match the audited policy. →
  **CONFIG_GAP**. Remediation: `ExecuteCoreNetworkChangeSet`.

- **Attachment assigned to nonexistent segment** — an attachment's
  `Segment` field references a segment name not defined in the policy's
  `segments` block. The attachment may route unpredictably or be
  assigned to the default segment implicitly. → **CONFIG_GAP**.

- **Missing edge location on attachment** — an attachment without an
  assigned `EdgeLocation` uses auto-selection. AWS may reassign the edge
  when new locations come online, causing latency shifts. → **CONFIG_GAP**
  (informational, not blocking).

- **Attachment count near quota** — if the core network has 95+ of its
  100-attachment quota in use, new cross-account attachments can fail
  silently: they enter `PENDING_ATTACHMENT_ACCEPTANCE` then drop to
  `DETACHED` on the next edge poll with no explicit quota error. Emit
  a **CONFIG_GAP** finding citing the current count and remaining headroom.

### Step 6: Aggregation — worst verdict wins

The final verdict is the **maximum severity** across all findings, where:

```text
DETACHED_ATTACHMENT > CIDR_OVERLAP > PERMISSIVE_POLICY > CONFIG_GAP > OK
```

If no findings from any step, the verdict is **OK**.

## Output format (per core network)

```text
CORE_NETWORK: <core-network-id>
VERDICT: DETACHED_ATTACHMENT | PERMISSIVE_POLICY | CIDR_OVERLAP | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and step>
FINDINGS:
  - [DETACHED_ATTACHMENT] <finding description (Step N)>
  - [CIDR_OVERLAP] <finding description (Step N)>
  - [OK] <dimension that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — detached attachment with CIDR overlap

```text
CORE_NETWORK: core-network-pqr678
VERDICT: DETACHED_ATTACHMENT
REASON: Attachment attachment-hhh888 is in DETACHED status — traffic to
the prod VPC is broken (Step 1). Additionally, CIDRs 10.0.0.0/16 and
10.0.1.0/24 overlap across the prod and non-prod segments (Step 2).
FINDINGS:
  - [DETACHED_ATTACHMENT] VPC attachment-hhh888 (vpc-hhh888) is DETACHED
    — prod-segment workloads are unreachable (Step 1)
  - [CIDR_OVERLAP] attachment-hhh888 CIDR 10.0.0.0/16 overlaps with
    attachment-iii999 CIDR 10.0.1.0/24 across prod/non-prod segments
    (Step 2)
  - [OK] Resource policy is same-account scoped (Step 3)
REMEDIATION:
  1. DETACHED_ATTACHMENT — Re-attach attachment-hhh888 via policy:
     update the core network policy to include the attachment in the
     prod segment, then execute the change set:
     aws networkmanager execute-core-network-change-set
       --core-network-id core-network-pqr678
  2. CIDR_OVERLAP — Re-IP one VPC's overlapping CIDR or restrict
     advertisement to non-overlapping subnets. Cloud WAN does not
     validate overlaps — you must enforce disjoint CIDR ranges
     across attachments manually.
```

## Anti-Patterns — NEVER

- NEVER treat `AttachmentState: AVAILABLE` as proof the attachment is
  connected. `State` tracks lifecycle; `AttachmentStatus` tracks
  connectivity. An attachment can be `AVAILABLE` and `DETACHED`
  simultaneously. Always check `AttachmentStatus: ATTACHED`.

- NEVER skip CIDR overlap detection. Cloud WAN silently accepts
  overlapping CIDRs at attachment creation — there is no API error, no
  console warning, no CloudTrail event. The overlap manifests as
  ambiguous routing, with traffic silently reaching the wrong VPC.

- NEVER assume the "default" segment is isolated. The default segment
  shares routes with ALL segments by design. Assigning a production VPC
  to `default` gives it full network connectivity and breaks every
  isolation boundary.

- NEVER treat the LATEST policy generation as the deployed state. Only
  LIVE is in effect. Auditing LATEST when LIVE differs produces a false
  picture — the running network may not match the policy text under
  review.

- NEVER flag a same-account root principal
  (`arn:aws:iam::ACCOUNT:root` + `networkmanager:*`) as permissive.
  This is the standard root-of-trust delegation that enables IAM-based
  core network management. Flagging it as a wildcard grant is a false
  positive.

- NEVER assume segment names imply isolation. A segment named
  "isolated" with `share-with: ["prod", "non-prod", "isolated"]` is
  NOT isolated. Route sharing is determined by the `share-with` list,
  not the segment name.

- NEVER ignore attachment policy rule ordering. Rules are evaluated in
  ascending `rule-number` order. A broad `condition: any` rule at
  position 1 shadows every subsequent rule — all attachments get
  assigned to that segment regardless of intent.

- NEVER recommend deleting a core network attachment without verifying
  workload dependencies. Attachment deletion stops traffic immediately
  for all resources in the attached VPC. Always check which subnets,
  EC2 instances, and services depend on the attachment before removing
  it.

- NEVER assume a multi-CIDR VPC advertises only the primary CIDR. A VPC
  with primary `10.0.0.0/16` and secondary `10.1.0.0/16` advertises
  BOTH. The secondary CIDR may overlap with another attachment even
  when the primary does not.

- NEVER treat `require-acceptance: false` on cross-account segments as
  acceptable by default. Without acceptance, any cross-account VPC that
  the resource policy allows can auto-attach and inject routes into the
  core network immediately — no review, no approval gate.

- NEVER assume policy changes are atomic. Core network policy changes
  propagate edge-by-edge (5-15 min). During propagation, routing can be
  inconsistent across edges. Do not audit a mid-propagation policy and
  treat the result as steady state.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (PutResourcePolicy, ExecuteCoreNetworkChangeSet, UpdateAttachment,
  DeleteAttachment), the auditor MUST emit:
  `CONFIRM: About to <action> on core network <id> in account <account>.
  This affects <consequence>. Proceed? (yes/no)`

- **Policy backup.** Capture the current LIVE policy before any
  modification:
  `aws networkmanager get-core-network-policy --core-network-id <id> --policy-version LIVE --output json > /tmp/<id>-policy-backup-$(date +%s).json`.
  Core network policies support rollback to prior generations, but the
  backup is the safety net if the rollback itself fails.

- **Verify attachment dependencies before deletion.** Before recommending
  attachment removal, check `aws ec2 describe-subnets --filters
  Name=vpc-id,Values=<vpc-id>` and confirm no production workloads
  depend on the VPC's core network connectivity.

- Prefer additive changes (restrict a policy, add a condition) over
  destructive changes (delete an attachment, remove a segment). Additive
  changes are reversible; attachment deletion is an immediate outage.

## Remediation guidance

### For DETACHED_ATTACHMENT

1. Re-attach the VPC by updating the core network policy to include the
   attachment in its segment, then execute the change set:
   `aws networkmanager execute-core-network-change-set --core-network-id <id>`
2. If the detachment was intentional (VPC decommissioned), delete the
   attachment resource to stop accruing cost:
   `aws networkmanager delete-attachment --attachment-id <id>`
3. Verify re-attachment:
   `aws networkmanager get-attachment --attachment-id <id>` — confirm
   `AttachmentStatus: ATTACHED`.

### For CIDR_OVERLAP

1. Identify which CIDR range is causing the overlap and re-IP one VPC to
   a disjoint range.
2. Alternatively, restrict the attachment's advertised CIDRs to
   non-overlapping subnets using the attachment's `SubnetArns` list —
   advertise only subnets whose CIDRs do not overlap.
3. After remediation, verify route tables:
   `aws networkmanager get-network-routes --core-network-id <id>` —
   confirm each destination has a unique next-hop attachment.

### For PERMISSIVE_POLICY — resource policy

1. Remove `Principal: "*"` from the resource policy. Replace with the
   specific account or role ARN that needs cross-account access.
2. Add `aws:SourceAccount` or `aws:SourceArn` conditions to any
   cross-account principal.
3. Back up the current policy first:
   `aws networkmanager get-resource-policy --resource-arn <core-network-arn> --output json > /tmp/resource-policy-backup.json`.
4. Apply the tightened policy:
   `aws networkmanager put-resource-policy --policy-document file://tightened-policy.json --resource-arn <core-network-arn>`.

### For PERMISSIVE_POLICY — segment policy

1. Remove the offending segment from each over-broad `share-with` list.
   If `prod` should not share with `non-prod`, remove `non-prod` from
   `prod`'s share-with and vice versa.
2. Move production attachments out of the `default` segment into a named
   segment with explicit isolation.
3. Set `require-acceptance: true` on any segment that accepts
   cross-account attachments.

### For CONFIG_GAP

1. If `LATEST != LIVE`, deploy the pending change set:
   `aws networkmanager execute-core-network-change-set --core-network-id <id>`.
2. If an attachment references a nonexistent segment, update the policy
   to either create the segment or reassign the attachment to a valid
   one.
3. Assign explicit edge locations to attachments to prevent auto-
   reassignment when AWS adds new PoPs.

### For OK

1. No remediation required for the current posture.
2. Recommend enabling CloudWatch alarms for `AttachmentStatusChanges`
   and `CoreNetworkPolicyChange` events.
3. Verify LATEST equals LIVE after every policy commit.

## Recent AWS features (2024-2026)

- **Core Network policy versioning and rollback (2024):** Core network policies now support versioned changes with rollback capability. Auditors should verify that the LATEST policy version matches the LIVE policy version — a mismatch indicates an unexecuted change.
- **Cloud WAN resource policy enhancements (2024-2025):** Improved cross-account resource policies for core network attachments. Auditors should verify that resource policies include `aws:SourceAccount` conditions for cross-account attachments.
- **Segment actions and route table improvements (2024):** Enhanced segment actions with more granular routing controls. Auditors should verify that `segment-actions` with `share-with` do not inadvertently allow cross-segment traffic that should be isolated.

## Domain

AWS CloudOps / Network Manager (Cloud WAN) Core Network Security and Compliance.
