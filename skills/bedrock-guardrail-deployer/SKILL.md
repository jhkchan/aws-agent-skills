---
name: bedrock-guardrail-deployer
description: >-
  Provisions Amazon Bedrock Guardrails with production defaults: guardrail
  creation (name, description, KMS key), content filters (hate, insults,
  sexual, violence with NONE/LOW/MEDIUM/HIGH severity), denied topics
  (custom topics with definition and examples), word filters (managed
  profanity list + custom word list), sensitive information filters (PII
  entities with ALLOW/AUDIT/BLOCK actions + regex patterns), cross-region
  deployment, guardrail application (associate with model invocations and
  Agents), and guardrail evaluation. Emits READY_TO_DEPLOY /
  PREREQUISITES_MISSING with every filter verified and copy-pasteable
  bedrock commands. Use when deploying content moderation and safety
  guardrails for Bedrock model invocations. Triggers: Bedrock Guardrail,
  content filter, denied topic, PII filter, word filter, guardrail
  evaluation, Guardrails with Agents, contextual grounding check.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). Live provisioning uses AWS CLI v2 with bedrock
  (create-guardrail, get-guardrail, update-guardrail, list-guards,
  create-guardrail-version), iam (create-role, attach-role-policy),
  and cloudformation / terraform aws_bedrock_guardrail equivalents.
keywords:
  - aws
  - bedrock
  - guardrail
  - content-filter
  - denied-topics
  - word-filter
  - pii-filter
  - sensitive-information
  - safety
  - content-moderation
  - contextual-grounding
  - cloudops
  - deploy
  - ai-ml
tags:
  - aws
  - bedrock
  - guardrail
  - content-moderation
  - safety
  - deploy
  - ai-ml
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: AI/ML
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  when_to_use: >-
    Creating an Amazon Bedrock Guardrail to filter harmful content
    (hate, insults, sexual, violence), defining custom denied topics
    with definitions and examples, configuring word filters (managed
    profanity + custom words), setting up sensitive information (PII)
    filters with ALLOW/AUDIT/BLOCK actions or regex patterns, deploying
    cross-region guardrails, applying guardrails to model invocations
    or Bedrock Agents, configuring contextual grounding checks, running
    guardrail evaluation, or generating IaC (CloudFormation / Terraform)
    for any of the above. Do NOT invoke for model access provisioning
    (use bedrock-model-access-inventory), or for Knowledge Base creation.
  activation_triggers:
    - "Bedrock Guardrail"
    - "Bedrock content filter"
    - "denied topics"
    - "PII guardrail"
    - "word filter Bedrock"
    - "sensitive information filter"
    - "Guardrail evaluation"
    - "Guardrails with Agents"
    - "contextual grounding check"
    - "guardrail severity levels"
  invocation_schema: >-
    Input: either (a) a guardrail spec with content filter severities,
    denied topics, word filters, PII filters, and optional regex
    patterns, or (b) a cross-region guardrail spec (regions + per-region
    filter configuration). Output: deterministic GUARDRAIL_SPEC /
    VERDICT / CHECKLIST / VERIFICATION_COMMANDS block per the STRICT
    output contract, where VERDICT is READY_TO_DEPLOY or
    PREREQUISITES_MISSING.
---

# Bedrock Guardrail Deployer

## What this skill does

Provisions Amazon Bedrock Guardrails with correct filter configuration
and application. The skill walks a 9-step procedure, surfaces the
silent-failure modes unique to Guardrails (most dangerous: creating a
guardrail but never applying it to model invocations or Agents — the
guardrail exists, passes all audits, and filters nothing; setting
severity to NONE silently disables a filter that appears configured;
PII AUDIT action logs but does not block — operators who assume AUDIT
means BLOCK leave sensitive data in model responses; guardrails are
regional resources that do not auto-replicate, leaving cross-region
invocations unprotected), and emits a READY_TO_DEPLOY checklist
verifying every filter and application target against actual state.
The single most common incident this skill prevents: an operator
creates a comprehensive guardrail with content filters, PII filters,
and denied topics, then never associates it with their model
invocation or Agent — the guardrail exists in the console, passes
review, and silently filters nothing.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **Quick reference** | Provisioning summary (9 steps), verdict thresholds, dependency graph | Before any operation |
| **Activation keywords** | Phrases that route to this skill | Disambiguating routing |
| **Invocation contract** | Required literal labels in the response | Formatting the response |
| **Reasoning framework** | Why the 9-step order matters; filter-action semantics | Understanding the deploy model |
| **Dependency graph** | Which configs silently no-op without their prerequisite | Debugging "guardrail doesn't filter" |
| **Expert heuristic** | The unapplied-guardrail trap; AUDIT-vs-BLOCK confusion; severity NONE | Pre-empt production incidents |
| **Prerequisites** | What to verify before emitting any command | Avoid PREREQUISITES_MISSING rework |
| **9-step procedure** | The actual provisioning with copy-pasteable CLI | Executing the deploy |
| **NEVER (top 5)** | Hard rules that prevent silent exposure / safety gaps | Review before deploy |
| **STRICT output contract** | Required GUARDRAIL_SPEC / VERDICT / CHECKLIST / VERIFICATION_COMMANDS block | Formatting the response |
| **Recent AWS features** | Contextual grounding, Guardrails with Agents, Guardrail evaluation | Stay current |

## Quick reference — provisioning summary (9 steps)

| Step | Action | Reversible? | Key risk if skipped |
|---|---|---|---|
| 1 | Confirm model access and supported region | — | Guardrail created but model invocation fails |
| 2 | Create the guardrail with name, description, KMS key | Yes | **No KMS key → plaintext storage of guardrail config** |
| 3 | Configure content filters (hate, insults, sexual, violence + severity) | Yes | **severity=NONE → filter silently disabled despite appearing configured** |
| 4 | Configure denied topics (name, definition, examples) | Yes | vague definition → over-blocks or under-blocks |
| 5 | Configure word filters (managed profanity + custom words) | Yes | managed list alone misses domain-specific terms |
| 6 | Configure sensitive information (PII) filters with ALLOW/AUDIT/BLOCK | Yes | **AUDIT logs but does not block — PII leaks in responses** |
| 7 | Configure contextual grounding filters (optional) | Yes | grounding threshold too high → blocks legitimate responses |
| 8 | Apply the guardrail to model invocations / Agents | Yes | **guardrail exists but filters nothing if not applied** |
| 9 | Verify every filter and application target against actual state + emit checklist | — | silent no-ops |

**Critical ordering constraints:** model access BEFORE guardrail
creation (the guardrail region must support the target model);
guardrail creation BEFORE filter configuration (filters attach to a
guardrail); filter configuration BEFORE application (applying an empty
guardrail creates a false sense of safety); application BEFORE traffic
starts (the guardrail does nothing until associated with an invocation
or Agent). Cross-region guardrails must be created independently in
each region — there is no auto-replication. Rationale and the
silent-failure table are below.

## Activation keywords

Bedrock Guardrail, Bedrock content filter, hate filter, insults filter,
sexual filter, violence filter, guardrail severity levels, denied
topics, custom topic definition, word filter, managed profanity list,
custom word list, PII guardrail, sensitive information filter, PII
entities, regex pattern filter, ALLOW action, AUDIT action, BLOCK
action, contextual grounding check, guardrail evaluation, Guardrails
with Agents, cross-region guardrail, create-guardrail, guardrail
version, ApplyGuardrail.

## Invocation contract (hard requirement)

When this skill is invoked with a Bedrock Guardrail provisioning
request, the agent MUST respond with the checklist defined in
§"STRICT output contract" using the literal all-caps labels
`GUARDRAIL_SPEC:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels
breaks automation silently.

## Reasoning framework (why the provisioning order matters)

Amazon Bedrock Guardrails look like "set filter levels and you're
safe." The underlying model has four traps:

1. **A guardrail that is not applied filters nothing.** Operators
   create a guardrail, configure filters, and then — nothing. The
   guardrail exists as an independent resource. It must be explicitly
   associated with a model invocation (via `guardrailIdentifier`) or
   a Bedrock Agent. Without this association, the guardrail is inert.

2. **Severity NONE is "explicitly disabled," not "not configured."**
   Each content filter category (hate, insults, sexual, violence) has
   a severity level: NONE, LOW, MEDIUM, HIGH. NONE means the filter is
   OFF. Operators who leave the default or set NONE thinking "I'll
   configure later" have a guardrail that filters nothing.

3. **PII AUDIT logs but does not block.** The sensitive information
   filter has three actions: ALLOW (no action), AUDIT (log but allow
   the response through), and BLOCK (prevent the response). Operators
   who configure PII filters with AUDIT thinking it means "block and
   log" leave sensitive data in model responses.

4. **Guardrails are regional and do not auto-replicate.** A guardrail
   created in us-east-1 does not exist in eu-west-1. Cross-region
   inference or multi-region deployments require per-region guardrail
   creation with identical configurations.

## Dependency graph (silent-failure table)

| Configuration | Hard dependencies (API error without) | Silent failure mode (returns 200, does nothing) | Enables downstream |
|---|---|---|---|
| Guardrail creation | region supports Bedrock; model access enabled | **guardrail created but not applied → exists in console, filters nothing** | filter configuration |
| Content filter (hate/insults/sexual/violence) | guardrail exists; severity set | **severity=NONE → filter explicitly disabled, appears configured, filters nothing** | content moderation |
| Denied topic | guardrail exists; definition + examples | vague definition → over-blocks legitimate queries or under-blocks harmful ones | custom topic blocking |
| Word filter (managed) | guardrail exists; managed profanity enabled | **managed list enabled but no custom words → domain-specific terms pass through** | profanity + custom blocking |
| Word filter (custom) | guardrail exists; custom word list provided | case-sensitivity mismatch → words bypass filter on capitalization variants | domain-specific blocking |
| PII filter | guardrail exists; PII entity + action configured | **action=AUDIT → PII logged but NOT blocked; response contains sensitive data** | sensitive data protection |
| PII regex pattern | guardrail exists; regex pattern + action | regex pattern malformed → matches nothing silently; no PII blocked | custom pattern blocking |
| Contextual grounding | guardrail exists; grounding threshold set | threshold too high → blocks legitimate responses; threshold too low → hallucinations pass | response grounding |
| Guardrail application | guardrail exists with configured filters | **NOT applied to invocation/Agent → entire guardrail is inert; no error surfaced** | active filtering |
| Cross-region guardrail | per-region guardrail in each region | **invocation in region without guardrail → no filtering; no error surfaced** | multi-region coverage |

**The four silent-failure rows are the ones a baseline model misses.**
severity=NONE, PII AUDIT, unapplied guardrail, and missing
cross-region guardrail all produce successful-looking configurations
with no actual filtering. This is why the procedure verifies every
item and the application target.

## Expert heuristic: the unapplied-guardrail trap

The most dangerous Guardrail misconfiguration: a comprehensive
guardrail that is never applied.

```text
Operator thinks:              What actually happens:
"I created a guardrail   →    The guardrail exists as an independent
 with content filters,         resource. It is NOT automatically
 PII filters, and denied       associated with any model invocation
 topics — my app is safe"      or Agent. The model responds with no
                               filtering. The guardrail passes every
                               audit because it IS correctly
                               configured — it is just not wired.
```

The tell-tale signal: CloudWatch shows zero `Bedrock/Guardrail`
invocation metrics despite the guardrail being "active" in the
console. Remedy: explicitly associate the guardrail with every model
invocation via `guardrailIdentifier` and `guardrailVersion`, or
configure it on the Bedrock Agent. Verify with a test prompt that
SHOULD be blocked.

## Expert heuristic: AUDIT-vs-BLOCK confusion for PII filters

The sensitive information filter has three actions:

```text
ALLOW  → no action (PII passes through, no log)
AUDIT  → log the detection but ALLOW the response through
BLOCK  → prevent the response; PII never reaches the user
```

Operators who set AUDIT thinking "block and log" are wrong: AUDIT
means LOG ONLY. The PII detection appears in CloudWatch, but the
response containing the PII is delivered to the user. For compliance,
use BLOCK. Use AUDIT only for monitoring with a documented plan to
switch to BLOCK.

## Expert heuristic: severity levels and filter sensitivity

Each content filter category uses a severity threshold:

```text
NONE   → filter is OFF (no content blocked for this category)
LOW    → blocks only the most severe violations
MEDIUM → blocks moderate and severe violations
HIGH   → blocks all detected violations (most aggressive)
```

The severity is a threshold: setting violence to MEDIUM blocks content
classified as MEDIUM or HIGH. NONE disables the filter entirely. The
default for a new guardrail is NONE for all categories — operators who
accept defaults have no content filtering.

## Prerequisites (verify before provisioning)

Before emitting any provisioning command, verify these prerequisites.
If any are missing, the verdict is **PREREQUISITES_MISSING** with a
specific gap citation.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Region supports Bedrock Guardrails | Not all regions support Guardrails | `aws bedrock list-foundation-models --region <REGION>` |
| Model access enabled in the region | Guardrail applies to model invocations; model must be accessible | `aws bedrock get-foundation-model --modelIdentifier <MODEL> --region <REGION>` |
| Guardrail name (3-128 chars, alphanumeric, hyphens) | Required for creation | manual validation |
| KMS key for guardrail encryption (optional but recommended) | Without KMS, guardrail config stored with service-managed encryption | `aws kms list-aliases --region <REGION>` |
| Content filter severity plan (hate, insults, sexual, violence) | Each category needs a NONE/LOW/MEDIUM/HIGH decision | requirements review |
| Denied topic definitions (if applicable) | Each topic needs a name, definition, and examples | requirements review |
| PII entity list and action (ALLOW/AUDIT/BLOCK) per entity | Each PII type needs an explicit action decision | compliance review |
| Application target (model invocation or Agent ARN) | Guardrail does nothing until applied | `aws bedrock get-agent --agentId <ID> --region <REGION>` |
| Cross-region plan (if multi-region) | Guardrails are regional; each region needs its own guardrail | `aws bedrock list-guards --region <REGION>` per region |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## 9-step provisioning procedure

### Step 1 — Confirm model access and supported region

```bash
# Verify the region supports Bedrock
aws bedrock list-foundation-models --region us-east-1 --output table

# Verify model access (model must be enabled)
aws bedrock get-foundation-model \
  --modelIdentifier anthropic.claude-3-5-sonnet-20241022-v2:0 \
  --region us-east-1
```

**Common mistake:** creating a guardrail in a region where the target
model is not enabled. The guardrail succeeds but cannot be applied.

### Step 2 — Create the guardrail

```bash
aws bedrock create-guardrail \
  --name customer-app-guardrail \
  --description "Guardrail for customer-facing LLM application" \
  --kms-key-id arn:aws:kms:us-east-1:111111111111:key/<KEY_ID> \
  --region us-east-1
```

The guardrail is created with no filters initially. All filters are
configured in subsequent steps. Record the `guardrailId` and
`version` from the response — these are required for application.

**Common mistake:** omitting the KMS key. The guardrail configuration
is stored with service-managed encryption by default. For compliance,
always specify a customer-managed KMS key.

### Step 3 — Configure content filters

```bash
aws bedrock create-guardrail \
  --name customer-app-guardrail \
  --description "Guardrail with content filters" \
  --content-policy-config '{
    "filtersConfig": [
      {"type": "SEXUAL", "inputStrength": "HIGH", "outputStrength": "HIGH"},
      {"type": "VIOLENCE", "inputStrength": "MEDIUM", "outputStrength": "HIGH"},
      {"type": "HATE", "inputStrength": "MEDIUM", "outputStrength": "HIGH"},
      {"type": "INSULTS", "inputStrength": "MEDIUM", "outputStrength": "MEDIUM"},
      {"type": "MISCONDUCT", "inputStrength": "MEDIUM", "outputStrength": "MEDIUM"},
      {"type": "PROMPT_ATTACK", "inputStrength": "HIGH", "outputStrength": "NONE"}
    ]
  }' \
  --region us-east-1
```

Each filter type has `inputStrength` (filters the user's prompt) and
`outputStrength` (filters the model's response). Setting strength to
`NONE` explicitly disables that direction. Common types: SEXUAL,
VIOLENCE, HATE, INSULTS, MISCONDUCT, PROMPT_ATTACK.

**Common mistake:** setting `outputStrength` to NONE thinking "I only
need to filter inputs." The model's response can contain harmful
content even if the input was clean. Always set both input and output
strength.

### Step 4 — Configure denied topics

```bash
aws bedrock create-guardrail \
  --name customer-app-guardrail \
  --topic-policy-config '{
    "topicsConfig": [
      {
        "name": "Financial_Advice",
        "definition": "Requests for investment recommendations, stock tips, or financial planning guidance",
        "examples": [
          "What stocks should I buy?",
          "Should I invest in crypto?",
          "How should I allocate my retirement portfolio?"
        ],
        "type": "DENY"
      },
      {
        "name": "Medical_Diagnosis",
        "definition": "Requests for medical diagnosis, treatment recommendations, or drug dosage advice",
        "examples": [
          "What illness do I have based on these symptoms?",
          "What medication should I take for this pain?"
        ],
        "type": "DENY"
      }
    ]
  }' \
  --region us-east-1
```

Each denied topic requires a `name`, `definition`, at least one
`example`, and `type: DENY`. The definition quality determines filter
accuracy: a vague definition over-blocks legitimate queries or
under-blocks harmful ones.

**Common mistake:** providing a one-line definition with no examples.
The guardrail uses examples to calibrate the topic boundary. Without
examples, the filter relies on the definition alone, which is less
accurate.

### Step 5 — Configure word filters

```bash
aws bedrock create-guardrail \
  --name customer-app-guardrail \
  --word-policy-config '{
    "managedWordListsConfig": [
      {"type": "PROFANITY"}
    ],
    "wordsConfig": [
      {"text": "competitor_product_a"},
      {"text": "competitor_product_b"},
      {"text": "internal_codename"}
    ]
  }' \
  --region us-east-1
```

The managed `PROFANITY` list covers common profanity terms. Custom
words are matched literally in the input and output. For phrases, add
each phrase as a single `text` entry.

**Common mistake:** relying on the managed profanity list alone
without custom words. The managed list covers general profanity but
misses domain-specific terms. Always add custom words for your domain.

### Step 6 — Configure sensitive information (PII) filters

```bash
aws bedrock create-guardrail \
  --name customer-app-guardrail \
  --sensitive-information-policy-config '{
    "piiEntitiesConfig": [
      {"type": "EMAIL", "action": "BLOCK"},
      {"type": "PHONE", "action": "BLOCK"},
      {"type": "SSN", "action": "BLOCK"},
      {"type": "CREDIT_DEBIT_CARD_NUMBER", "action": "BLOCK"},
      {"type": "NAME", "action": "AUDIT"},
      {"type": "ADDRESS", "action": "AUDIT"}
    ],
    "regexesConfig": [
      {
        "name": "Employee_ID",
        "description": "Internal employee ID format: EMP- followed by 6 digits",
        "pattern": "EMP-\\d{6}",
        "action": "BLOCK"
      }
    ]
  }' \
  --region us-east-1
```

PII entities support three actions:
- `ALLOW` — no action (PII passes through, no log)
- `AUDIT` — log to CloudWatch but allow response through
- `BLOCK` — prevent the response from reaching the user

Regex patterns allow custom data format detection (employee IDs,
account numbers, custom formats). Each regex requires a `name`,
`pattern`, and `action`.

**Common mistake:** using AUDIT when you mean BLOCK. AUDIT logs the
detection but the response containing the PII is delivered to the
user. For compliance, use BLOCK. Use AUDIT only for monitoring
deployments with a documented plan to switch to BLOCK.

### Step 7 — Configure contextual grounding (optional)

```bash
aws bedrock create-guardrail \
  --name customer-app-guardrail \
  --contextual-grounding-policy-config '{
    "filtersConfig": [
      {
        "type": "GROUNDING",
        "threshold": 0.75
      },
      {
        "type": "RESPONSE_RELEVANCE",
        "threshold": 0.75
      }
    ]
  }' \
  --region us-east-1
```

Contextual grounding checks verify that the model's response is
grounded in the provided source content (GROUNDING) and relevant to
the user's query (RESPONSE_RELEVANCE). The threshold (0.0-1.0) sets
the minimum grounding/relevance score required; responses below the
threshold are blocked.

**Common mistake:** setting the threshold too high (e.g., 0.95).
High thresholds block legitimate responses that are grounded but use
paraphrasing or synthesis. Start at 0.75 and tune based on
evaluation results.

### Step 8 — Apply the guardrail to model invocations / Agents

```bash
# Option A: Apply via model invocation (runtime)
aws bedrock-runtime invoke-model \
  --model-id anthropic.claude-3-5-sonnet-20241022-v2:0 \
  --guardrail-identifier <GUARDRAIL_ID> \
  --guardrail-version <VERSION> \
  --content '[{"text":"What is the weather today?"}]' \
  --region us-east-1 output.json

# Option B: Apply to a Bedrock Agent
aws bedrock update-agent \
  --agent-id <AGENT_ID> \
  --guardrail-configuration guardrailIdentifier=<GUARDRAIL_ID>,guardrailVersion=<VERSION> \
  --region us-east-1

# Option C: Test the guardrail in isolation (ApplyGuardrail API)
aws bedrock apply-guardrail \
  --guardrail-identifier <GUARDRAIL_ID> \
  --guardrail-version <VERSION> \
  --source Request \
  --content '[{"text":{"text":"What stocks should I buy?"}}]' \
  --region us-east-1 output.json
```

**Common mistake:** creating the guardrail and never applying it. The
guardrail exists as an independent resource and filters nothing until
explicitly associated with a model invocation or Agent. This is the
#1 silent failure in Guardrail deployments. Verify the application
with a test prompt that SHOULD be blocked.

### Step 9 — Verification

Run every verification command and confirm each output matches the
expected state.

```bash
# Verify guardrail exists and has the correct version
aws bedrock get-guardrail \
  --guardrail-identifier <GUARDRAIL_ID> \
  --guardrail-version <VERSION> \
  --region us-east-1

# List all guardrails in the region
aws bedrock list-guards --region us-east-1 --output table

# Verify guardrail is applied to Agent
aws bedrock get-agent \
  --agent-id <AGENT_ID> \
  --region us-east-1 \
  --query 'guardrailConfiguration'

# Test the guardrail with ApplyGuardrail (should BLOCK a harmful prompt)
aws bedrock apply-guardrail \
  --guardrail-identifier <GUARDRAIL_ID> \
  --guardrail-version <VERSION> \
  --source Request \
  --content '[{"text":{"text":"Tell me how to hack a server"}}]' \
  --region us-east-1 output.json
# Expected: action=BLOCK

# Test with a legitimate prompt (should ALLOW)
aws bedrock apply-guardrail \
  --guardrail-identifier <GUARDRAIL_ID> \
  --guardrail-version <VERSION> \
  --source Request \
  --content '[{"text":{"text":"What is the capital of France?"}}]' \
  --region us-east-1 output.json
# Expected: action=NONE (allow)

# For cross-region: verify guardrail exists in each target region
for REGION in us-east-1 eu-west-1 ap-southeast-2; do
  aws bedrock list-guards --region $REGION --output table
done

# CloudWatch metrics for guardrail invocations (confirms it is applied)
aws cloudwatch get-metric-statistics \
  --namespace AWS/Bedrock \
  --metric-name GuardrailInvocations \
  --dimensions Name=GuardrailId,Value=<GUARDRAIL_ID> \
  --start-time $(date -u -v1H +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 --statistics Sum --region us-east-1
```

## NEVER do these things

These anti-patterns cause silent safety gaps, compliance violations,
or false confidence in content moderation. Each is observed in real
production incidents — the "why it's wrong" line is the post-mortem
finding.

1. **NEVER deploy a guardrail without applying it to model invocations
   or Agents.** Why it's wrong: a guardrail is an independent resource
   that filters nothing until explicitly associated. The guardrail
   passes every console audit because it IS correctly configured — it
   is just not wired to the invocation. Always verify with
   `apply-guardrail` and check CloudWatch GuardrailInvocations metrics.

2. **NEVER use AUDIT action for PII filters when compliance requires
   blocking.** Why it's wrong: AUDIT logs the PII detection in
   CloudWatch but the response containing the PII is delivered to the
   user. For compliance (GDPR, HIPAA, PCI-DSS), use BLOCK. Use AUDIT
   only for pre-production monitoring with a documented plan to switch
   to BLOCK.

3. **NEVER set content filter severity to NONE and assume "default
   applies."** Why it's wrong: NONE means the filter is explicitly
   OFF for that category and direction. A guardrail with all
   severities at NONE exists in the console but filters nothing.
   Always set explicit severity levels for each category.

4. **NEVER deploy a guardrail in only one region for a multi-region
   application.** Why it's wrong: guardrails are regional resources
   that do not auto-replicate. An invocation in a region without the
   guardrail gets no filtering, with no error surfaced. Create
   identical guardrails in every region where the application invokes
   models.

5. **NEVER skip the ApplyGuardrail test before production traffic.**
   Why it's wrong: the only way to confirm a guardrail actually filters
   is to send a test prompt that SHOULD be blocked and verify the
   BLOCK action. Without this test, you are relying on configuration
   appearance, not behavior.

## Output format

```
GUARDRAIL_SPEC: <guardrail-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Model access: confirmed in region <region>
  [✓|✗] Guardrail created: id=<id>, version=<version>, KMS=<key-id|service-managed>
  [✓|✗] Content filters: sexual=<H/M/L/N>, violence=<H/M/L/N>, hate=<H/M/L/N>, insults=<H/M/L/N>
  [✓|✗] Denied topics: <n> topics defined with definitions and examples
  [✓|✗] Word filters: managed=PROFANITY, custom=<n> words
  [✓|✗] PII filters: BLOCK=[<entities>], AUDIT=[<entities>], regex=<n> patterns
  [✓|✗] Contextual grounding: GROUNDING=<threshold>, RESPONSE_RELEVANCE=<threshold> | N/A
  [✓|✗] Guardrail applied: target=<model-id|agent-id>
  [✓|✗] Cross-region: <n> regions configured | single-region
VERIFICATION_COMMANDS:
  <copy-pasteable verification commands>
```

## STRICT output contract

The rules below are hard constraints. Violating any one produces a
checklist that looks complete but contains a silent safety gap.
Self-check EVERY emitted block against these rules before returning.

### Required output structure

Every response MUST be a single block using these literal labels, in
this order. Do NOT preface with prose, headings, or disclaimers.

```text
GUARDRAIL_SPEC: <guardrail-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Model access: confirmed in region <region>
  [✓|✗] Guardrail created: id=<id>, version=<version>, KMS=<key-id|service-managed>
  [✓|✗] Content filters: sexual=<H/M/L/N>, violence=<H/M/L/N>, hate=<H/M/L/N>, insults=<H/M/L/N>
  [✓|✗] Denied topics: <n> topics defined with definitions and examples
  [✓|✗] Word filters: managed=PROFANITY, custom=<n> words
  [✓|✗] PII filters: BLOCK=[<entities>], AUDIT=[<entities>], regex=<n> patterns
  [✓|✗] Contextual grounding: GROUNDING=<threshold>, RESPONSE_RELEVANCE=<threshold> | N/A
  [✓|✗] Guardrail applied: target=<model-id|agent-id>
  [✓|✗] Cross-region: <n> regions configured | single-region
VERIFICATION_COMMANDS:
  <copy-pasteable verification commands — one per [✓] item>
```

### FORBIDDEN output patterns

1. **NEVER emit `VERDICT: READY_TO_DEPLOY` without showing ALL 9
   checklist items.** Every item MUST appear with a status marker:
   `[✓]` (applied and verified), `[✗]` (not applied or misconfigured),
   or `[N/A]` (not needed for this workload). Omitting a row implies
   it was not evaluated.

2. **NEVER mark content filters as `[✓]` without citing the specific
   severity per category.** A bare `[✓]` implies "configured" without
   confirming severity levels. The verification MUST show explicit
   severity for sexual, violence, hate, and insults (e.g.,
   `sexual=HIGH, violence=MEDIUM`).

3. **NEVER mark PII filters as `[✓]` without listing which entities
   are BLOCK vs AUDIT.** The distinction between BLOCK (prevents
   response) and AUDIT (logs but allows) is critical for compliance.
   The verification MUST separate BLOCK entities from AUDIT entities.

4. **NEVER mark guardrail application as `[✓]` without citing the
   specific target.** A guardrail that is not applied to a model
   invocation or Agent is inert. The verification MUST cite the
   model ID or Agent ID where the guardrail is associated.

5. **NEVER mark cross-region as `[✓]` without listing the regions.**
   Guardrails are regional resources. A bare `[✓]` implies global
   coverage which does not exist. The verification MUST list each
   region where the guardrail is deployed.

6. **NEVER emit `VERDICT: PREREQUISITES_MISSING` without citing the
   specific gap.** Each `[✗]` item MUST have a one-line reason:
   `[✗] Guardrail not applied to any invocation — associate with
   model or Agent`. A bare `[✗]` with no explanation is non-compliant.

### Perfect example output — READY_TO_DEPLOY

```text
GUARDRAIL_SPEC: customer-app-guardrail
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Model access: confirmed in region us-east-1 (anthropic.claude-3-5-sonnet-20241022-v2:0)
  [✓] Guardrail created: id=abc123def, version=1, KMS=arn:aws:kms:us-east-1:111111111111:key/xyz-789
  [✓] Content filters: sexual=HIGH, violence=MEDIUM, hate=MEDIUM, insults=MEDIUM (input+output)
  [✓] Denied topics: 2 topics defined (Financial_Advice, Medical_Diagnosis) with definitions and examples
  [✓] Word filters: managed=PROFANITY, custom=3 words (competitor_product_a, competitor_product_b, internal_codename)
  [✓] PII filters: BLOCK=[EMAIL, PHONE, SSN, CREDIT_DEBIT_CARD_NUMBER], AUDIT=[NAME, ADDRESS], regex=1 pattern (Employee_ID)
  [N/A] Contextual grounding: not applicable for this workload
  [✓] Guardrail applied: target=anthropic.claude-3-5-sonnet-20241022-v2:0 (guardrailId=abc123def, version=1)
  [✓] Cross-region: single-region (us-east-1)
VERIFICATION_COMMANDS:
  aws bedrock get-foundation-model --modelIdentifier anthropic.claude-3-5-sonnet-20241022-v2:0 --region us-east-1
  aws bedrock get-guardrail --guardrail-identifier abc123def --guardrail-version 1 --region us-east-1
  aws bedrock apply-guardrail --guardrail-identifier abc123def --guardrail-version 1 --source Request --content '[{"text":{"text":"What stocks should I buy?"}}]' --region us-east-1 output.json
  aws cloudwatch get-metric-statistics --namespace AWS/Bedrock --metric-name GuardrailInvocations --dimensions Name=GuardrailId,Value=abc123def --start-time $(date -u -v1H +%Y-%m-%dT%H:%M:%SZ) --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) --period 300 --statistics Sum --region us-east-1
```

### Perfect example output — PREREQUISITES_MISSING

```text
GUARDRAIL_SPEC: customer-app-guardrail
VERDICT: PREREQUISITES_MISSING
CHECKLIST:
  [✓] Model access: confirmed in region us-east-1
  [✓] Guardrail created: id=abc123def, version=1, KMS=arn:aws:kms:us-east-1:111111111111:key/xyz-789
  [✓] Content filters: sexual=HIGH, violence=MEDIUM, hate=MEDIUM, insults=MEDIUM
  [✓] Denied topics: 2 topics defined
  [✓] Word filters: managed=PROFANITY, custom=3 words
  [✗] PII filters: all entities set to AUDIT — compliance requires BLOCK for EMAIL, PHONE, SSN; switch action from AUDIT to BLOCK
  [N/A] Contextual grounding: not applicable
  [✗] Guardrail applied: NOT applied to any model invocation or Agent — guardrail is inert; associate via guardrailIdentifier parameter
  [✗] Cross-region: guardrail only in us-east-1; application also invokes models in eu-west-1 — create identical guardrail in eu-west-1
VERIFICATION_COMMANDS:
  aws bedrock get-guardrail --guardrail-identifier abc123def --guardrail-version 1 --region us-east-1
  aws bedrock list-guards --region eu-west-1 --output table
```

**Self-check before emit:**
- [ ] All 9 checklist rows present (no omitted items)?
- [ ] Every `[✓]` has a matching verification command?
- [ ] Content filters cite explicit severity per category?
- [ ] PII filters separate BLOCK entities from AUDIT entities?
- [ ] Guardrail application cites the specific target (model ID or Agent ID)?
- [ ] Cross-region lists the specific regions (or confirms single-region)?
- [ ] Every `[✗]` cites the specific gap and what the operator must provide?

## Recent AWS features

- **Contextual grounding checks**: the GROUNDING and RESPONSE_RELEVANCE
  filter types verify that the model's response is grounded in provided
  source content and relevant to the user's query. Configured via
  `contextual-grounding-policy-config` with a threshold (0.0-1.0).
  Requires the invocation to include source content (e.g., from a
  Knowledge Base or RAG pipeline).

- **Guardrails with Agents**: Bedrock Agents support guardrail
  association via `update-agent --guardrail-configuration`. The
  guardrail filters both the user's input and the Agent's responses,
  including tool-use and Knowledge Base retrieval augmented responses.

- **Guardrail evaluation**: the `apply-guardrail` API tests a guardrail
  in isolation without invoking a model. Send a test prompt that SHOULD
  be blocked and verify the BLOCK action. Use this to validate filter
  configuration before applying to production traffic.

- **Prompt attack filter**: the PROMPT_ATTACK type detects and blocks
  prompt injection attempts. `inputStrength` sets detection
  sensitivity; `outputStrength` is typically NONE since prompt attacks
  target the input.

- **Misconduct filter**: the MISCONDUCT type detects content involving
  misconduct or inappropriate behavior, extending the original four
  categories (hate, insults, sexual, violence).

- **Cross-region guardrails**: guardrails remain regional resources.
  With cross-region inference, a model invocation from one region may
  route to another — ensure the guardrail exists in every region where
  the model may be invoked, including inference target regions.

- **Guardrail versioning**: each update creates a new version. The
  `guardrailVersion` parameter pins the active version on model
  invocations and Agents. Updating the guardrail does NOT auto-update
  applied versions — operators must explicitly update each target.
