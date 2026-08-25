---
name: config-recorder-coverage-auditor
description: 'Audits AWS Config posture across all four coverage layers — configuration recorder (existence, status, resource-type scope), delivery channel (S3 delivery health, bucket accessibility), Config rules (deployed count, rule type), and conformance packs (deployment status). Detects silent coverage gaps: allSupported=false losing new resource types, includeGlobalResourceTypes false in every region (global resources never recorded), delivery channel FAILURE status (deleted bucket or missing bucket policy), and custom Lambda rules whose Lambda was deleted (rule frozen, no evaluations). Emits a deterministic verdict per region: INCOMPLETE_COVERAGE | NO_RULES | DELIVERY_GAP | CONFIG_GAP | OK. Use when checking Config recorder coverage, validating delivery-channel health, auditing conformance-pack deployment, or verifying multi-region Config completeness.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline configuration-data classification. Live-account audits use aws configservice describe-configuration-recorders, describe-configuration-recorder-status, describe-delivery-channels, describe-delivery-channel-status, describe-config-rules, and describe-conformance-packs (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Governance
  verdict_shape: INCOMPLETE_COVERAGE | NO_RULES | DELIVERY_GAP | CONFIG_GAP | OK
  when_to_use: Auditing AWS Config recorder coverage before a compliance assessment, validating delivery-channel health, checking whether all resource types and regions are recorded, verifying conformance-pack deployment, or diagnosing why Config rules show stale compliance results.
  activation_triggers: audit AWS Config coverage, check Config recorder status, is Config recording all resources, Config delivery channel health, conformance pack deployment status, multi-region Config audit, Config rules coverage gap, Config recorder not recording
  invocation_schema: 'Input: either (a) a set of AWS Config API responses (describe-configuration-recorders, describe-configuration-recorder-status, describe-delivery-channels, describe-delivery-channel-status, describe-config-rules, describe-conformance-packs) for one or more regions, OR (b) a region/account identifier for live-account audit. Output: deterministic AUDIT/REGION/VERDICT/REASON/FINDINGS/REMEDIATION block per region, where VERDICT is one of {CONFIG_GAP, DELIVERY_GAP, INCOMPLETE_COVERAGE, NO_RULES, OK}.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: AWS Config, configuration recorder, delivery channel, conformance packs, Config rules, allSupported, includeGlobalResourceTypes, recorder status, delivery channel status, global resource types, compliance posture, coverage audit, multi-region Config, Config aggregator, AWSServiceRoleForConfig, governance
  tags: aws-config, governance, compliance, recorder, delivery-channel, conformance-packs, coverage-audit
---

# Config Recorder Coverage Auditor

## Mindset

**One-line takeaway:** AWS Config has four independent layers that must ALL
be healthy for complete coverage — recorder (records changes), delivery
channel (persists to S3), coverage scope (which resources and regions), and
rules (evaluates compliance). A failure in ANY layer creates a different
type of silent gap, and the verdict captures WHICH layer is broken.

- **Recorder** is the foundation: without it, no configuration changes are
  captured at all.
- **Delivery channel** is the persistence layer: without it, snapshots and
  history never reach S3, and Config rules cannot evaluate compliance
  against delivered data.
- **Coverage scope** determines breadth: `allSupported: false` silently
  loses new resource types as AWS launches them; `includeGlobalResourceTypes:
  false` in every region means IAM, CloudFront, and Route 53 are never
  recorded anywhere.
- **Rules** are the intelligence layer: without rules, Config provides
  configuration history but no compliance evaluation — you can see what
  changed but not whether it violates policy.

## Critical rules at a glance (do NOT bury these)

These are the rules most commonly missed by non-expert auditors. Read these
BEFORE classifying a region:

1. **`describe-configuration-recorders` returns config, NOT status.** A
   perfectly configured recorder can be stopped or failing. Always also
   check `describe-configuration-recorder-status`.
2. **`allSupported: true` is the cost driver.** Switching from `false` to
   `true` records every resource type, including high-churn ones, and can
   multiply Config costs by 5-10x in large accounts. Always warn the
   operator about cost impact BEFORE recommending the switch.
3. **`includeGlobalResourceTypes: true` should be enabled in exactly ONE
   region** (typically us-east-1). Enabling it in many regions records IAM
   changes N times — duplicated configuration items, inflated S3 cost,
   forensic ambiguity. Enabling it in ZERO regions means IAM, CloudFront,
   and Route 53 are never recorded anywhere.
4. **A conformance pack name in the API response does NOT mean its rules
   are active.** Check `DeploymentStatus` — `ROLLBACK_COMPLETE` and
   `CREATE_FAILED` deployed zero effective rules.
5. **A Config aggregator is NOT a recorder.** A region with only an
   aggregator and no local recorder has a CONFIG_GAP for local coverage.

## Quick reference — verdict thresholds

| Condition | Verdict | Step |
|---|---|---|
| No configuration recorder in the region | **CONFIG_GAP** | Step 1 |
| Recorder exists but `recording: false` (stopped) | **CONFIG_GAP** | Step 1 |
| Recorder `lastStatus: FAILURE` | **CONFIG_GAP** | Step 1 |
| No delivery channel configured | **DELIVERY_GAP** | Step 2 |
| Delivery channel `lastStatus: FAILURE` | **DELIVERY_GAP** | Step 2 |
| Delivery channel `lastErrorCode: NO_SUCH_BUCKET` | **DELIVERY_GAP** | Step 2 |
| Delivery channel `lastErrorCode: ACCESS_DENIED` | **DELIVERY_GAP** | Step 2 |
| `allSupported: false` with explicit resourceTypes | **INCOMPLETE_COVERAGE** | Step 3 |
| `includeGlobalResourceTypes: false` in global-resource region | **INCOMPLETE_COVERAGE** | Step 3 |
| Multi-region: regions missing recorder (any) → worst is CONFIG_GAP | **CONFIG_GAP** | Step 3 |
| Zero Config rules AND zero conformance packs | **NO_RULES** | Step 4 |
| All layers healthy, rules deployed | **OK** | Step 5 |

Verdict priority (worst wins):
`CONFIG_GAP > DELIVERY_GAP > INCOMPLETE_COVERAGE > NO_RULES > OK`.

## Pre-flight: API data requirements

The audit requires data from SIX Config API calls per region. Checking only
a subset produces false "OK" verdicts — a recorder can be configured but
not running, or a delivery channel can exist but be failing silently.

| API call | What it reveals | Layer |
|---|---|---|
| `describe-configuration-recorders` | Recorder config (resource types, role ARN) | Recorder |
| `describe-configuration-recorder-status` | Recorder operational status (running/stopped, last error) | Recorder |
| `describe-delivery-channels` | Delivery channel config (S3 bucket, SNS topic, frequency) | Delivery |
| `describe-delivery-channel-status` | Delivery operational status (SUCCESS/FAILURE, error code) | Delivery |
| `describe-config-rules` | Rule count, type (managed/custom/Lambda), scope | Rules |
| `describe-conformance-packs` | Conformance pack name, deployment status | Rules |

Multi-region sweep commands, pagination/throttling handling, and live-account pre-flight checks (IAM permissions, `AWSServiceRoleForConfig`, aggregator check) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load them before a live-account audit.

**If the input is malformed** (missing required fields, invalid JSON),
output:

```text
AUDIT: <reference>
REGION: <region>
VERDICT: ERROR
REASON: Config API response data is incomplete or malformed — cannot classify.
REMEDIATION: Re-fetch with the six required describe-* calls and re-audit.
```

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious AWS Config behaviors

Step 0 expert knowledge (recorder config vs status, global-resource-type duplication, creeping `allSupported` gaps, delivery error codes, conformance-pack rollback, frozen Lambda rules, quota ceiling, aggregator is NOT a recorder, scope mismatch, overwrite semantics, org packs) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand before classifying edge cases.

### Classification discipline — avoid redundant and over-classified findings

Apply these discipline rules to keep the output concise and actionable:

1. **Suppress downstream findings when an upstream layer is broken.** If
   the recorder is missing or stopped (CONFIG_GAP), DO NOT also emit a
   NO_RULES finding — without a recorder, rules cannot evaluate by
   definition, so the NO_RULES finding is redundant noise. The CONFIG_GAP
   verdict already subsumes it. Only emit findings for layers that are
   independently broken.

2. **One verdict per region, worst wins.** Do not stack verdicts. If a
   region has both INCOMPLETE_COVERAGE and NO_RULES, the verdict is
   INCOMPLETE_COVERAGE (higher severity) and the FINDINGS section lists
   both root causes — but the VERDICT line shows only INCOMPLETE_COVERAGE.

3. **Do not classify awareness notes as findings.** `deliveryFrequency:
   TwentyFour_Hours`, `includeGlobalResourceTypes: true` in a second
   region (cost note), and a single stale `LastEvaluationTime` on a
   managed rule are advisory notes, NOT verdict-driving findings. Put
   them under REMEDIATION as "Advisory:" lines, not under FINDINGS with a
   severity tag.

4. **Do not over-classify healthy layers.** A delivery channel with
   `lastStatus: SUCCESS` and no error code is healthy — do not flag it as
   a DELIVERY_GAP candidate just because the frequency is high. A recorder
   with `recording: true`, `lastStatus: SUCCESS`, and `allSupported: true`
   is healthy — do not flag it because `includeGlobalResourceTypes` is
   false in this particular region (check the multi-region aggregate).

5. **FINDINGS entries must cite the Step and the specific field.** Every
   FINDINGS line must reference which classification step produced it and
   the specific API field/value that triggered it (e.g., "[INCOMPLETE_COVERAGE]
   allSupported: false — only 3 of 200+ resource types (Step 3)").

### Step 1: Recorder existence and status (CONFIG_GAP)

This is the highest-priority check — without a recorder, no other layer
matters.

1. **No recorder in the region** → **CONFIG_GAP**. The `describe-
   configuration-recorders` response is empty. No configuration changes
   are being captured. This is the most severe Config gap.

2. **Recorder exists but `recording: false`** → **CONFIG_GAP**. The
   recorder is configured but has been stopped (either manually via
   `stop-configuration-recorder` or due to an error). The configuration
   looks correct but no recording is happening.

3. **Recorder `lastStatus: FAILURE`** → **CONFIG_GAP**. The recorder is
   attempting to record but failing. The most common causes are: (a)
   missing or misconfigured `AWSServiceRoleForConfig`, (b) the role lacks
   permission to read the target resource types, (c) an internal AWS
   service error. Check `lastErrorMessage` for the specific cause.

4. **Recorder exists, `recording: true`, `lastStatus: SUCCESS`** → proceed
   to Step 2.

### Step 2: Delivery channel health (DELIVERY_GAP)

The delivery channel persists configuration snapshots and history to S3.
Without it, Config records changes internally but the data never reaches
S3 — snapshots are lost and Config rules cannot evaluate compliance against
delivered data.

1. **No delivery channel** → **DELIVERY_GAP**. The
   `describe-delivery-channels` response is empty. Config has nowhere to
   deliver snapshots.

2. **Delivery channel `lastStatus: FAILURE`** → **DELIVERY_GAP**. Surface
   the `lastErrorCode` in the FINDINGS:
   - `NO_SUCH_BUCKET` — the S3 bucket was deleted after channel creation.
   - `ACCESS_DENIED` — the bucket policy does not grant `s3:PutObject` to
     `config.amazonaws.com`.
   - `INTERNAL_ERROR` — transient AWS-side failure; usually self-resolves.

3. **Delivery channel exists, `lastStatus: SUCCESS`** → proceed to Step 3.

**Delivery frequency note:** `deliveryFrequency: TwentyFour_Hours` is the
default and means up to 24 hours of delivery latency. This is not a
DELIVERY_GAP (delivery is working), but note it as a detection-latency
finding in the FINDINGS section for awareness.

### Step 3: Coverage scope evaluation (INCOMPLETE_COVERAGE)

The coverage scope determines which resources are recorded. A narrow scope
creates blind spots.

1. **`allSupported: false`** → **INCOMPLETE_COVERAGE**. The recorder only
   captures explicitly listed `resourceTypes`. New AWS resource types are
   silently excluded. Flag the specific count: "recording N of M+ supported
   resource types." The finding is worse when critical resource types
   (e.g., `AWS::IAM::Role`, `AWS::S3::Bucket`, `AWS::EC2::SecurityGroup`)
   are missing from the list.

2. **`includeGlobalResourceTypes: false` in the global-resource region** →
   **INCOMPLETE_COVERAGE**. If NO region in the account has
   `includeGlobalResourceTypes: true`, global resources (IAM, CloudFront,
   Route 53, S3 bucket-level) are never recorded anywhere. This is the
   hardest gap to detect because every regional recorder appears healthy.
   In a multi-region audit, explicitly check: "is there at least one region
   with `includeGlobalResourceTypes: true`?"

3. **Multi-region audit — regions with CONFIG_GAP or DELIVERY_GAP** → those
   regions get their respective verdict. The aggregate verdict is the worst
   across all regions. A region with no recorder makes the overall audit
   CONFIG_GAP even if other regions are healthy.

4. **`allSupported: true` and at least one region has
   `includeGlobalResourceTypes: true`** → proceed to Step 4.

### Step 4: Rules and conformance packs (NO_RULES)

Rules evaluate compliance. Without rules, Config is a configuration-history
archive, not a compliance tool.

1. **Zero Config rules AND zero conformance packs** → first check
   `describe-organization-conformance-packs` (if the account is a member
   of an AWS Organization with org-level packs deployed). Org-level packs
   do NOT appear in `describe-conformance-packs` but DO enforce rules in
   member accounts. Only if BOTH `describe-conformance-packs` AND
   `describe-organization-conformance-packs` are empty → **NO_RULES**.
   The account has configuration recording but no compliance evaluation.

2. **Config rules exist but all have stale `LastEvaluationTime`** → note
   as a finding (custom Lambda rule may have a deleted function) but do
   NOT set NO_RULES — rules are deployed, just not evaluating. The verdict
   stays at OK if all other layers are healthy; the stale evaluation is a
   FINDINGS-level note.

3. **Rule-scope vs recorder-scope mismatch** → a rule whose `Scope`
   targets resource types NOT in the recorder's `recordingGroup` will
   silently never evaluate (no configuration items exist for it). For
   each rule, cross-check its `Scope` resource types against the
   recorder's recording group. If a rule's target types are entirely
   absent from the recording group, flag it as a finding: "[NO_RULES
   EFFECTIVE] Rule <name> scope targets <types> not in recording group —
   rule will never evaluate (Step 4)." Do NOT change the verdict from
   OK if other rules are evaluating correctly; this is a per-rule
   finding, not a region-level verdict driver.

4. **Conformance packs exist but `DeploymentStatus` is `ROLLBACK_COMPLETE`
   or `CREATE_FAILED`** → the pack deployed zero effective rules. Treat
   as zero rules for this step. Flag the failed pack name and status.

5. **At least one active rule or conformance pack** (direct or
   org-level) → proceed to Step 5.

### Step 5: Aggregation — worst verdict wins

The final verdict is the **maximum severity** across all findings from all
steps, where `CONFIG_GAP > DELIVERY_GAP > INCOMPLETE_COVERAGE > NO_RULES
> OK`:

```text
verdict = max(all_layer_findings)
```

If no findings (all layers healthy), the verdict is **OK**.

## Output format (per region)

```text
AUDIT: <audit-reference>
REGION: <region>
VERDICT: CONFIG_GAP | DELIVERY_GAP | INCOMPLETE_COVERAGE | NO_RULES | OK
REASON: <1-2 sentences citing the worst finding and its step>
FINDINGS:
  - [CONFIG_GAP] <finding description (Step N)>
  - [DELIVERY_GAP] <finding description (Step N)>
  - [OK] <layer that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — recorder running but partial coverage and no rules

```text
AUDIT: prod-compliance-audit
REGION: us-east-1
VERDICT: INCOMPLETE_COVERAGE
REASON: Recorder is running with allSupported: false (only 5 resource types),
delivery channel is healthy, but zero Config rules are deployed. The worst
finding is INCOMPLETE_COVERAGE (Step 3).
FINDINGS:
  - [OK] Recorder exists, recording: true, lastStatus: SUCCESS (Step 1)
  - [OK] Delivery channel lastStatus: SUCCESS, deliveryFrequency: Six_Hours (Step 2)
  - [INCOMPLETE_COVERAGE] allSupported: false — recording only 5 of 200+ resource
    types (Step 3). Missing critical types: AWS::IAM::Role, AWS::S3::Bucket.
  - [NO_RULES] Zero Config rules and zero conformance packs deployed (Step 4)
REMEDIATION:
  1. Set allSupported: true:
     aws configservice put-configuration-recorder \
       --configuration-recorder name=default,roleARN=arn:aws:iam::111:role/service-role/AWSServiceRoleForConfig \
       --recording-group allSupported=true,includeGlobalResourceTypes=true \
       --region us-east-1
  2. Deploy at least the AWS-managed conformance pack:
     aws configservice put-conformance-pack \
       --conformance-pack-name operational-best-practices \
       --template-s3-uri s3://aws-quickstart/config-conformance-packs/operational-best-practices.yaml \
       --region us-east-1
```

## Anti-Patterns — NEVER

- NEVER classify a region as OK based solely on `describe-configuration-
  recorders`. The recorder configuration (what it SHOULD do) is independent
  of its operational status (what it IS doing). A recorder can be
  configured perfectly but stopped or failing. Always check both
  `describe-configuration-recorders` AND `describe-configuration-recorder-
  status`.

- NEVER assume `allSupported: true` means ALL resource types. AWS
  periodically adds new resource types to the auto-include list, but some
  specialized types still require explicit registration. If the input
  provides a discovered-resource-count comparison, flag types that exist in
  the account but are not being recorded.

- NEVER treat a Config aggregator as equivalent to a local recorder. An
  aggregator collects data FROM other regions/accounts — it does not record
  local resources. A region with an aggregator but no local recorder has a
  CONFIG_GAP for local coverage. The aggregator provides cross-region
  visibility, not local recording.

- NEVER assume a conformance pack with a name in the API response means its
  rules are active. Check `DeploymentStatus` — `ROLLBACK_COMPLETE` and
  `CREATE_FAILED` mean zero effective rules. The pack name exists in the
  API but no rules are evaluating compliance.

- NEVER flag `includeGlobalResourceTypes: true` in exactly one region
  (typically us-east-1) as a problem. This is the RECOMMENDED
  configuration. The problem is the OPPOSITE: no region having it enabled,
  or too many regions having it enabled (cost waste from duplicate IAM
  recordings).

- NEVER classify a delivery channel with `lastStatus: SUCCESS` but
  `deliveryFrequency: TwentyFour_Hours` as DELIVERY_GAP. The delivery is
  working — the frequency affects detection latency, not delivery health.
  Note it as an awareness finding, not a verdict-driving finding. Related:
  NEVER treat the delivery-frequency latency itself as a compliance gap or
  escalate `TwentyFour_Hours` into a verdict-driving finding. A slow
  delivery cadence is a detection-latency note (advisory), never a
  DELIVERY_GAP, NO_RULES, or INCOMPLETE_COVERAGE trigger.

- NEVER assume a Config rule with a stale `LastEvaluationTime` means the
  rule is deleted. Custom Lambda-backed rules freeze evaluations when the
  Lambda is deleted, but managed rules simply re-evaluate on their next
  periodic cycle. Check whether the rule is managed or custom before
  diagnosing the cause.

- NEVER recommend deleting a configuration recorder as remediation. Stopping
  or deleting the recorder halts ALL configuration tracking for the region,
  including existing rule evaluations. The remediation for a
  misconfigured recorder is to FIX the configuration, not remove the
  recorder.

- NEVER overlook the `AWSServiceRoleForConfig` service-linked role. If the
  recorder shows `lastStatus: FAILURE`, the most common root cause is a
  missing or misconfigured service-linked role. Check its existence before
  investigating more exotic causes.

- NEVER report INCOMPLETE_COVERAGE without specifying WHICH resource types
  are missing. "allSupported is false" alone is vague — enumerate the
  critical types excluded (IAM roles, S3 buckets, security groups, etc.)
  so the operator can assess the real blind-spot impact.

- NEVER assume `describe-config-rules` returning rules means they are
  actively evaluating. Check `LastEvaluationTime` — a rule that last
  evaluated weeks ago has a dead evaluation engine (deleted Lambda for
  custom rules, or a scope mismatch that excludes all resources).

- NEVER auto-accept the default S3 bucket name generated by the console
  ("config-bucket-<account-id>") without verifying the bucket policy
  grants `s3:PutObject` to `config.amazonaws.com`. A bucket that exists
  but lacks the Config service principal grant produces `ACCESS_DENIED`
  in the delivery channel status — the recorder looks healthy but
  snapshots silently fail to land. Always verify the policy, not just the
  bucket name.

- NEVER recommend an aggressively low `deliveryFrequency` (e.g.,
  `One_Hour`) for cost-sensitive accounts without flagging the cost
  trade-off. Lower frequency means more snapshot deliveries and higher
  S3 PUT + storage costs, especially when `allSupported: true` is also
  enabled. The default `TwentyFour_Hours` is sufficient for most
  compliance regimes; reserve `One_Hour` for high-churn, tightly-regulated
  environments.

- NEVER overlook S3 bucket encryption on the Config delivery target. If
  the delivery bucket lacks server-side encryption (SSE-S3, SSE-KMS), the
  delivery channel may still report `SUCCESS`, but compliance frameworks
  (PCI-DSS, HIPAA, FedRAMP) require encryption at rest. Flag the missing
  encryption as an advisory finding even when delivery is healthy — it is
  not a DELIVERY_GAP but it is a compliance posture gap worth surfacing.

- NEVER assume a rule is evaluating just because it appears ACTIVE in
  `describe-config-rules`. Cross-check the rule's `Scope` resource types
  against the recorder's `recordingGroup`. A rule scoped to
  `AWS::IAM::Role` when the recorder's `resourceTypes` list omits
  `AWS::IAM::Role` (and `allSupported: false`) silently evaluates nothing.
  The rule looks deployed but is dead.

## Pre-flight safety checks (run before any remediation CLI)

Pre-flight safety checks (confirmation gate, recorder backup, service-linked role, `allSupported` cost warning, rule-quota check) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Run them before any remediation CLI.

## Remediation guidance

Remediation guidance per verdict (CONFIG_GAP, DELIVERY_GAP, INCOMPLETE_COVERAGE, NO_RULES, OK — full CLI fixes) moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand when emitting REMEDIATION.

## Recent AWS features (2024-2026)

Recent AWS features (new recordable resource types, conformance-pack updates, aggregator enhancements, evaluation frequency) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when auditing recently changed environments.

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — Step 0 expert-knowledge deep dive and Recent AWS features moved from SKILL.md.
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — multi-region sweep commands, pagination/throttling handling, live-account pre-flight checks, and pre-flight safety checks moved from SKILL.md.
- [references/error-handling.md](references/error-handling.md) — remediation guidance per verdict moved from SKILL.md.

## Domain

AWS CloudOps / Config Governance & Compliance Coverage.

## AWS documentation

- **AWS Config Developer Guide** — https://docs.aws.amazon.com/config/latest/developerguide/WhatIsConfig.html
- **AWS Config Security** — https://docs.aws.amazon.com/config/latest/developerguide/security.html
- **AWS Config API Reference** — https://docs.aws.amazon.com/config/latest/APIReference/
- **AWS Config CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/configservice/
