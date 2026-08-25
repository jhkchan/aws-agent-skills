---
name: ssm-managed-instance-auditor
description: Audits AWS Systems Manager (SSM) managed instances across six dimensions — instance coverage (SSM Agent reachable + IAM profile attached), association compliance, patch baseline adherence, Session Manager vs SSH exposure, inventory collection, and Run Command posture — then emits a deterministic verdict (UNMANAGED | NONCOMPLIANT | NO_SESSION_MANAGER | CONFIG_GAP | OK) per instance with enumerated findings and CLI remediation. Use when reviewing SSM fleet health, checking why an instance is "ConnectionLost" or "Inactive", validating patch compliance, verifying Session Manager coverage (versus open SSH), confirming inventory collection, or hardening operational posture before a compliance gate.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline instance-config classification. Live-account audits use aws ssm describe-instance-information, describe-instance-associations-status, describe-patch-states, describe-sessions, get-inventory, and aws ec2 describe-instances / describe-security-groups (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Management
  verdict_shape: UNMANAGED | NONCOMPLIANT | NO_SESSION_MANAGER | CONFIG_GAP | OK
  when_to_use: Reviewing SSM managed-instance fleet health, diagnosing why an instance stopped pinging (ConnectionLost / Inactive), validating patch baseline compliance, confirming Session Manager coverage (no SSH exposure), checking inventory collection, or hardening operational posture before a compliance gate (CIS, PCI-DSS, SOC 2).
  activation_triggers: audit my SSM managed instances, why is this instance ConnectionLost, is Session Manager enabled, patch compliance status, is the SSM agent running, SSM NON_COMPLIANT count, is inventory collection enabled, AWS-ApplyPatchbaseline failed, open SSH instead of Session Manager, audit hybrid activation instances
  invocation_schema: 'Input: either (a) an SSM instance-info document (describe-instance-information output) paired with association, patch, session, and inventory snapshots, OR (b) an instance-id for live-account audit. Output: deterministic INSTANCE/VERDICT/REASON/FINDINGS/REMEDIATION block per instance, where VERDICT ∈ {UNMANAGED, NONCOMPLIANT, NO_SESSION_MANAGER, CONFIG_GAP, OK, ERROR}.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Systems Manager, SSM, SSM Agent, managed instance, Session Manager, patch baseline, association compliance, inventory collection, Run Command, hybrid activation, mi- instance, AmazonSSMManagedInstanceCore, PingStatus, ConnectionLost, NON_COMPLIANT, AWS-ApplyPatchBaseline, AWS-GatherSoftwareInventory, AWS-UpdateSSMAgent, Patch Group, EC2 IAM profile, ssmmessages VPC endpoint, fleet visibility, operational posture
  tags: ssm, systems-manager, management, patch-compliance, session-manager, inventory, managed-instance, audit
---

# SSM Managed Instance Auditor

## Mindset

**One-line takeaway:** the verdict is the **worst** finding across six
dimensions taken **in order** — coverage first (no coverage = no other
dimension matters), then compliance, then access path, then operational
config. A NON_COMPLIANT instance with a healthy agent is a known,
actionable gap; an UNMANAGED instance is a black box you cannot reason
about further.

SSM is the operations control plane for EC2 and hybrid fleets. Three
behaviours shape every audit:

- **Coverage is binary and upstream of everything.** An instance that is
  not pinging SSM has no association state, no patch telemetry, no
  Session Manager capability, and no inventory. Auditing downstream
  dimensions on an unreachable instance produces noise, not findings —
  classify UNMANAGED and stop.
- **Session Manager eliminates inbound attack surface; SSH adds it.** A
  managed instance that still exposes TCP/22 is "managed and
  exfiltratable". The SSM Agent already provides shell, file transfer,
  and port forwarding with full audit logging — keeping SSH open
  alongside is a redundant, weaker control.
- **Compliance is multi-layered and each layer has a separate API.**
  Association execution status (`Success`/`Failed`) and patch
  compliance status (`COMPLIANT`/`NON_COMPLIANT`) come from different
  calls. A `Success` association can still produce `NON_COMPLIANT`
  patch state if the patch run found missing packages — never treat a
  green association as proof of patch compliance.

## Quick reference — verdict matrix

| Worst finding | Verdict | Rule |
|---|---|---|
| EC2 with no IAM instance profile, or profile missing `AmazonSSMManagedInstanceCore` (or equivalent) | **UNMANAGED** | C-1 |
| Hybrid (`mi-*`) or EC2 instance with `PingStatus: ConnectionLost` / `Inactive`, or `LastPingDateTime` > 1 hour stale | **UNMANAGED** | C-2 |
| Managed instance with CRITICAL/HIGH-severity patch compliance = `NON_COMPLIANT`, or named association in `Failed` state | **NONCOMPLIANT** | P-1 / A-1 |
| Managed instance with inbound TCP/22 from `0.0.0.0/0` (or broad CIDR) AND no recent Session Manager session | **NO_SESSION_MANAGER** | S-1 |
| Missing inventory collection (`AWS-GatherSoftwareInventory` absent, or schema empty), stale agent (`IsLatestVersion: false`), no auto-update association | **CONFIG_GAP** | I-1 / V-1 |
| Coverage healthy, associations green, patches COMPLIANT, Session Manager active, inventory populated, agent current | **OK** | OK |

See the ordered steps below for edge cases. Deep SSM internals (VPC
endpoints, hybrid activation, IMDS, rate limits) are in the
[Deep reference](#deep-reference-ssm-internals) section at the end.

## Pre-flight: instance metadata gate (run before classification)

Several instance attributes **short-circuit** the audit — misclassifying
them produces false positives that erode trust.

**Fleet-wide sweep note (pagination):** `describe-instance-information`
returns at most 50 instances per page (default; `--max-results 50`).
Always drain `NextToken` to completion — the long tail of stale,
offline, or unmanaged instances is exactly where coverage gaps hide.
Cross-reference with `aws ec2 describe-instances --query
Reservations[*].Instances[*].[InstanceId,IamInstanceProfile]` to find
EC2 instances that have **never** appeared in SSM (silent missing-coverage
gap that `describe-instance-information` alone cannot surface).

**Live-account pre-flight checks (skip if doing offline config audit):**

1. Confirm CloudTrail is logging SSM **data-plane** events
   (`StartSession`, `SendCommand`, `StartAutomationExecution`). These
   are *not* on by default for all event types; without them, session
   forensics (Step 4) have no signal.
2. Snapshot `aws ssm describe-instance-information --output json` BEFORE
   any remediation — `PingStatus` and `LastPingDateTime` are
   point-in-time; an agent auto-update triggered mid-audit will change
   them under you.
3. If auditing a private-subnet fleet, confirm the SSM VPC endpoints
   exist (`ssm`, `ssmmessages`, `ec2messages` interface endpoints in
   the instance VPC). Without them, instances cannot reach SSM even with
   the correct IAM role — the agent will show `ConnectionLost` and the
   real cause is networking, not the agent.

| Attribute | Value | Effect on audit |
|---|---|---|
| `ResourceType` | `EC2Instance` | Standard EC2 — evaluate IAM instance profile (C-1). |
| `ResourceType` | `ManagedInstance` | Hybrid activation (`mi-*`) — IAM profile is the activation role. Cannot use EC2 describe-instances; use `describe-instance-information` only. |
| `ResourceType` | `EC2Host` / `EC2MacHost` | Dedicated host / macOS host. Coverage requires host-level SSM setup — different IAM scope. Note as `EC2Host coverage` if absent. |
| `PingStatus` | `Active` + `LastPingDateTime` < 30 min ago | Online — proceed with full audit. |
| `PingStatus` | `ConnectionLost` | Agent stopped checking in (typically < 14 days). Treat as UNMANAGED pending investigation (Rule C-2). |
| `PingStatus` | `Inactive` | Agent has not pinged in ~14+ days. UNMANAGED (Rule C-2). |
| `PlatformType` | `Linux` / `Windows` / `macOS` | Determines default patch baseline (`AWS-<OS>PatchBaseline`) and applicable documents. |
| `IamRoleARN` | absent (EC2) | No instance profile — UNMANAGED (Rule C-1). |
| `IsLatestVersion` | `false` | Agent out of date — may lack Session Manager / Inventory features. CONFIG_GAP (Rule V-1). |

**If the input document is malformed** (invalid JSON, missing required
fields), output:

```text
INSTANCE: <instance-id>
VERDICT: ERROR
REASON: Instance information document is missing required fields (InstanceId, PingStatus) — cannot classify.
REMEDIATION: Re-fetch with `aws ssm describe-instance-information --instance-information-filter-list Key=InstanceIds,ValueSet=<id> --output json` and re-audit.
```

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious SSM behaviors that change classification

These behaviours are easy to misjudge without operational SSM experience.
Each changes a verdict if ignored:

- **`describe-instance-information` only shows instances SSM already
  knows about.** A freshly launched EC2 instance with no IAM profile
  will NOT appear in this API at all. To find the true fleet coverage
  gap, diff `ec2 describe-instances` (full EC2 set) against
  `ssm describe-instance-information` (managed subset). Missing
  instances are UNMANAGED by Rule C-1 — silent coverage holes.

- **`AmazonSSMManagedInstanceCore` is the modern role policy.** Older
  accounts carry the deprecated `AmazonEC2RoleforSSM` (now
  `AmazonSSMRoleForInstancesQuickSetup`). The modern policy adds
  Session Manager, CloudWatch Logs delivery, and Inventory permissions
  that the legacy policy lacks. A "managed" instance on the legacy
  policy may show green associations but lack Session Manager
  capability — classify as CONFIG_GAP (Rule V-2), not OK.

- **`PingStatus` is heartbeat, not health.** `Active` only means the
  agent pinged SSM in the last ~5 minutes; it does NOT mean associations
  are running, patches are current, or Session Manager works. Always
  pair `PingStatus` with `LastPingDateTime` — an instance can be
  `Active` but stale (ping > 1 hour ago indicates a flapping agent).

- **The 5-minute heartbeat is a soft SLA.** The SSM Agent checks in
  approximately every 5 minutes, but transient network blips or
  `DescribeInstanceInformation` eventual-consistency can produce stale
  readings. Treat `LastPingDateTime` > 1 hour as the UNMANAGED
  threshold (Rule C-2); anything 5-60 minutes stale is a soft warning,
  not a verdict driver.

- **`ConnectionLost` vs `Inactive` is a recovery signal.** Both are
  UNMANAGED, but `ConnectionLost` (recent loss) often recovers on agent
  restart; `Inactive` (>14 days) typically means the instance is
  stopped, terminated, or the agent is uninstalled. The remediation
  differs: `ConnectionLost` → investigate network/agent;
  `Inactive` → verify the instance still exists.

- **Patch Group is a TAG, not an association.** Instances are linked to
  a patch baseline via the case-sensitive tag key `Patch Group` (with
  space, capital G). The value maps to a `PatchBaselineName` or
  baseline-defined group. Without this tag, the instance falls back to
  the default regional patch baseline — silently. A "patched" fleet
  with no `Patch Group` tags may be patching against the wrong
  baseline. Flag as CONFIG_GAP (Rule P-2).

- **`AWS-ApplyPatchBaseline` has two Operations: `Scan` and `Install`.**
  `Scan` records compliance but does not patch; `Install` applies
  patches. An association running `Operation=Scan` will keep compliance
  fresh without ever remediating — surface this in findings. The
  default Operation if unspecified is `Scan`.

- **Default baselines are REGIONAL and per-OS.** Each AWS Region has
  `AWS-RunPatchBaseline` (Linux family) and `AWS-WindowsPatchBaseline`
  pre-provisioned by AWS. Custom baselines only take effect if
  explicitly set as default OR selected via `Patch Group` tag. A custom
  baseline that is not "set as default" and has no matching tag is
  dead configuration — flag as CONFIG_GAP.

- **Association status and compliance status are separate APIs.**
  `describe-instance-associations-status` returns the last execution
  status (`Success`/`Failed`/`Pending`). `list-compliance-items`
  returns patch compliance (`COMPLIANT`/`NON_COMPLIANT`). A `Success`
  association can produce `NON_COMPLIANT` compliance (scan found
  missing patches). NEVER treat association green as patch green.

- **Session Manager requires NO inbound ports.** The `ssmmessages`
  traffic is outbound from the instance to the SSM service over
  HTTPS/443. Keeping TCP/22 open "for fallback" defeats the primary
  security benefit. A managed instance with port 22 open to any CIDR
  is NO_SESSION_MANAGER (Rule S-1), regardless of whether Session
  Manager is also configured — the open port is a parallel, weaker
  control.

- **Session logging is opt-in and three-layered.** Session Manager can
  log to (1) S3 (full transcript), (2) CloudWatch Logs (searchable),
  (3) KMS encryption (envelope). Without at least one, sessions are
  unauditable — a compliance failure for most audit frameworks.
  Default is NO logging. Flag absence as CONFIG_GAP (Rule S-3).

- **Hybrid activation `mi-*` instances use the activation role, not an
  EC2 profile.** `IamRoleARN` for `ResourceType: ManagedInstance` comes
  from the activation code/ID exchange at registration time. If that
  role lacks `AmazonSSMManagedInstanceCore`, the instance can register
  but cannot run associations or sessions. Different remediation path
  than EC2 (re-activate with a new role, not re-attach a profile).

- **`AWS-UpdateSSMAgent` is the auto-update association.** Without it,
  the agent only updates on instance stop/start or manual `SendCommand`.
  AWS does not auto-update agents on a schedule by default. Missing
  this association is the root cause of most `IsLatestVersion: false`
  findings (Rule V-1).

- **Rate limits on `SendCommand`:** SSM enforces a per-instance command
  concurrency limit (default 1 concurrent command per instance; a
  second command returns `InvalidInstanceId` or
  `TargetNotConnected`). Diagnose as a transient back-off, not a
  coverage failure.

- **VPC endpoints for private subnets:** three interface endpoints are
  required for fully-private SSM: `ssm`, `ssmmessages`, `ec2messages`.
  Missing any one produces `ConnectionLost` PingStatus even with
  correct IAM and a running agent. This is a NETWORKING failure, not
  an agent failure — remediation is "deploy endpoints", not "restart
  agent".

### Step 1: Coverage check — agent reachable + IAM attached (highest priority)

If the instance is not pinging SSM with the correct IAM role, no other
dimension can be audited. Evaluate coverage first:

**Rule C-1 — Missing IAM instance profile (EC2).** An EC2 instance with
no `IamInstanceProfile.Arn`, or a profile whose attached role lacks
`AmazonSSMManagedInstanceCore` (or the equivalent
`AmazonSSMRoleForInstancesQuickSetup`), is **UNMANAGED**. The SSM Agent
on the instance cannot authenticate to the SSM service without the role.
Output VERDICT: **UNMANAGED**, REASON: "EC2 instance has no IAM instance
profile (or profile lacks AmazonSSMManagedInstanceCore) — SSM Agent
cannot authenticate."

**Rule C-2 — Stale or lost ping.** An instance with `PingStatus` of
`ConnectionLost` OR `Inactive` OR `LastPingDateTime` more than 1 hour
in the past is **UNMANAGED**. The agent is not currently checking in;
any association/patch/session data is stale. Output VERDICT: **UNMANAGED**,
REASON: "SSM Agent ping status is {PingStatus}; last ping {LastPingDateTime}
— instance is not currently controllable via SSM."

**Rule C-3 — Hybrid activation role gap.** For `mi-*` instances
(`ResourceType: ManagedInstance`), the activation's IAM role must
include `AmazonSSMManagedInstanceCore`. If missing, the instance can
register but cannot run associations — treat as UNMANAGED.

Coverage is the upstream gate. **If VERDICT is UNMANAGED, emit findings
and STOP** — do not evaluate patch, session, or inventory state on a
non-reporting instance. Downstream dimensions produce noise.

### Step 2: Association compliance

For each association targeting the instance (from
`describe-instance-associations-status`):

**Rule A-1 — Failed association.** An association with `Status: Failed`
on its most recent execution is a finding. Severity is the **declared
`ComplianceSeverity`** of the association document (CRITICAL > HIGH >
MEDIUM > LOW). A CRITICAL-severity association in `Failed` state drives
VERDICT: **NONCOMPLIANT**. A LOW-severity failure drives CONFIG_GAP at
worst — do not conflate.

**Rule A-2 — Stale association.** An association whose
`ExecutionTime` is more than 24 hours old (and the schedule is more
frequent than daily) is stale — the instance missed a scheduled run.
Flag as CONFIG_GAP (Rule V-3) unless the association is CRITICAL
severity, in which case it is NONCOMPLIANT.

**Rule A-3 — Missing core associations.** An instance without these
core associations is missing operational basics:
- `AWS-UpdateSSMAgent` (auto-update the agent itself) — CONFIG_GAP (Rule V-1).
- `AWS-GatherSoftwareInventory` (inventory collection) — CONFIG_GAP (Rule I-1).
- A patch association running `AWS-ApplyPatchBaseline` — CONFIG_GAP (Rule P-2) unless patch compliance is independently maintained.

The **default SSM Quick Setup** creates these three associations
automatically. Their absence on an EC2 instance suggests the instance
was launched outside Quick Setup, or the associations were deleted.

### Step 3: Patch baseline adherence

For patch state (from `describe-patch-states` /
`list-compliance-items`):

**Rule P-1 — NON_COMPLIANT patch state.** An instance with
`ComplianceStatus: NON_COMPLIANT` and at least one CRITICAL-severity
missing patch drives VERDICT: **NONCOMPLIANT**. The `MissingCount`
and `InstalledRejectedCount` fields quantify the gap.

**Rule P-2 — No patch baseline / no Patch Group tag.** An instance with
no `Patch Group` tag (Linux/Windows) AND no explicit association to a
patch baseline falls back to the AWS-managed default regional baseline
for its OS. This is not a security failure on its own, but it means
your patch governance is implicit. Flag as CONFIG_GAP — your custom
patch approval rules are not applied.

**Rule P-3 — Scan-only patch association.** An association running
`AWS-ApplyPatchBaseline` with `Operation=Scan` keeps compliance
telemetry fresh but does NOT install patches. If the association has
been Scan-only for > 30 days AND the instance is NON_COMPLIANT,
elevate to NONCOMPLIANT — the scan knew about the gap and nothing
remediated it.

**Patch severity mapping:** CRITICAL missing patches → NON_COMPLIANT
finding (drives NONCOMPLIANT verdict). HIGH missing patches on
internet-facing instances → NONCOMPLIANT. HIGH missing on internal
instances → CONFIG_GAP. MEDIUM/LOW missing → CONFIG_GAP at worst.

### Step 4: Session Manager vs SSH

Evaluate the access path — this dimension is about attack surface, not
operational state.

**Rule S-1 — SSH open to broad CIDR with no Session Manager use.** An
instance whose security group allows inbound TCP/22 from `0.0.0.0/0`
or any broad CIDR (e.g. `0.0.0.0/0`, `10.0.0.0/8` when the fleet is
multi-tenant), AND has no recent Session Manager session in
`describe-sessions --state Active` or recent history, drives VERDICT:
**NO_SESSION_MANAGER**. The SSH path is the de-facto access control
and it is weaker than Session Manager (no audit trail, key rotation
burden, lateral movement risk).

**Rule S-2 — SSH open AND Session Manager active.** If both exist, the
SSH rule is redundant. Still flag as a finding (CONFIG_GAP — close the
SSH rule once Session Manager is verified working), but the verdict is
driven by the worst of the *other* dimensions, not NO_SESSION_MANAGER.
The instance has a managed access path; SSH is now technical debt.

**Rule S-3 — Session Manager configured but no logging.** Sessions can
run with no S3 / CloudWatch / KMS logging. This is a CONFIG_GAP — the
access is managed but unauditable. For regulated workloads, treat as
NONCOMPLIANT (compliance framework requires audit trail).

**Rule S-4 — SSH restricted to a single known CIDR (e.g., corporate
NAT).** SSH from a narrow, named egress CIDR is acceptable as a
fallback. Do NOT flag as NO_SESSION_MANAGER — this is defence-in-depth,
not an open exposure. Note as informational.

**Session Manager preconditions (skill knowledge):**
- SSM Agent v2.3.12.0 or later.
- IAM role includes `AmazonSSMManagedInstanceCore` (modern) — the
  legacy `AmazonEC2RoleforSSM` lacks `ssmmessages:*`.
- Caller (human or role) has `ssm:StartSession` on
  `arn:aws:ssm:*:*:session/$SessionId` and on the instance ARN.
- Network path to `ssmmessages.<region>.amazonaws.com` (HTTPS/443) OR
  the `ssmmessages` interface VPC endpoint in private subnets.

### Step 5: Inventory collection

**Rule I-1 — No inventory association.** An instance with no
`AWS-GatherSoftwareInventory` association (or an association with an
empty `Schema`/data-types list) is a CONFIG_GAP. Without inventory,
you have no visibility into installed software, drivers, network
config, or file integrity — incident response and license audits lose
their starting signal.

**Rule I-2 — Stale inventory.** `LastExecutionDateTime` on the
inventory association > 24 hours old (when scheduled more frequently)
is a CONFIG_GAP — inventory is configured but not delivering fresh
data.

**Inventory data types (reference):** `AWS:Application`,
`AWS:File` (with custom paths), `AWS:NetworkConfiguration`,
`AWS:Service` (Windows), `AWS:WindowsUpdate` (Windows),
`AWS:PatchCompliance`, `AWS:PatchSummary`, `AWS:InstanceDetailedInformation`,
`AWS:Component` (custom). The schema is a JSON document on the SSM
Document; an empty schema collects nothing.

### Step 6: Run Command posture (informational — does not drive verdict)

This is a **secondary dimension**. Surface findings but do not let them
drive the verdict unless they reveal a security gap:

- **Outbound SSM command rate:** if `SendCommand` is being invoked more
  than ~10x/minute per instance, the rate-limit kicks in. Operational
  note, not a verdict driver.
- **Command output destination:** commands without S3 or CloudWatch
  output retention lose forensic value. Note as informational.

### Step 7: Aggregation — worst finding wins, in order

The final verdict is the worst across dimensions, evaluated in this
precedence (worst first):

```text
UNMANAGED > NONCOMPLIANT > NO_SESSION_MANAGER > CONFIG_GAP > OK
```

Rationale: an instance you cannot reach is the worst case (black box).
A reachable instance with failed patches is dangerous but observable.
An observable, patched instance with open SSH is a known exposure. An
exposure-free instance with config gaps is operationally immature but
not actively dangerous.

If no findings across any dimension, the verdict is **OK**.

## Output format (per instance)

```text
INSTANCE: <instance-id>
VERDICT: UNMANAGED | NONCOMPLIANT | NO_SESSION_MANAGER | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its rule number>
FINDINGS:
  - [UNMANAGED] <finding description (Rule C-x)>
  - [NONCOMPLIANT] <finding description (Rule P-x or A-x)>
  - [CONFIG_GAP] <finding description (Rule V-x / I-x)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — managed but patch-noncompliant with open SSH

```text
INSTANCE: i-0abc123def456789a
VERDICT: NONCOMPLIANT
REASON: Instance is pinging (Active, 3 min ago) but has 14 CRITICAL
patches missing against baseline `pb-0123456789abcdef0` (Rule P-1).
Separately, security group sg-0123456789abcdef0 allows TCP/22 from
0.0.0.0/0 with no recent Session Manager session (Rule S-1).
FINDINGS:
  - [NONCOMPLIANT] 14 CRITICAL patches missing; ComplianceStatus NON_COMPLIANT (Rule P-1)
  - [NO_SESSION_MANAGER] Inbound TCP/22 from 0.0.0.0/0 on sg-0123456789abcdef0; no Session Manager sessions in last 30 days (Rule S-1)
  - [CONFIG_GAP] `AWS-GatherSoftwareInventory` association absent — no software inventory (Rule I-1)
REMEDIATION:
  1. NON_COMPLIANT — Run a one-time patch install:
     aws ssm send-command --instance-ids i-0abc123def456789a \
       --document-name "AWS-ApplyPatchBaseline" \
       --parameters "Operation=[Install]"
  2. NO_SESSION_MANAGER — Restrict sg-0123456789abcdef0 TCP/22 to your
     corporate egress CIDR, then verify Session Manager works:
     aws ssm start-session --target i-0abc123def456789a
  3. CONFIG_GAP — Add inventory:
     aws ssm create-association --name AWS-GatherSoftwareInventory \
       --targets Key=InstanceIds,Values=i-0abc123def456789a
```

## Edge-case handling

- **Stopped EC2 instance.** A stopped EC2 instance will not appear in
  `describe-instance-information`. Cross-reference
  `ec2 describe-instances --filters Name=instance-state-name,Values=stopped`
  — these are NOT unmanaged, they are offline. Note as informational
  ("stopped, last seen <date>"); do not emit UNMANAGED.

- **Freshly launched instance (< 5 min ago).** The SSM Agent takes 1-5
  minutes to bootstrap on first boot. Treat `LastPingDateTime` absence
  on an instance launched < 5 min ago as PENDING, not UNMANAGED.

- **`mi-*` hybrid instance with expired activation.** Hybrid activations
  have an expiration date; an expired activation blocks new instances
  from registering but does NOT disconnect already-registered ones. If
  a `mi-*` instance is `ConnectionLost`, check activation expiry via
  `aws ssm describe-activations` — different remediation than EC2.

- **Mac instances (`EC2MacHost`).** macOS hosts require a dedicated
  SSM setup (`AmazonSSMMonitoring`, `AmazonSSMMaintenance`,
  `EC2MacHost` resource type). Standard EC2 rules do not apply. Note
  and skip detailed audit if not configured for macOS.

- **Multiple patch baselines for one instance.** If an instance matches
  multiple `Patch Group` tag values, the lexicographically-first
  baseline wins (SSM does not merge). Surface as CONFIG_GAP — the
  governance intent is ambiguous.

- **Association in `Pending` state.** `Pending` is in-flight, not
  failed. Do not flag — re-evaluate after the schedule window passes.

## Anti-Patterns — NEVER

- NEVER treat a `Success` association status as proof of patch
  compliance. Association execution success and patch compliance are
  separate APIs (`describe-instance-associations-status` vs
  `list-compliance-items`). A `Success` `AWS-ApplyPatchBaseline`
  `Operation=Scan` association frequently reports green while the
  compliance state is `NON_COMPLIANT`. The scan ran; the patches are
  still missing.

- NEVER classify an instance as UNMANAGED based solely on absence from
  `describe-instance-information`. That API returns only instances SSM
  already knows about — silent coverage holes (no IAM profile) are
  invisible. Always diff against `ec2 describe-instances` for the true
  coverage gap.

- NEVER treat TCP/22 restricted to a narrow corporate egress CIDR as
  NO_SESSION_MANAGER. A scoped SSH fallback alongside Session Manager
  is defence-in-depth, not an open exposure. Reserve NO_SESSION_MANAGER
  for broad CIDRs (internet, RFC1918 in multi-tenant environments).

- NEVER assume `AmazonEC2RoleforSSM` (legacy) is equivalent to
  `AmazonSSMManagedInstanceCore` (modern). The legacy policy lacks
  `ssmmessages:CreateSession` and several inventory permissions. An
  instance on the legacy policy may show healthy associations but
  cannot use Session Manager — flag as CONFIG_GAP.

- NEVER report an instance as OK when `PingStatus` is `Active` but
  `LastPingDateTime` is more than 1 hour stale. `Active` is a status
  enum, not a freshness timestamp. A stale `Active` means the agent is
  flapping or the SSM control plane has not updated the record —
  investigate before declaring health.

- NEVER skip checking for the `AWS-UpdateSSMAgent` association. Without
  it, the agent only updates on instance reboot or manual command.
  AWS does not auto-update agents on a schedule. Missing this
  association is the leading root cause of `IsLatestVersion: false`.

- NEVER recommend deleting an SSM association as the first remediation
  step. Modify-then-test (e.g., change `Operation=Scan` to `Install`)
  preserves the targeting and schedule; deleting loses the
  configuration context. Use `update-association` before
  `delete-association`.

- NEVER assume a managed instance in a private subnet can reach SSM
  without VPC endpoints. The three required interface endpoints are
  `ssm`, `ssmmessages`, and `ec2messages`. Their absence produces
  `PingStatus: ConnectionLost` even with correct IAM and a healthy
  agent — misdiagnosing this as an agent issue sends operators down
  the wrong remediation path.

- NEVER evaluate patch, session, or inventory state on an instance
  classified UNMANAGED. Downstream data is stale; reporting it
  produces noise and erodes audit trust. Stop at the UNMANAGED
  finding and emit the coverage remediation only.

- NEVER conflate `InstalledPendingCount` with `MissingCount` in patch
  state. `InstalledPending` are patches installed but awaiting reboot
  to finalize (Windows); `Missing` are not installed at all. Both
  count toward NON_COMPLIANT, but the remediation differs (reboot vs
  install).

- NEVER flag Session Manager as NO_SESSION_MANAGER when sessions ARE
  active but logging is absent. That is Rule S-3 (CONFIG_GAP for no
  logging), not Rule S-1 (no Session Manager use). Conflating them
  misroutes remediation.

- NEVER classify a `Patch Group` tag mismatch as a patch compliance
  failure. The patch baseline selected is a configuration choice; if
  the instance is COMPLIANT against whatever baseline it falls under,
  the verdict is OK or CONFIG_GAP (governance ambiguity), not
  NONCOMPLIANT.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`send-command Operation=Install`, `update-association`,
  `delete-association`, `start-session`), the auditor MUST emit:
  `CONFIRM: About to <action> on instance <id> in account <account>.
  This affects <consequence>. Proceed? (yes/no)`. Do NOT execute the
  CLI command until the operator confirms. `AWS-ApplyPatchBaseline`
  with `Operation=Install` reboots Windows instances and may restart
  services on Linux — never auto-trigger.
- **`SendCommand` target blast radius.** Always pass `--instance-ids
  <id>` (single instance) for remediation commands, NEVER
  `--targets Key=InstanceIds,Values=*` or a tag-based target. A
  mis-scoped patch Install can reboot an entire fleet simultaneously.
- **Patch Install pre-flight:** before running `Operation=Install`,
  verify the patch baseline's `ApprovalRules` match the intended
  maintenance window. Custom baselines can auto-approve more than
  expected. Run `aws ssm describe-patch-baseline --baseline-id <id>`
  to confirm.
- **Session start pre-flight:** confirm CloudTrail logs `StartSession`
  data events in the region. Without it, the session is unauditable —
  fix logging BEFORE invoking `start-session` for verification.
- **Association modification:** snapshot
  `aws ssm describe-association --association-id <id> --output json`
  BEFORE `update-association`. SSM keeps association version history
  (up to 99 versions) but explicit rollback is easier with a snapshot.
- **Prefer `RateControl` on SendCommand.** When running fleet-wide
  remediation, set `--max-errors 0` and `--max-concurrency "10%"` —
  halt on first error to avoid cascading bad patches.

## Remediation guidance

**Ordering principle:** fix coverage first (no other dimension
matters on an unreachable instance), then compliance, then access
path, then config gaps. Within each dimension, prefer read-only
verification before state-changing operations.

### For UNMANAGED — coverage gap (Rules C-1, C-2, C-3)

1. **C-1 (no IAM profile on EC2):** Attach the modern instance role:
   ```bash
   aws ec2 associate-iam-instance-profile \
     --instance-id i-0abc123def456789a \
     --iam-instance-profile Name=AmazonSSMManagedInstanceCore-Role
   ```
   Confirm the role exists or create it:
   ```bash
   aws iam create-role --role-name AmazonSSMManagedInstanceCore-Role \
     --assume-role-policy-document file://trust-ec2.json
   aws iam attach-role-policy --role-name AmazonSSMManagedInstanceCore-Role \
     --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
   ```
2. **C-2 (stale ping):** Diagnose in order: (a) instance running?
   (`ec2 describe-instances`); (b) SSM Agent service running on host?
   (`ssm send-command AWS-RunShellScript "systemctl status amazon-ssm-agent"`
   if reachable); (c) VPC endpoints present in the instance's VPC? (d)
   security group allows HTTPS/443 outbound to SSM endpoints?
3. **C-3 (hybrid activation role):** Create a new activation with the
   correct role and re-register the instance:
   ```bash
   aws ssm create-activation --iam-role AmazonSSMManagedInstanceCore-Role \
     --registration-limit 1 --expiry-date $(date -u -v+7d +%Y-%m-%d)
   ```
4. After coverage is restored, RE-RUN the audit — patch, session, and
   inventory data need a fresh collection cycle before they are
   trustworthy.

### For NONCOMPLIANT — failed patches or associations (Rules P-1, A-1)

1. **P-1 (missing patches):** Run a one-time Install (with confirmation):
   ```bash
   aws ssm send-command \
     --instance-ids i-0abc123def456789a \
     --document-name "AWS-ApplyPatchBaseline" \
     --parameters "Operation=[Install]" \
     --max-errors 0 --max-concurrency 1
   ```
   For Windows, plan for a reboot (`AWS-RebootEC2Instance` document).
2. **A-1 (failed association):** Diagnose via:
   ```bash
   aws ssm describe-association-execution-targets \
     --association-id <id> --execution-id <execution-id>
   ```
   Common causes: S3 output bucket deleted, IAM role revoked
   `s3:PutObject`, document parameter mismatch. Fix root cause before
   re-running.

### For NO_SESSION_MANAGER — open SSH with no managed access (Rule S-1)

1. Verify Session Manager prerequisites: agent v2.3.12.0+,
   `AmazonSSMManagedInstanceCore` attached.
2. Test Session Manager:
   ```bash
   aws ssm start-session --target i-0abc123def456789a
   ```
3. After verifying, restrict the SSH security group rule to a narrow
   egress CIDR (or remove the rule entirely if Session Manager is the
   sole intended path):
   ```bash
   aws ec2 revoke-security-group-ingress --group-id sg-xxx \
     --protocol tcp --port 22 --cidr 0.0.0.0/0
   aws ec2 authorize-security-group-ingress --group-id sg-xxx \
     --protocol tcp --port 22 --cidr <corporate-egress>/32
   ```
4. Enable session logging (Rule S-3 remediation):
   ```bash
   aws ssm update-session-manager-preferences \
     --s3-bucket-name <audit-bucket> \
     --cloud-watch-log-group <log-group> \
     --kms-key-id <key-id>
   ```

### For CONFIG_GAP — inventory / agent / logging gaps

1. **V-1 (stale agent):** Create the auto-update association:
   ```bash
   aws ssm create-association --name AWS-UpdateSSMAgent \
     --targets Key=InstanceIds,Values=i-0abc123def456789a \
     --schedule-expression "rate(1 day)"
   ```
2. **I-1 (no inventory):** Create the inventory association with a
   schema:
   ```bash
   aws ssm create-association --name AWS-GatherSoftwareInventory \
     --targets Key=InstanceIds,Values=i-0abc123def456789a \
     --schedule-expression "rate(12 hours)" \
     --parameters "applications=[Enabled],networkConfig=[Enabled]"
   ```
3. **S-3 (no session logging):** See NO_SESSION_MANAGER step 4 above.
4. **P-2 (no Patch Group tag):** Tag the instance to map to your
   custom baseline:
   ```bash
   aws ec2 create-tags --resources i-0abc123def456789a \
     --tags "Key=Patch Group,Value=<baseline-group>"
   ```

### For OK

1. No remediation required for the current posture.
2. Recommend periodic re-audit (weekly) — SSM state drifts as instances
   are launched/terminated.
3. Recommend enabling SSM Change Manager / Incident Manager for
   production fleets (defence-in-depth).

## Deep reference: SSM internals

### Required IAM permissions (per dimension)

| Dimension | API calls | Minimum IAM action |
|---|---|---|
| Coverage | `ssm:DescribeInstanceInformation`, `ec2:DescribeInstances` | `ssm:DescribeInstanceInformation`, `ec2:Describe*`, `iam:ListInstanceProfiles` |
| Associations | `ssm:DescribeInstanceAssociationsStatus`, `ssm:DescribeAssociation` | `ssm:DescribeInstanceAssociationsStatus`, `ssm:DescribeAssociation`, `ssm:ListAssociations` |
| Patch | `ssm:DescribePatchStates`, `ssm:ListComplianceItems`, `ssm:DescribePatchBaselines` | `ssm:DescribePatchStates`, `ssm:ListComplianceItems`, `ssm:DescribePatchBaselines` |
| Session | `ssm:DescribeSessions`, `ec2:DescribeSecurityGroups` | `ssm:DescribeSessions`, `ec2:DescribeSecurityGroups` |
| Inventory | `ssm:GetInventory`, `ssm:ListInventoryEntries` | `ssm:GetInventory`, `ssm:ListInventoryEntries` |
| Run Command | `ssm:ListCommands`, `ssm:GetCommandInvocation` | `ssm:ListCommands`, `ssm:GetCommandInvocation` |

### VPC endpoints (private subnet SSM)

Three interface endpoints are required for SSM in a private VPC without
internet egress:

- `com.amazonaws.<region>.ssm` — control-plane API (`describe-*`,
  `send-command`, `start-session`).
- `com.amazonaws.<region>.ssmmessages` — Session Manager data channel
  (the WebSocket-style message stream for `start-session`).
- `com.amazonaws.<region>.ec2messages` — agent-to-SSM polling
  (`DescribeInstanceInformation` ping, command dispatch).

Without all three, the agent may show `Active` briefly but will degrade
to `ConnectionLost` within ~30 minutes as the polling channel fails.
The endpoint security group must allow HTTPS/443 inbound from the
instance subnet.

### Hybrid activation lifecycle

- `create-activation` returns an `ActivationCode` + `ActivationId`.
  The code is single-use-per-registration and expires at `ExpiryDate`.
- On the on-prem host, `amazon-ssm-agent -register -code <code> -id <id> -region <region>`
  exchanges the code for the activation's IAM role ARN. The instance
  becomes `mi-<uuid>`.
- The IAM role is fixed at registration; rotating it requires
  re-registration with a new activation. There is no
  `replace-iam-role` API for hybrid instances.
- `ActivationCode` is a credential — if leaked, anyone can register
  instances under your account until `RegistrationLimit` is reached or
  `ExpiryDate` passes. Audit `describe-activations` for stale codes.

### Patch baseline mechanics

- Approval rules are JSON on the baseline (`ApprovalRules.PatchRules[]`):
  each rule has `PatchFilterGroup` (CVE/classification), `ApproveAfterDays`
  (auto-approve N days after release), and `ComplianceLevel`
  (CRITICAL/HIGH/MEDIUM/LOW).
- `ApproveAfterDays: 0` means "approve immediately on release" —
  aggressive. `7` is the common safe default for security patches.
- A baseline must be either (a) set as the default for its OS/region
  (`set-default-patch-baseline`), or (b) selected via `Patch Group`
  tag value matching the baseline's name. Both paths are valid; the
  default wins if no tag matches.
- Patch Manager does NOT auto-reboot. Windows patches that require
  reboot show `InstalledPending` until the next reboot. Surface this
  in findings — the patch is "installed" but not "active".

### Session Manager data path

- Control plane: `ssm:StartSession` API → returns a `SessionId` and a
  pre-signed WebSocket URL.
- Data plane: the agent opens a WebSocket to `ssmmessages.<region>` and
  streams shell I/O. This is why `ssmmessages` VPC endpoint is required
  for private subnets.
- Logging: shell I/O is captured and written to S3 (full stream) and
  CloudWatch Logs (line-by-line) asynchronously. Encryption uses a
  customer-managed KMS key if specified; otherwise S3/SSE or
  CloudWatch-managed keys.
- `TerminateSession` revokes active access immediately; the WebSocket
  drops within seconds.

### Agent version feature matrix (reference)

| Agent version | Notable capability added |
|---|---|
| v2.3.12.0 | Session Manager GA |
| v2.3.372.0 | Port forwarding via Session Manager |
| v3.0.xxx | New DynamoDB-backed control plane (faster `DescribeInstanceInformation` convergence) |
| v3.1.xxx | macOS support (host-level registration) |

An agent older than v2.3.12.0 cannot do Session Manager regardless of
IAM — flag as CONFIG_GAP even if `PingStatus: Active`.

## Recent AWS features (2024-2026)

- **SSM Quick Setup (2024):** Quick Setup provides pre-configured SSM baselines (patch policies, session manager, inventory) deployable via CloudFormation. Auditors should verify that Quick Setup configurations match organizational baselines and that Quick Setup-managed resources are not locally overridden.
- **Session Manager port forwarding and SSH proxy (2024-2025):** Enhanced Session Manager with native SSH proxy support and port forwarding without requiring bastion hosts. Auditors should verify that Session Manager logging is enabled for port-forwarding sessions — without logging, port-forwarding creates an unmonitored access path.
- **Hybrid Activator (2024):** SSM Hybrid Activator enables on-premises servers and edge devices to be managed by SSM. Auditors should verify that hybrid-activated instances have appropriate IAM service roles and that the activation code is not shared across environments.
- **Patch baseline enhancements (2024-2025):** Enhanced patch baselines with Amazon Linux 2023 support, Debian/Ubuntu package manager improvements, and patch compliance reporting. Auditors should verify that patch baselines cover all managed OS types in the fleet.
- **SSM Document versioning (2024):** SSM Documents now support versioning. Auditors should verify that association documents reference a specific version (not `$LATEST`) for production stability.

## Domain

AWS CloudOps / Systems Manager Operational Posture & Compliance.

## AWS documentation

- **AWS Systems Manager User Guide** — https://docs.aws.amazon.com/systems-manager/latest/userguide/what-is-systems-manager.html
- **Security** — https://docs.aws.amazon.com/systems-manager/latest/userguide/security.html
- **API Reference** — https://docs.aws.amazon.com/systems-manager/latest/APIReference/
- **CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/ssm/
- **Session Manager** — https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager.html
- **Hybrid Activator** — https://docs.aws.amazon.com/systems-manager/latest/userguide/managed-instances.html
