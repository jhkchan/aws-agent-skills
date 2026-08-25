# Advanced patterns — networkmanager-core-network-auditor

Expert Cloud WAN behaviors and recent AWS features, moved verbatim from SKILL.md (load on demand).

## Step 0: Expert knowledge — non-obvious Network Manager behaviors

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

## Recent AWS features (2024-2026)

- **Core Network policy versioning and rollback (2024):** Core network policies now support versioned changes with rollback capability. Auditors should verify that the LATEST policy version matches the LIVE policy version — a mismatch indicates an unexecuted change.
- **Cloud WAN resource policy enhancements (2024-2025):** Improved cross-account resource policies for core network attachments. Auditors should verify that resource policies include `aws:SourceAccount` conditions for cross-account attachments.
- **Segment actions and route table improvements (2024):** Enhanced segment actions with more granular routing controls. Auditors should verify that `segment-actions` with `share-with` do not inadvertently allow cross-segment traffic that should be isolated.
