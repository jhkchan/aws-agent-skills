---
name: bedrock-guardrail-coverage-auditor
description: >-
  Audits Amazon Bedrock Guardrails configurations for model coverage gaps,
  weak or disabled content filters (hate, insult, sexual, violence), missing
  or low-threshold contextual grounding, absent denied topics and word
  filters, DRAFT-vs-READY enforcement status, and per-application bypass
  risk. Emits a deterministic verdict (NO_GUARDRAIL | INCOMPLETE_COVERAGE |
  WEAK_FILTER | CONFIG_GAP | OK) per guardrail or Bedrock deployment with
  enumerated findings and specific remediation. Use when reviewing Bedrock
  Guardrails, checking which models are protected, validating content-filter
  strength, auditing grounding thresholds, or hardening generative AI safety
  posture before production deployment.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline guardrail-config classification.
  Live-account audits use aws bedrock get-guardrail, aws bedrock
  list-guardrails, aws bedrock list-agents, and aws bedrock
  list-knowledge-bases (AWS CLI v2, SSO or key-based credentials).
keywords:
  - Bedrock Guardrails
  - content filter
  - hate
  - insult
  - sexual
  - violence
  - contextual grounding
  - grounding threshold
  - relevance threshold
  - denied topics
  - word filter
  - profanity filter
  - PII filter
  - model coverage
  - guardrail status
  - DRAFT guardrail
  - READY guardrail
  - guardrail version
  - blocked messaging
  - generative AI safety
  - LLM guardrail audit
  - Bedrock agent guardrail
  - knowledge base guardrail
  - hallucination detection
tags: [bedrock, ai-ml, security, guardrails, content-filter, grounding, generative-ai, llm-safety, audit]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: AI/ML
  verdict_shape: "NO_GUARDRAIL | INCOMPLETE_COVERAGE | WEAK_FILTER | CONFIG_GAP | OK"
  when_to_use: >-
    Reviewing a Bedrock Guardrail configuration before production deployment,
    checking which models or agents are protected by a guardrail, validating
    content-filter strength levels, auditing contextual grounding thresholds,
    inspecting denied-topic or word-filter coverage, or hardening generative
    AI safety posture across a Bedrock deployment.
  activation_triggers:
    - "audit this Bedrock guardrail"
    - "are my Bedrock models protected"
    - "check guardrail coverage"
    - "content filter too weak"
    - "grounding threshold too low"
    - "is this guardrail in DRAFT"
    - "which models have guardrails"
    - "Bedrock agent unguarded"
    - "knowledge base guardrail missing"
    - "LLM safety audit"
  invocation_schema: >-
    Input: either (a) a Bedrock Guardrail configuration (contentPolicy,
    contextualGroundingPolicy, topicPolicy, wordPolicy, status, version)
    optionally paired with a model/resource coverage manifest, OR (b) a
    guardrail ID/ARN for live-account audit. Output: deterministic
    GUARDRAIL/VERDICT/RISK/REASON/FINDINGS/REMEDIATION block per guardrail
    or deployment, where VERDICT is one of NO_GUARDRAIL, INCOMPLETE_COVERAGE,
    WEAK_FILTER, CONFIG_GAP, OK, or ERROR.
---

# Bedrock Guardrail Coverage Auditor

## Mindset

**One-line takeaway:** the verdict is always the **worst** finding across
all dimensions, evaluated in the precedence
`NO_GUARDRAIL > INCOMPLETE_COVERAGE > WEAK_FILTER > CONFIG_GAP > OK`.

Bedrock Guardrails are the application-layer safety control for generative
AI on AWS. Three structural facts drive the audit:

- **A guardrail in DRAFT status provides ZERO enforcement.** Only
  `status: READY` intercepts requests. DRAFT is a saved configuration that
  has never been activated — the most common false sense of security in
  Bedrock deployments.
- **Guardrails are per-request, not per-model.** The `guardrailIdentifier`
  is passed in each `converse`/`invoke-model` call or via
  `guardrailConfiguration` on an Agent or Knowledge Base. An application
  that omits the guardrail ID bypasses every filter.
- **`outputStrength: NONE` is worse than `inputStrength: NONE`.** Blocking
  harmful prompts but allowing harmful model responses only protects half
  the surface. For generative AI, the output path is where novel harmful
  content is generated.

## Quick reference — verdict thresholds

| Condition | Verdict | Risk | Step |
|---|---|---|---|
| No guardrail exists, or all guardrails `status: DRAFT` | **NO_GUARDRAIL** | CRITICAL | 1 |
| Guardrail READY but any model/agent/KB/application omits guardrail ID | **INCOMPLETE_COVERAGE** | HIGH | 2 |
| Any core category (HATE/INSULT/SEXUAL/VIOLENCE) `outputStrength: NONE` | **WEAK_FILTER** | HIGH | 3 |
| Contextual grounding threshold < 0.2 (effectively disabled) | **WEAK_FILTER** | HIGH | 4 |
| `blockedInputMessaging`/`blockedOutputsMessaging` empty or default | **CONFIG_GAP** | MEDIUM | 5 |
| Production caller references `guardrailVersion: DRAFT` | **CONFIG_GAP** | MEDIUM | 5 |
| All dimensions pass (READY, full coverage, strong filters, proper config) | **OK** | LOW | 6 |

## Pre-flight: deployment context gate

Before evaluating the guardrail config, classify the deployment context.

**Multi-guardrail sweep (pagination):** `aws bedrock list-guardrails`
returns at most 30 per page. Use `--next-token` to drain all pages. For
each guardrail, page `aws bedrock list-agents` and
`aws bedrock list-knowledge-bases` — both paginate and silently truncate.

| Attribute | Value | Effect |
|---|---|---|
| `status` | `DRAFT` | **NOT enforced.** Jump to Step 1 — highest priority. |
| `status` | `READY` | Proceed with full audit. |
| Guardrail count | 0 | Every model is unguarded — NO_GUARDRAIL. |
| Resource type | Agent / KB | Has own `guardrailConfiguration` — check independently. |
| Cross-region profile | Yes | Guardrail evaluated in invocation region — verify per-region. |

**If the guardrail config is malformed** (invalid JSON, missing `status`),
output `VERDICT: ERROR` with a re-fetch remediation.

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious Bedrock Guardrails behaviors

- **DRAFT is a saved configuration, not an active control.**
  `create-guardrail` creates in DRAFT status. It must be promoted to READY
  via `create-guardrail-version` before intercepting any request. A DRAFT
  guardrail with perfect filters is functionally identical to no guardrail.

- **`outputStrength` is the generative-AI-critical axis.** Content filters
  have separate `inputStrength` (prompt) and `outputStrength` (response).
  `inputStrength: HIGH` + `outputStrength: NONE` blocks harmful prompts
  but does NOT prevent the model from generating harmful text. Always
  verify `outputStrength` first.

- **Grounding threshold 0.0 is silently disabled.** Unlike content filters
  (explicit `NONE`), grounding uses a float 0.0–1.0. Threshold 0.0 means
  everything passes — configured but zero detection. Below 0.2 catches
  almost nothing. Production range is 0.5–0.75.

- **Grounding threshold tradeoff is asymmetric.** Above 0.85 causes
  excessive false-positive blocking; below 0.2 provides no meaningful
  check. Sweet spot for RAG workloads: 0.55–0.70.

- **Guardrails are caller-side, not model-side.** No model-level attachment.
  `guardrailIdentifier` is per `converse`/`invoke-model` call. An IAM
  principal calling `InvokeModel` directly bypasses every guardrail —
  guardrails are application-layer, not IAM/network controls.

- **Agents and KBs have separate guardrail fields.** `create-agent` and
  `create-knowledge-base` each accept `guardrailConfiguration`. An agent
  without this field processes input unguarded even if the underlying model
  is invoked with a guardrail elsewhere.

- **`guardrailVersion: DRAFT` in production is a live-edit risk.** Numbered
  versions are immutable. DRAFT is the working copy — any `update-guardrail`
  instantly changes production behaviour for every caller referencing DRAFT.

- **Guardrails are regional.** A guardrail in us-east-1 has no effect in
  eu-west-1. Multi-region deployments need per-region guardrails.
  Cross-region inference profiles evaluate the guardrail in the invocation
  region.

- **Filter evaluation order:** content policy → topic policy → word policy
  → sensitive information (PII) → contextual grounding. First-matching
  filter is returned in `actionReason`.

- **CONDUCT and MISCONDUCT are newer categories.** The original four are
  HATE, INSULT, SEXUAL, VIOLENCE. CONDUCT (criminal/weaponisation) and
  MISCONDUCT (financial fraud) were added later. Guardrails created before
  these categories shipped default to NONE.

- **PII action: ANONYMIZE vs BLOCK.** ANONYMIZE masks PII and passes the
  response; BLOCK denies the entire request. Missing PII policy means the
  model freely surfaces or echoes PII.

- **`blockedInputMessaging`/`blockedOutputsMessaging` are UX-critical.**
  Empty or default messages leave users confused when content is blocked.

- **Grounding requires model support.** Only available on Claude family,
  Amazon Nova, and certain Titan models. Third-party models on Bedrock may
  not support it — the filter is silently ignored.

- **Guardrail quotas.** Max 10 guardrails per account/region (adjustable).
  Up to 30 denied topics, 10,000 custom words per guardrail.

### Step 1: Guardrail existence and status (highest priority)

If no guardrail exists in the account/region, OR every guardrail has
`status: DRAFT`, classify as **NO_GUARDRAIL** with **CRITICAL** risk.

A DRAFT guardrail is functionally identical to no guardrail — it has never
been promoted to READY and intercepts zero requests. This short-circuits
the audit: no filter configuration in DRAFT provides protection.

### Step 2: Model/resource coverage

If a guardrail is READY, verify every Bedrock resource serving end-user
traffic references it:

- **Agents** — check `guardrailConfiguration.guardrailIdentifier`
  (`aws bedrock get-agent`).
- **Knowledge Bases** — check `guardrailConfiguration`
  (`aws bedrock get-knowledge-base`).
- **Application callers** — every `converse`/`invoke-model` call must pass
  `guardrailIdentifier` (requires code-level review; API has no "list
  callers" operation).

If ANY resource omits the guardrail ID, classify as
**INCOMPLETE_COVERAGE** with **HIGH** risk. Unguarded resources have zero
protection despite the guardrail existing and being correctly configured.
Report coverage as a percentage and list each unguarded resource.

### Step 3: Content filter strength

For each of the four core categories (HATE, INSULT, SEXUAL, VIOLENCE),
evaluate `outputStrength`:

| Condition | Finding |
|---|---|
| All four `outputStrength: NONE` | Content policy disabled → **WEAK_FILTER** |
| Any one `outputStrength: NONE` | That category unprotected on output → **WEAK_FILTER** |
| All present with at least LOW | Minimum baseline met — evaluate quality |
| All at HIGH | Strong posture |

**inputStrength:** if NONE on any category, flag as additional WEAK_FILTER
finding. Should be at least MEDIUM for all four in production.

**CONDUCT/MISCONDUCT:** evaluate based on workload risk profile (additive
findings, not core requirements).

### Step 4: Contextual grounding, denied topics, and word filters

**Contextual grounding:**

| Threshold | Assessment |
|---|---|
| ≤ 0.1 | Effectively disabled → **WEAK_FILTER** |
| 0.11–0.2 | Very weak — borderline |
| 0.21–0.5 | Moderate — acceptable for low-stakes |
| 0.51–0.75 | Strong — recommended production range |
| > 0.85 | Excessive — high false-positive rate |

If `contextualGroundingPolicy` is **absent entirely**, classify as
**CONFIG_GAP** (recommended but not configured — no hallucination layer).
If present with threshold ≤ 0.1, classify as **WEAK_FILTER** (configured
but effectively disabled).

**Denied topics:** absent `topicPolicy` or zero topics → additive CONFIG_GAP
(no domain restriction). Acceptable for general-purpose assistants; a gap
for domain-specific workloads.

**Word filters:** `managedWordListsEnabled: false` and no custom words →
additive CONFIG_GAP (no baseline profanity/hate-speech filtering).

### Step 5: Configuration gaps

Evaluate operational quality — **CONFIG_GAP** (MEDIUM) findings:

- **Empty `blockedInputMessaging`/`blockedOutputsMessaging`** — users get
  no explanation when blocked.
- **`guardrailVersion: DRAFT` in production caller** — live-edit risk;
  production must pin a numbered version.
- **Missing PII policy** — model can freely surface PII.
- **Cross-region deployment without per-region guardrails**.
- **Missing CloudWatch metrics on guardrail activations** — no visibility
  into trigger frequency for threshold tuning.

### Step 6: Aggregation — worst finding wins

```text
verdict = max(step1, step2, step3, step4, step5)
          in precedence: NO_GUARDRAIL > INCOMPLETE_COVERAGE > WEAK_FILTER > CONFIG_GAP > OK
```

If all steps pass → **OK**.

## Output format (per guardrail or deployment)

```text
GUARDRAIL: <guardrail-id or name>
VERDICT: NO_GUARDRAIL | INCOMPLETE_COVERAGE | WEAK_FILTER | CONFIG_GAP | OK
RISK: CRITICAL | HIGH | MEDIUM | LOW
REASON: <1-2 sentences citing the worst finding and its step>
FINDINGS:
  - [CRITICAL] <description (Step N)>
  - [HIGH] <description (Step N)>
  - [OK] <dimension that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — partial coverage with weak output filter

```text
GUARDRAIL: prod-content-guard (grn-abc123)
VERDICT: INCOMPLETE_COVERAGE
RISK: HIGH
REASON: Guardrail is READY with strong content filters, but 2 of 5 Bedrock
resources omit the guardrail ID — those resources are completely unguarded
(Step 2). INSULT outputStrength is NONE, leaving that output path unprotected
(Step 3).
FINDINGS:
  - [HIGH] Agent "content-writer" has no guardrailConfiguration (Step 2)
  - [HIGH] Application "summarizer-app" omits guardrailIdentifier (Step 2)
  - [HIGH] INSULT outputStrength: NONE (Step 3)
  - [OK] Guardrail status READY (Step 1)
  - [OK] SEXUAL/VIOLENCE/HATE at HIGH outputStrength (Step 3)
  - [OK] Grounding threshold 0.55, relevance 0.55 (Step 4)
REMEDIATION:
  1. Add guardrailConfiguration to agent "content-writer":
     aws bedrock update-agent --agent-id <id> \
       --guardrail-configuration guardrailIdentifier=grn-abc123,guardrailVersion=1
  2. Update summarizer-app to pass guardrailIdentifier in converse calls.
  3. Set INSULT outputStrength to HIGH via update-guardrail.
```

## Edge-case handling

- **Multiple guardrails in one account.** Audit each independently; report
  the worst verdict. If models are distributed across guardrails, coverage
  must account for which guardrail each model references.

- **Guardrail shared across agents and KBs.** A single guardrail referenced
  by multiple resources is normal. Verify each points to the correct version.

- **Cross-account deployment.** Guardrails are account-scoped — cannot be
  shared cross-account. Each account needs its own. Flag as CONFIG_GAP if
  multi-account deployment lacks per-account guardrails.

- **Model without grounding support.** If the model lacks grounding
  capability, the filter is silently ignored. Do NOT flag as WEAK_FILTER —
  note as informational. It is a model limitation, not a config error.

- **Guardrail in different region than invocation.** The converse API
  returns ValidationException. Flag as CONFIG_GAP for cross-region inference
  without per-region guardrails.

- **Application code not available.** Note that coverage cannot be fully
  verified. Recommend CloudWatch metrics on guardrail interventions to
  detect unguarded call paths empirically.

## Anti-Patterns — NEVER

- NEVER treat `status: DRAFT` as providing protection. DRAFT intercepts
  zero requests — it is functionally identical to no guardrail. This is the
  most dangerous false positive in Bedrock auditing.

- NEVER assume that because a guardrail exists with strong filters, all
  models are protected. Guardrails are per-request. An application omitting
  `guardrailIdentifier` bypasses every filter. Always verify caller-level
  coverage.

- NEVER classify `outputStrength: NONE` on all four core categories as
  anything other than WEAK_FILTER. The content policy is effectively
  disabled.

- NEVER treat a grounding threshold of 0.0 as "configured and active." It
  means everything passes — the filter is present but functionally
  disabled. This is WEAK_FILTER, not CONFIG_GAP.

- NEVER assume DRAFT version is safe for production. DRAFT is a live-edit
  target — any `update-guardrail` instantly changes production. Production
  must reference a numbered version.

- NEVER ignore the input/output strength asymmetry. `inputStrength: HIGH`
  + `outputStrength: NONE` blocks prompts but NOT model-generated harmful
  content. The output filter is the generative-AI-critical axis.

- NEVER assume a us-east-1 guardrail protects models in other regions.
  Guardrails are regional. Multi-region needs per-region guardrails.

- NEVER flag a model lacking contextual grounding support as WEAK_FILTER.
  Grounding requires model-level support; the filter is silently ignored.
  This is a model limitation, not a config error.

- NEVER recommend deleting a guardrail without verifying no resources
  reference it. Deleting an active guardrail causes ValidationException on
  the next invocation.

- NEVER assume managed word lists are enabled by default. The
  `managedWordListsEnabled` flag must be explicitly set.

- NEVER conflate "no denied topics" with "no topic filtering." Content
  filters still apply. Missing denied topics is CONFIG_GAP (domain gap).

- NEVER assume CloudWatch logs guardrail interventions by default. Log-level
  detail requires explicit configuration. Without monitoring, thresholds
  cannot be tuned.

- NEVER treat ANONYMIZE PII action as equivalent to BLOCK. ANONYMIZE passes
  the response with masked PII; BLOCK denies entirely. The choice depends
  on data-handling requirements.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (update-guardrail, create-guardrail-version, update-agent,
  delete-guardrail), emit:
  `CONFIRM: About to <action> on guardrail <id>. Proceed? (yes/no)`

- **Back up the current config:**
  `aws bedrock get-guardrail --guardrail-id <id> --guardrail-version DRAFT
  --output json > /tmp/<id>-backup-$(date +%s).json`

- **Verify no production callers reference a guardrail before deleting.**

- **Promote DRAFT to numbered version before production rollout:**
  `aws bedrock create-guardrail-version --guardrail-id <id>`

- **After increasing filter strength (MEDIUM→HIGH), test with sample
  inputs.** Higher strength increases false-positive blocking.

- **Cross-region sync:** apply the same config in each region independently.
  Bedrock does not sync guardrails across regions.

## Remediation guidance

**Ordering principle:** always prefer adding protection over removing it.

### For NO_GUARDRAIL — missing or DRAFT

1. If no guardrail: `aws bedrock create-guardrail --name prod-guard
   --content-policy-config file://content.json ...`
2. If DRAFT: `aws bedrock create-guardrail-version --guardrail-id <id>`
3. Update every agent/KB/application to reference the guardrail.

### For INCOMPLETE_COVERAGE — missing model references

1. List unguarded agents: `aws bedrock list-agents
   --query 'agentSummaries[?guardrailConfiguration==null]'`
2. List unguarded KBs: `aws bedrock list-knowledge-bases
   --query 'knowledgeBaseSummaries[?guardrailConfiguration==null]'`
3. Add guardrail ID to each resource. Add `guardrailIdentifier` to every
   `converse` call in application code.

### For WEAK_FILTER — disabled or weak filters

1. Set all four core categories to at least MEDIUM outputStrength:
   `aws bedrock update-guardrail --guardrail-id <id>
   --content-policy-config '[...]'`
2. For grounding ≤ 0.1, increase to 0.5+:
   `aws bedrock update-guardrail --guardrail-id <id>
   --contextual-grounding-policy-config '[{"type":"GROUNDING","threshold":0.55},...]'`
3. Promote DRAFT to a new version and update callers.

### For CONFIG_GAP — operational gaps

1. Set `blockedInputMessaging`/`blockedOutputsMessaging` to clear messages.
2. Pin production callers to numbered versions.
3. Add denied topics for domain-specific restrictions.
4. Enable managed word lists.
5. Add PII filter if handling user data.
6. Create guardrails in every invocation region.

### For OK

1. No remediation required.
2. Recommend periodic threshold tuning via CloudWatch metrics.
3. Add CloudWatch alarms on intervention-rate spikes.
4. For multi-region, verify per-region guardrails.

## Deep reference: Guardrails internals

### Filter evaluation pipeline

When `converse` includes `guardrailIdentifier`, Bedrock evaluates through
the pipeline in fixed order: content policy → topic policy → word policy →
sensitive information (PII) → contextual grounding. The first filter to
trigger returns the block response with `actionReason`.

### DRAFT vs numbered version lifecycle

A guardrail starts as DRAFT (`create-guardrail`). Edits via
`update-guardrail` modify DRAFT. `create-guardrail-version` snapshots DRAFT
into an immutable numbered version. Production callers reference numbered
versions; referencing DRAFT means every edit instantly changes production.

### Regional isolation

Guardrail ARN includes region:
`arn:aws:bedrock:<region>:<account>:guardrail/<id>`. Multi-region
deployments require creating the guardrail in each region independently.
Cross-region inference profiles evaluate the guardrail in the invocation
region, not the model's home region.

## Recent AWS features (2024-2026)

- **Guardrails GA and enhanced (2024-2025):** Bedrock Guardrails moved from preview to GA with new policy types: contextual grounding control (grounding and relevance filters), denied topics, content filters (hate, insult, sexual, violence), word filters, and sensitive information filters (PII and regex). Auditors must check whether all applicable policy types are configured, not just content filters.
- **Cross-region inference profiles (2024):** Guardrails now evaluate on cross-region inference profiles in the invocation region. Auditors should verify that guardrail coverage follows models deployed via inference profiles — a guardrail created in one region may not protect a model invoked through a cross-region profile.
- **Guardrail versioning (2024-2025):** Guardrails support versioned drafts (DRAFT vs READY). Auditors should check that production applications reference a READY-published guardrail version, not a DRAFT, and that outdated versions are cleaned up.
- **Application-level guardrail bypass:** Bedrock applications (Agents, Knowledge Bases) can reference guardrails. Auditors should verify that every model-invoking application has a guardrail attached — the audit surface includes not just standalone models but Agents, Knowledge Bases, and inference profiles.

## Domain

AWS CloudOps / Bedrock Generative AI Safety & Compliance.
