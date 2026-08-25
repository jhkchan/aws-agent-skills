---
name: detective-investigation-coverage-auditor
description: Audits Amazon Detective behavior graph coverage, member-account ingestion health, data-source package states (DETECTIVE_CORE, EKS_AUDIT, EKS_RUNTIME), data freshness lag, GuardDuty integration dependency, and Organizations delegated-admin posture. Emits a deterministic verdict (NO_GRAPH | INCOMPLETE_INGESTION | STALE_DATA | CONFIG_GAP | OK) per behavior graph or region with enumerated findings and CLI remediation. Use when validating Detective investigation readiness, checking member-account ingestion gaps, auditing data freshness, verifying GuardDuty integration, or hardening security-investigation coverage before an incident.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline configuration classification. Live-account audits use aws detective list-graphs, list-members, batch-get-graph-member-datasources, batch-get-graph-datasources, describe-organization-configuration, and aws guardduty list-detectors / get-detector (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Security
  verdict_shape: NO_GRAPH | INCOMPLETE_INGESTION | STALE_DATA | CONFIG_GAP | OK
  when_to_use: Validating Amazon Detective investigation readiness, checking member-account ingestion completeness, auditing data freshness lag, verifying GuardDuty integration, reviewing data-source package coverage, or confirming Organizations delegated-admin posture before a security incident.
  activation_triggers: audit Detective behavior graph, is Detective enabled, Detective member accounts not ingesting, Detective data freshness check, GuardDuty Detective integration, Detective source graph coverage, Detective investigation readiness, check Detective Organizations admin, Detective data source packages
  invocation_schema: 'Input: either (a) a Detective behavior-graph configuration snapshot (graph ARN, member list, data-source package states, lastDataReceived timestamps), optionally paired with GuardDuty detector status, OR (b) a region/account identifier for live-account audit. Output: deterministic GRAPH/VERDICT/REASON/FINDINGS/REMEDIATION block per behavior graph, where VERDICT is NO_GRAPH | INCOMPLETE_INGESTION | STALE_DATA | CONFIG_GAP | OK.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Amazon Detective, behavior graph, investigation coverage, GuardDuty integration, member account ingestion, data freshness, DETECTIVE_CORE, EKS_AUDIT, EKS_RUNTIME, Organizations delegated admin, source graph, security investigation, incident response readiness, data source packages, VPC Flow Logs, CloudTrail ingestion
  tags: detective, security, behavior-graph, investigation, guardduty, ingestion, freshness, audit
---

# Detective Investigation Coverage Auditor

## Mindset

**One-line takeaway:** a behavior graph that exists but is not ingesting
data from all accounts — or is ingesting stale data — gives false confidence
during an incident. Detective's value is proportional to its coverage
breadth and data freshness; a partial graph is worse than no graph because
it creates the illusion of completeness.

Amazon Detective builds a **behavior graph** — a linked map of entities
(IPs, instances, roles, IAM principals) derived from GuardDuty findings,
CloudTrail management events, and VPC Flow Logs. Three things must be true
for Detective to be useful during an investigation:

- **The graph must exist** (enabled per-region; Detective is REGIONAL).
- **All member accounts must be actively ingesting** (INVITED is not
  ENABLED — an invitation that is never accepted is a blind spot).
- **Data must be fresh** (Detective has an inherent processing lag; data
  older than 24 hours may indicate a broken ingestion pipeline).

GuardDuty is the **primary security-signal source**. Without a GuardDuty
detector enabled in the same region, Detective has no security findings to
investigate — the graph exists but is a passive telemetry store, not an
investigation tool.

## Quick reference — verdict matrix

| Condition | Verdict | Step |
|---|---|---|
| No behavior graph exists in the target region | **NO_GRAPH** | Step 1 |
| Behavior graph exists but zero member accounts (org has > 1 account) | **INCOMPLETE_INGESTION** | Step 2a |
| Any member account in INVITED or ACCEPTED_BUT_DISABLED state | **INCOMPLETE_INGESTION** | Step 2b |
| Any member DETECTIVE_CORE data-source package not COLLECTING | **INCOMPLETE_INGESTION** | Step 2c |
| All members active but lastDataReceived > 24h for any member | **STALE_DATA** | Step 3 |
| Graph + members healthy but GuardDuty detector disabled in region | **CONFIG_GAP** | Step 4a |
| Graph + members healthy but no Organizations delegated admin | **CONFIG_GAP** | Step 4b |
| All checks pass: graph exists, members COLLECTING, data fresh, GuardDuty on | **OK** | Step 5 |

## Pre-flight: graph discovery gate (run before classification)

Before classifying ingestion health, verify that a behavior graph exists.
This is the first gate — no graph means no investigation capability.

Live-account pre-flight checks (run from the Detective administrator account: ListGraphs permission, GuardDuty list-detectors reachability, delegated-admin verification) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load them before any live-account audit; skip them for offline configuration audits.

**Multi-region sweep note:** Detective is REGIONAL — each region has its
own independent behavior graph. A graph in `us-east-1` provides zero
investigation capability for findings in `eu-west-1`. When auditing
enterprise coverage, enumerate ALL enabled regions (via
`aws account list-regions` or `aws ec2 describe-regions`) and check
each independently. A common blind spot is enabling Detective only in
the primary region and assuming it covers the entire org.

## Process — Classification logic (apply in order, first match wins)

### Step 0: Expert knowledge — non-obvious Detective behaviors

Step 0 expert knowledge — all twelve non-obvious Detective behaviors (GuardDuty as primary trigger, DETECTIVE_CORE mandatory package, 50-day invitation window, ACCEPTED_BUT_DISABLED silent failure, per-member package states, lastDataReceived ingestion-vs-processing lag, irreversible graph deletion, delegated-admin auto-enrollment, per-GB pricing, auto-ingested VPC Flow Logs, one unified admin graph, bidirectional Security Hub integration) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load it whenever a subtle behavior could change the verdict.

### Step 1: Graph existence (NO_GRAPH)

Check whether a behavior graph exists in the target region:

- **No graph ARN returned by `list-graphs`** → **NO_GRAPH**. There is
  zero investigation capability. All downstream checks are moot. This is
  the most fundamental gap — if an incident occurs, there is no graph to
  query, no entity profiles, no behavior baselines.

- **Graph exists** → proceed to Step 2.

NO_GRAPH is always the final verdict when triggered — there is no point
checking member ingestion or data freshness for a graph that does not
exist. Emit the verdict and stop.

### Step 2: Member account ingestion (INCOMPLETE_INGESTION)

For an existing graph, verify that all expected member accounts are
actively ingesting. This step has three sub-checks; any one triggers
INCOMPLETE_INGESTION.

**Step 2a: Member count vs organization size.**

If the graph is the admin graph for an Organization with N accounts, and
the member list contains fewer than N-1 accounts (excluding the admin
itself), accounts are missing. An org with 10 accounts and 3 Detective
members has 7 blind spots — those accounts have zero representation in
the behavior graph.

For standalone (non-org) accounts, this check is N/A — the admin account
is the only member.

**Step 2b: Member state classification.**

For each member account returned by `list-members`, classify the state:

- **ENABLED** — actively ingesting. Healthy.
- **INVITED** — invitation sent but not accepted. If the invitation was
  sent > 50 days ago, it has expired and the account is a blind spot.
  Even within the window, INVITED means zero data is being contributed.
- **ACCEPTED_BUT_DISABLED** — previously enabled, now disabled. Zero
  ingestion. This is a silent failure that is easy to overlook because
  the account appears in the member list.

Any member in INVITED or ACCEPTED_BUT_DISABLED state triggers
INCOMPLETE_INGESTION.

**Step 2c: Data-source package state per member.**

For each ENABLED member, check the DETECTIVE_CORE data-source package
state via `batch-get-graph-member-datasources`:

- **COLLECTING** — actively ingesting. Healthy.
- **STARTING** — transitioning to enabled. Transient; acceptable if
  the member was recently added (< 1 hour). If STARTING persists beyond
  1 hour, treat as STOPPED (ingestion failure).
- **STOPPED / DISABLED** — not ingesting. The core data-source is off;
  the member contributes nothing to the graph even though it is in
  ENABLED state at the graph level.

Any member with DETECTIVE_CORE not in COLLECTING state triggers
INCOMPLETE_INGESTION.

If all members are ENABLED with DETECTIVE_CORE COLLECTING, proceed to
Step 3.

### Step 3: Data freshness (STALE_DATA)

For each member with DETECTIVE_CORE in COLLECTING state, evaluate
`lastDataReceived`:

- **lastDataReceived within 24 hours** → data is fresh. Proceed.
- **lastDataReceived > 24 hours** → **STALE_DATA**. The ingestion
  pipeline is degraded or broken. The member's data in the graph does
  not reflect current state, and investigations will be based on stale
  entity profiles.

The 24-hour threshold accounts for Detective's inherent processing lag
(up to 12 hours) plus a margin for normal ingestion delay. A
lastDataReceived of 24+ hours indicates a genuine pipeline problem, not
normal latency.

**Expert note:** stale data is particularly dangerous because the graph
appears functional — entity profiles exist, finding correlations are
present — but the underlying data may be days old. During an incident,
investigators trust the graph without realizing it does not reflect
recent activity. Always check freshness before trusting investigation
results.

If all members have fresh data, proceed to Step 4.

### Step 4: Configuration gaps (CONFIG_GAP)

Even when the graph, members, and data are healthy, configuration gaps
can undermine investigation readiness:

**Step 4a: GuardDuty detector status.**

Check whether a GuardDuty detector is enabled in the same region:

- **No detector / detector status DISABLED** → **CONFIG_GAP**. Without
  GuardDuty, Detective has no security findings to investigate. The graph
  contains CloudTrail and VPC Flow data but lacks the security-signal
  layer that makes Detective useful for incident response.

- **Detector status ENABLED** → GuardDuty integration is healthy.
  Proceed.

**Step 4b: Organizations delegated admin (org environments only).**

For Organization-managed Detective deployments, verify a delegated admin
account is designated:

- **No delegated admin** → **CONFIG_GAP**. Without delegated admin, new
  org accounts are not automatically invited — each must be manually
  added, and this is frequently forgotten. The graph will develop
  coverage gaps as the org grows.

- **Delegated admin configured** → healthy. Proceed.

For standalone accounts, skip this check.

If all config checks pass, proceed to Step 5.

### Step 5: Aggregation (OK)

If all steps passed (graph exists, all members ENABLED and COLLECTING,
data fresh, GuardDuty integrated, org admin designated), the verdict is
**OK**. The behavior graph provides full investigation coverage for the
target region and all member accounts.

## Output format (per behavior graph or audit scope)

```text
GRAPH: <graph-arn or audit-scope-identifier>
VERDICT: NO_GRAPH | INCOMPLETE_INGESTION | STALE_DATA | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its step number>
FINDINGS:
  - [<severity>] <finding description (Step N)>
  - [<severity>] <finding description (Step N)>
  - [OK] <dimension that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

**When no graph exists (NO_GRAPH verdict):** the GRAPH field must contain the
audit scope identifier (region + account or the named audit scope from the
input), NOT "None" — the auditor always identifies what was audited. Example:
`GRAPH: no-graph-no-detector (us-east-1 / 111111111111)`.

### Worked example — member invitation pending

```text
GRAPH: arn:aws:detective:us-east-1:111111111111:graph:invitation-pending-incomplete
VERDICT: INCOMPLETE_INGESTION
REASON: Graph exists but 2 of 5 member accounts are in INVITED state with no
data ingestion — 40% of the org has no investigation coverage (Step 2b).
FINDINGS:
  - [HIGH] Member 222222222222 in INVITED state, invitation sent 35 days ago (Step 2b)
  - [HIGH] Member 333333333333 in INVITED state, invitation sent 52 days ago — likely expired (Step 2b)
  - [MEDIUM] Member 444444444444 DETECTIVE_CORE in STARTING state for 3 hours — treat as STOPPED (Step 2c)
  - [OK] Graph ARN exists in us-east-1 (Step 1)
REMEDIATION:
  1. Re-send invitation to 222222222222 and 333333333333:
     aws detective create-members --graph-arn <arn> --accounts '[{"AccountId":"222222222222",...}]'
  2. Check data-source state for 444444444444:
     aws detective batch-get-graph-member-datasources --graph-arn <arn> --account-ids 444444444444
```

## Anti-Patterns — NEVER

- NEVER treat a graph with INVITED members as fully covered. INVITED
  means the account was invited but has not accepted — zero data is being
  contributed. An INVITED member is a blind spot, not a covered account.
  The investigation graph is only as complete as its actively ingesting
  members.

- NEVER assume a member in ENABLED state is ingesting data. ENABLED is
  the graph-level membership state; the DETECTIVE_CORE data-source
  package can independently be in STOPPED or DISABLED state. Always check
  `batch-get-graph-member-datasources` for the actual ingestion state —
  a STOPPED DETECTIVE_CORE means the member contributes nothing.

- NEVER treat a graph without GuardDuty as investigation-ready. The
  behavior graph still ingests CloudTrail and VPC Flow Logs, but without
  GuardDuty findings there is no security-signal layer. An incident
  responder querying a GuardDuty-less graph will find entity profiles but
  no findings to pivot from. This creates false confidence.

- NEVER assume Detective covers all regions because it is enabled in one.
  Detective is REGIONAL — each region has an independent graph. A graph
  in us-east-1 provides zero coverage for findings in ap-southeast-1.
  When auditing enterprise coverage, enumerate ALL regions.

- NEVER ignore ACCEPTED_BUT_DISABLED members. This state is a silent
  failure — the account appears in the member list (it was once active)
  but is contributing zero data. It is easy to overlook because it does
  not appear as a new invitation. Always classify member states
  explicitly.

- NEVER recommend deleting a behavior graph without warning about data
  loss. Graph deletion is irreversible — all historical entity profiles,
  behavior baselines, and finding correlations are permanently destroyed.
  Re-enabling Detective starts from zero; it takes weeks to rebuild
  behavioral baselines. This is a one-way door.

- NEVER assume lastDataReceived reflects real-time graph state. The
  timestamp measures ingestion time, not processing time. Detective has
  an additional processing lag of up to 12 hours. A lastDataReceived of
  6 hours ago may mean the graph is 18 hours behind real-time activity.

- NEVER treat EKS_AUDIT or EKS_RUNTIME STOPPED as an ingestion failure.
  These are additive data-source packages. DETECTIVE_CORE is the
  mandatory package. If EKS packages are STOPPED but DETECTIVE_CORE is
  COLLECTING, the graph is functional — it lacks EKS-specific telemetry
  but is not blind. Note it as a CONFIG_GAP, not INCOMPLETE_INGESTION.

- NEVER confuse the admin account perspective with the member account
  perspective. The admin account sees all member data in a unified graph;
  member accounts see only their own data. For org-wide investigation
  readiness, always audit from the admin account. A member account
  auditing itself will see a healthy single-member graph and miss all
  cross-account blind spots.

- NEVER treat STARTING state as healthy if it persists beyond 1 hour.
  STARTING is a transient state during package enablement. If it lasts
  more than 1 hour, the enablement has likely failed silently. Treat as
  STOPPED and investigate the root cause.

## Pre-flight safety checks (run before any remediation CLI)

Pre-flight safety checks (CONFIRM gate before state-changing CLIs, irreversible graph deletion, no data backfill on member re-enable, one-time delegated-admin designation, admin-account verification, additive-change preference) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load them before emitting or executing any remediation CLI.

## Remediation guidance

### For NO_GRAPH — behavior graph does not exist

1. Enable Detective in the target region:
   `aws detective create-graph --region <region>`
2. Verify GuardDuty is enabled in the same region:
   `aws guardduty list-detectors --region <region>`
   If empty, create a detector:
   `aws guardduty create-detector --enable --region <region>`
3. For Organizations, designate a delegated admin:
   `aws detective enable-organization-admin-account --account-id <admin-id>`
4. Invite member accounts (or rely on auto-enrollment if delegated admin
   is configured).

### For INCOMPLETE_INGESTION — members not actively ingesting

**INVITED members:**
1. Re-send invitations for expired (> 50 days) or stale invitations:
   `aws detective create-members --graph-arn <arn> --accounts <account-list> --message <invitation-message>`
2. Verify acceptance: `aws detective list-members --graph-arn <arn>`
   — state should transition from INVITED to ENABLED.

**ACCEPTED_BUT_DISABLED members:**
1. Re-enable the member:
   `aws detective start-monitoring-member --graph-arn <arn> --account-id <id>`
2. Verify DETECTIVE_CORE transitions to COLLECTING:
   `aws detective batch-get-graph-member-datasources --graph-arn <arn> --account-ids <id>`

**DETECTIVE_CORE STOPPED on ENABLED member:**
1. Re-enable the data-source package:
   `aws detective batch-enable-disable-data-source-packages --graph-arn <arn> --account-ids <id> --data-source-packages DETECTIVE_CORE`
2. Verify state transitions to COLLECTING within 1 hour.

**Missing member accounts (org has accounts not in the graph):**
1. If delegated admin is configured, verify auto-enrollment is working:
   `aws detective describe-organization-configuration`
2. If no delegated admin, manually invite missing accounts:
   `aws detective create-members --graph-arn <arn> --accounts <account-list>`

### For STALE_DATA — lastDataReceived > 24h

1. Check IAM permissions for the member account's Detective service-linked
   role (`AWSServiceRoleForDetective`). If the role was deleted, Detective
   cannot ingest data.
2. Verify the member account is active and not suspended:
   `aws organizations describe-account --account-id <id>`
3. Check CloudTrail is logging in the member account — Detective ingests
   CloudTrail management events. If CloudTrail is stopped or misconfigured,
   Detective loses its primary telemetry source.
4. Verify VPC Flow Logs are enabled for VPCs in the member account.
5. If all prerequisites are healthy but data is still stale, open an AWS
   Support case — the ingestion pipeline may have a service-side issue.

### For CONFIG_GAP — GuardDuty disabled or no delegated admin

**GuardDuty detector disabled:**
1. Enable GuardDuty in the region:
   `aws guardduty create-detector --enable --region <region>`
2. Verify Detective picks up the detector — Detective auto-discovers
   GuardDuty findings in the same region. No manual integration step.

**No Organizations delegated admin:**
1. Designate a delegated admin account:
   `aws detective enable-organization-admin-account --account-id <admin-id>`
2. This enables auto-enrollment for all current and future org member
   accounts. Existing members are not automatically migrated — verify
   they remain ENABLED after the designation.

### For OK

1. No remediation required for the current posture.
2. Recommend enabling EKS_AUDIT and EKS_RUNTIME data-source packages
   if the org uses EKS — these provide EKS-specific investigation
   telemetry.
3. Recommend periodic freshness audits (weekly) to catch silent ingestion
   failures early.
4. For multi-region environments, verify Detective is enabled in all
   regions where GuardDuty findings may originate.

## Recent AWS features (2024-2026)

Recent AWS features (2024-2026) — EKS_RUNTIME data-source package, Security Hub ASFF integration, auto-enrollment enhancements, data-source package lifecycle APIs, pricing visibility — moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load it when auditing EKS packages or newly added Detective APIs.

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — Step 0 expert-knowledge deep dive and Recent AWS features (2024-2026) moved from SKILL.md
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — live-account pre-flight checks and pre-flight safety checks moved from SKILL.md

## Domain

AWS CloudOps / Security Investigation & Incident-Response Readiness.

## AWS documentation

- **Amazon Detective User Guide** — https://docs.aws.amazon.com/detective/latest/userguide/
- **Amazon Detective Security** — https://docs.aws.amazon.com/detective/latest/userguide/security.html
- **Amazon Detective API Reference** — https://docs.aws.amazon.com/detective/latest/APIReference/
- **AWS CLI Detective Reference** — https://docs.aws.amazon.com/cli/latest/reference/detective/
- **Amazon Detective pricing** — https://aws.amazon.com/detective/pricing/
- **GuardDuty + Detective integration** — https://docs.aws.amazon.com/detective/latest/userguide/detective-overview.html#detective-overview-source-data
