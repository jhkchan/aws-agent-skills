---
name: lex-bot-deployer
description: >-
  Provisions Amazon Lex V2 conversational bots with production defaults:
  bot creation (create-bot), locale setup (en-US and other supported
  locales), intents (sample utterances, slots, slot priorities), slot
  types (built-in AMAZON.Date/AMAZON.Number vs custom enumeration),
  prompt configuration (elicitation, confirmation, closing, failure),
  Lambda code hook (dialog and fulfillment DIALOG_CODE_HOOK and
  FULFILLMENT_CODE_HOOK interception between every turn), fulfillment
  (Lambda or ReturnIntent), conversation logs (text and audio with KMS
  encryption), sentiment analysis (Amazon Comprehend integration), voice
  (Amazon Polly integration, voice_id selection), bot versioning
  (create-bot-version) and alias (create-resource-link) for blue-green
  deployment, lexv2-models vs lexv2-runtime API separation, KMS CMK
  encryption at rest, and channel integration (Twilio, Genesys, Slack,
  Facebook Messenger, Web UI). Emits a READY_TO_DEPLOY checklist with
  verification commands. Use when creating a Lex V2 bot, configuring
  intents and slots, wiring a Lambda dialog code hook, enabling voice or
  sentiment analysis, publishing a bot version and alias, or integrating
  a messaging channel. Triggers: create lex bot, lex v2 intent, lex slot
  type, lex lambda code hook, lex conversation logs, lex polly voice,
  lex bot version alias, lexv2-models, lexv2-runtime, lex channel
  integration.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). For live deployment: AWS CLI v2 with lexv2-models (build-time
  configuration) and lexv2-runtime (conversations) access, plus
  lambda:AddPermission for code-hook wiring and iam:PassRole if a
  service-linked role is customized. Works with Terraform
  aws_lexv2models_bot / aws_lexv2models_bot_version /
  aws_lexv2models_bot_alias resources and CloudFormation
  AWS::Lex::Bot / AWS::Lex::ResourceLink templates.
keywords:
  - aws
  - lex
  - lex v2
  - lexv2-models
  - lexv2-runtime
  - chatbot
  - conversational ai
  - cloudops
  - deploy
  - provisioning
  - intent
  - slot
  - slot type
  - utterance
  - code hook
  - lambda
  - fulfillment
  - elicitation prompt
  - confirmation prompt
  - closing prompt
  - sentiment analysis
  - amazon polly
  - voice bot
  - bot version
  - bot alias
  - blue-green
  - kms encryption
  - conversation logs
  - channel integration
  - twilio
  - genesys
  - slack
tags:
  - aws
  - lex
  - lexv2
  - chatbot
  - cloudops
  - deploy
  - conversational-ai
  - ai-ml
  - provisioning
  - intent
  - slot
  - code-hook
  - voice
  - polly
  - blue-green
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
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - lex
    - lexv2
    - chatbot
    - cloudops
    - deploy
    - conversational-ai
    - ai-ml
    - provisioning
    - intent
    - slot
    - code-hook
    - voice
    - polly
    - blue-green
  dependencies:
    - aws-orchestrator
  keywords:
    - create lex bot
    - lex v2 intent
    - lex slot type
    - lex lambda code hook
    - lex conversation logs
    - lex polly voice
    - lex bot version alias
    - lexv2-models
    - lexv2-runtime
    - lex channel integration
  when_to_use: >-
    Invoke when the user wants to create an Amazon Lex V2 conversational
    bot, configure intents and slots with elicitation prompts, wire a
    Lambda dialog/fulfillment code hook, enable voice (Amazon Polly) or
    sentiment analysis, publish a bot version and alias for blue-green
    rollout, enable conversation logs with KMS encryption, or integrate
    a third-party messaging channel (Twilio, Genesys, Slack). Do NOT
    invoke for Amazon Lex V1 (the legacy build-bot API), Amazon Connect
    flows (use connect skills), or Amazon Alexa skills (different
    runtime).
---

# Lex Bot Deployer

An AWS CloudOps agent skill that provisions Amazon Lex V2 conversational
bots with correct defaults. The skill walks the operator through bot
creation, locale setup, intent and slot modeling, prompt configuration,
Lambda code-hook wiring, voice/sentiment options, versioning and alias
for blue-green deployment, KMS-encrypted conversation logs, and channel
integration. It captures decisions, explains why each default matters,
and emits a READY_TO_DEPLOY checklist with verification commands.

## Activation keywords

create Lex bot, Lex V2 intent, Lex slot type, Lex Lambda code hook, Lex
conversation logs, Lex Polly voice, Lex bot version alias, lexv2-models,
lexv2-runtime, Lex channel integration.

## STRICT output contract

When this skill is invoked with a Lex V2 provisioning request (create a
bot, configure intents, slots, prompts, code hook, voice, version,
alias, logs, or channel integration), the agent MUST respond with the
READY_TO_DEPLOY checklist defined in the "Output format" section using
the literal all-caps labels `LEX_BOT:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels breaks
automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Bot, locale, and voice | Core bot shell |
| Step 2 — Intents, utterances, slots | Conversation modeling |
| Step 3 — Slot types (built-in vs custom) | Slot resolution |
| Step 4 — Prompt configuration | UX prompts |
| Step 5 — Lambda code hook | Dialog management |
| Step 6 — Fulfillment (Lambda or ReturnIntent) | Intent completion |
| Step 7 — Conversation logs and KMS | Observability + encryption |
| Step 8 — Sentiment analysis | Comprehend integration |
| Step 9 — Voice and Amazon Polly | Voice bots |
| Step 10 — Bot versioning and alias | Blue-green rollout |
| Step 11 — lexv2-models vs lexv2-runtime | API separation |
| Step 12 — Channel integration | Omnichannel |
| Step 13 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/intents-and-slots.md | Intent + slot detail |
| references/code-hooks-and-aliases.md | Code hook + alias detail |

## Mindset

**One-line takeaway:** A Lex V2 bot is a state machine of intents. Each
intent declares sample utterances, slots (typed parameters), and
prompts. A Lambda code hook (when enabled) intercepts between EVERY
turn — validating slots, branching dialog, and Fulfillment — and an
alias points to a specific bot version, enabling blue-green deployment.

Three misconceptions dominate Lex V2 misdesign at provisioning time:

- **"Slots elicit in declaration order."** They elicit in PRIORITY order
  (priority 1 first), and only REQUIRED slots are auto-elicited. A
  baseline model declares slots and assumes code order. The correct model
  assigns explicit priorities, puts required slots first, and leaves
  optional slots to be elicited only when the code hook demands them.

- **"The Lambda code hook runs once at the end."** It does NOT. The
  DIALOG_CODE_HOOK fires after EVERY user turn — between slot elicitation,
  confirmation, and fulfillment. It is the dialog manager. A baseline
  wires `FULFILLMENT_CODE_HOOK` only and is surprised when the bot cannot
  branch mid-conversation. Opt in to both hooks per intent.

- **"Publishing a bot is enough to make it live."** It is NOT. create-bot
  yields DRAFT. You MUST call create-bot-version to snapshot DRAFT into a
  numbered version, then create-resource-link (alias) pointing at it. The
  runtime uses the alias, not the version directly — this enables
  blue-green: shift the alias from version N to N+1 with rollback being
  a single API call.

## Configuration dependency graph (novel heuristic)

Lex V2 configurations are NOT independent. Intents need slots; slots
need slot types; code hooks need a Lambda ARN with a resource-based
permission granting Lex service invocation; aliases need versions;
versions need built intents; channels need an alias. Use this graph to
sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Bot (create-bot) | unique bot name; COPPA flag; IAM permissions | dataPrivacy is IMMUTABLE after creation — set ChildDirected correctly the first time | bot shell that holds locales |
| Locale (create-bot-locale) | bot exists; localeId (e.g., en-US); voiceId if voice | NLU trains asynchronously; bot is not conversational until locale status is Built | intent/slot modeling |
| Slot type (create-slot-type) | bot exists; locale exists | slot type values must be unique within the slot type | slots referencing the type |
| Slot (create-slot) | intent exists; slot type exists (built-in or custom) | priority MUST be 1..100; required slots are elicited in priority order | elicitation flow |
| Intent (create-intent) | bot + locale exist; sampleUtterances non-empty | intent is not active until locale is rebuilt | conversation state |
| Code hook (Lambda) | Lambda function deployed in same region; resource-based permission granting `lexv2.amazonaws.com` | DIALOG_CODE_HOOK and FULFILLMENT_CODE_HOOK are SEPARATE flags per intent — opting into one does NOT opt into the other | dialog management + fulfillment |
| Conversation logs | bot exists; CloudWatch Logs role ARN; KMS key policy grants Lex | audio and text logs are independent toggles; without KMS the logs role is the only encryption | observability |
| Bot version (create-bot-version) | locale status is Built; DRAFT has changes | version is a SNAPSHOT — immutable once created | reproducible bot state |
| Alias (create-resource-link) | bot version exists | alias points at exactly one version; shifting it is the blue-green switch | runtime endpoint |
| Channel integration | alias exists (channels bind to alias); channel-specific credentials | a channel always points at an alias — never at DRAFT | omnichannel publishing |

**The slot-priority and alias rows are the ones a baseline model misses.**
Slot priority controls elicitation order, but a baseline treats slots
as unordered. Alias is the runtime's source of truth, but a baseline
publishes a version and assumes it is live. The procedure below forces
explicit decisions on each.

**Cross-dependency gotchas:**
- A locale must be `Built` before you can create a bot version. Changes
  land in DRAFT — `build-bot-locale` again, then stamp a new version.
- The Lambda resource-based policy MUST grant `lambda:InvokeFunction` to
  `lexv2.amazonaws.com` scoped to the bot's ARN, or the code hook
  silently fails at runtime (no error at config time).
- KMS key policy must allow the Lex service-linked role
  `kms:GenerateDataKey` and `kms:Decrypt`, or log delivery fails silently.
- Aliases are immutable pointers but you CAN call update-resource-link
  to shift the version — the blue-green switch AND the rollback switch.
- Multiple locales share one bot but each has its own intents. A bot
  version snapshots ALL built locales simultaneously.

## Expert heuristic: slot elicitation priority

A baseline model declares slots and assumes elicitation in code order.
The correct heuristic recognizes Lex elicits REQUIRED slots in PRIORITY
order (1 = highest), only when the slot is not already filled.

```text
Intent: OrderCoffee
  Slots (declared with priority):
    CoffeeSize    (priority 1, required, slot type CoffeeSizeType)
    CoffeeDrink   (priority 2, required, slot type CoffeeDrinkType)
    CoffeeTemp    (priority 3, optional, slot type AMBIENT)

User: "I'd like a large latte"
  → Lex fills CoffeeSize=large, CoffeeDrink=latte from the utterance
  → CoffeeTemp is OPTIONAL — Lex does NOT auto-elicit
  → Lambda DIALOG_CODE_HOOK can choose to elicit CoffeeTemp or skip

User: "I'd like a coffee"
  → Lex elicits CoffeeSize first (priority 1, required, not filled)
  → Then CoffeeDrink (priority 2)
  → CoffeeTemp skipped unless code hook intervenes
```

**Key implication:** the priority field is the ONLY way to control
auto-elicitation order. Required slots with the same priority are
elicited in undefined order — assign distinct priorities. Optional
slots MUST be elicited by the Lambda code hook; the bot will not ask
for them on its own.

## Expert heuristic: Lambda code hook fires between every turn

The DIALOG_CODE_HOOK is the dialog manager. It fires after every user
turn — between slot elicitation, between confirmation, before
fulfillment. A baseline model wires only FULFILLMENT_CODE_HOOK and
loses the ability to validate, branch, or skip slots.

```text
Turn 1: User says "book a flight" → Lex matches BookFlight intent
  → DIALOG_CODE_HOOK fires (invocationSource = "DialogCodeHook")
     → Lambda validates, enriches, sets next slot
  → Lex elicits DepartureCity (priority 1)

Turn 2: User says "San Francisco"
  → DIALOG_CODE_HOOK fires → Lambda validates city, sets slot
  → Lex elicits DestinationCity (priority 2)

Final turn: All required slots filled → Lex prompts confirmation
  → DIALOG_CODE_HOOK fires (user confirmed)
  → FULFILLMENT_CODE_HOOK fires (invocationSource = "FulfillmentCodeHook")
     → Lambda performs the action (call API, write DB)
     → Returns Close action with success message
```

**Key implication:** treat DIALOG_CODE_HOOK as the validation/branching
layer and FULFILLMENT_CODE_HOOK as the action layer. Separate them in
your Lambda by branching on `invocationSource`.

## Expert heuristic: alias enables blue-green bot deployment

A Lex V2 alias (resource link) points to exactly one bot version.
Shifting the alias is the blue-green switch.

```text
Bot: OrderBot
  Version 1 (snapshot of DRAFT at 2026-08-01)
  Version 2 (snapshot of DRAFT at 2026-08-05)

Alias "prod" → Version 1 (live traffic)
Alias "staging" → Version 2 (QA traffic)

Blue-green rollout:
  1. Test against staging alias (Version 2)
  2. update-resource-link → prod alias points to Version 2
  3. If issue: update-resource-link → prod back to Version 1 (single call)

Channel integrations and runtime clients reference the ALIAS, not the
version. Shifting the alias atomically shifts all clients.
```

**Key implication:** NEVER point clients at a specific version. Always
use an alias. This makes rollback trivial and decouples release from
deployment.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Bot name is unique in the account/region | create-bot fails on collision | `aws lexv2-models list-bots --query 'botsSummaries[?botName==\`<name>\`]'` |
| `dataPrivacy` (ChildDirected) decision | IMMUTABLE after creation — set correctly the first time | Confirm with the operator |
| Locale ID confirmed (e.g., en-US) | Locale determines NLU model and voice | Confirm with the operator |
| Intent names follow Lex V2 naming rules | Names must match `[A-Za-z_][A-Za-z0-9_]*` and be unique within the bot | Validate against regex |
| Slot types resolved (built-in or custom) | Each slot must reference a slot type | Confirm built-in (AMAZON.*) or define custom values |
| Lambda function deployed (if code hook) | Code hook requires an existing Lambda ARN | `aws lambda get-function --function-name <name>` |
| Lambda resource-based policy grants Lex | Without it, Lex cannot invoke the code hook at runtime | `aws lambda get-policy --function-name <name>` |
| IAM permissions for lexv2-models | Required to create bot, locale, intent, slot, version, alias | `aws iam list-attached-user-policies` |
| KMS key ID (if encryption at rest) | Custom encryption requires a CMK with Lex service-linked role access | `aws kms describe-key --key-id <id>` |
| CloudWatch Logs role ARN (if conversation logs) | Lex assumes this role to deliver logs | Confirm role trust policy includes `lexv2.amazonaws.com` |
| Channel credentials (if integration) | Each channel requires provider-specific tokens | Confirm Twilio SID, Slack token, Genesys config |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Bot, locale, and voice

A Lex V2 bot is the top-level container. Each bot has one or more
locales; each locale carries its own intents and slots.

```bash
BOT_ID=$(aws lexv2-models create-bot \
  --bot-name "OrderCoffeeBot" \
  --description "Coffee ordering conversational bot" \
  --data-privacy childDirected=false \
  --idle-session-ttl-in-seconds 300 \
  --role-arn arn:aws:iam::123456789012:role/lex-v2-bot-role \
  --query 'botId' --output text)

aws lexv2-models create-bot-locale \
  --bot-id "$BOT_ID" --locale-id en-US \
  --n-lu-intent-confidence-threshold 0.40 \
  --voice-id "Ivy" --engine-type standard
```

**Critical:** `dataPrivacy.childDirected` is IMMUTABLE. Set it correctly
the first time. The locale must reach `Built` status before the bot can
be versioned. voice_id only matters for voice bots (Polly integration)
and is per-locale.

## Step 2 — Intents, utterances, slots

Intents are the states the bot can match. Each intent has sample
utterances, slots, and prompts.

```bash
INTENT_ID=$(aws lexv2-models create-intent \
  --bot-id "$BOT_ID" --bot-version DRAFT --locale-id en-US \
  --intent-name "OrderCoffee" \
  --sample-utterances \
    '[{"utterance":"I want a {CoffeeSize} {CoffeeDrink}"},{"utterance":"Can I get a coffee"}]' \
  --query 'intentId' --output text)
```

**Slot elicitation order is controlled by `priority`, NOT declaration
order.** Assign priorities explicitly. Lower number = higher priority.
Required slots with priority 1 are elicited first.

## Step 3 — Slot types (built-in vs custom)

Lex V2 ships built-in slot types prefixed `AMAZON.` (e.g.,
`AMAZON.Date`, `AMAZON.Number`, `AMAZON.City`). Custom slot types are
enumerations or regex patterns you define.

**Built-in slot type** (no slot-type resource needed):

```bash
aws lexv2-models create-slot \
  --bot-id "$BOT_ID" --bot-version DRAFT --locale-id en-US \
  --intent-id "$INTENT_ID" --slot-name "OrderQuantity" \
  --slot-type-id "AMAZON.Number" --priority 1 \
  --value-elicitation-setting \
    '{"slotConstraint":"Required","promptSpecification":{"messageGroups":[{"message":{"plainTextMessage":{"value":"How many coffees would you like?"}}}],"maxRetries":3}}'
```

**Custom slot type** (enumeration):

```bash
SLOT_TYPE_ID=$(aws lexv2-models create-slot-type \
  --bot-id "$BOT_ID" --bot-version DRAFT --locale-id en-US \
  --slot-type-name "CoffeeDrinkType" \
  --slot-type-values \
    '[{"sampleValue":{"value":"latte"}},{"sampleValue":{"value":"cappuccino"}},{"sampleValue":{"value":"americano"}}]' \
  --value-selection-setting '{"resolutionStrategy":"TopResolution"}' \
  --query 'slotTypeId' --output text)
```

**When to use built-in vs custom:**
- Built-in (`AMAZON.*`) for dates, numbers, cities, currencies — Lex's
  pretrained NLU resolves them well.
- Custom for domain-specific enumerations (drink types, product names,
  categories). Avoid reinventing built-ins.

## Step 4 — Prompt configuration

Lex V2 supports four prompt categories per intent:

| Prompt | When it fires | Required |
|---|---|---|
| Elicitation (`promptSpecification`) | When the bot needs a slot value | Per required slot |
| Confirmation (`confirmationSetting`) | Before fulfillment — "Should I place your order?" | Recommended for side-effectful intents |
| Closing (`closingSetting`) | After fulfillment — "Your order is confirmed." | Optional |
| Failure (`failureHandling`) | When confirmation denied or max retries exceeded | Recommended |

**maxRetries on elicitation** is the number of times the bot re-prompts
before giving up (typically 3). After maxRetries, Lex raises the
failure-handling branch or ends the conversation.

## Step 5 — Lambda code hook (dialog + fulfillment)

A Lambda code hook is the dialog manager. It intercepts between every
turn. There are TWO independent hooks per intent:

| Hook | invocationSource | Purpose |
|---|---|---|
| DialogCodeHook | `DialogCodeHook` | Validation, branching, slot enrichment, dynamic prompts |
| FulfillmentCodeHook | `FulfillmentCodeHook` | Final action — call API, write DB, then Close |

**Wire the code hook on an intent:**

```bash
aws lexv2-models update-intent \
  --bot-id "$BOT_ID" --bot-version DRAFT --locale-id en-US \
  --intent-id "$INTENT_ID" --intent-name OrderCoffee \
  --sample-utterances '[{"utterance":"I want a {CoffeeSize} {CoffeeDrink}"}]' \
  --dialog-code-hook '{"enabled":true}' \
  --fulfillment-code-hook '{"enabled":true}'
```

**Grant Lex permission to invoke the Lambda:**

```bash
aws lambda add-permission \
  --function-name OrderCoffeeFulfillment \
  --statement-id LexInvokePermission \
  --action lambda:InvokeFunction \
  --principal lexv2.amazonaws.com \
  --source-arn "arn:aws:lex:us-east-1:123456789012:bot/$BOT_ID"
```

**Common mistake:** wiring FULFILLMENT_CODE_HOOK only and being surprised
the bot cannot validate or branch mid-conversation. Enable both hooks
unless you have a specific reason to disable DialogCodeHook.

## Step 6 — Fulfillment (Lambda or ReturnIntent)

| Mode | Behavior |
|---|---|
| `FulfillmentCodeHook` (Lambda) | Lex invokes Lambda which performs the action and returns `Close` |
| `ReturnIntent` (no Lambda) | Lex returns intent + slot values to the client application |

Use Lambda Fulfillment for server-side actions (DB, API, email). Use
ReturnIntent when the client owns the action (mobile navigation, web
UI). ReturnIntent is the default if no code hook is wired and CANNOT
perform server-side actions.

## Step 7 — Conversation logs and KMS

Lex V2 conversation logs capture text and audio of every conversation.
Logs deliver to CloudWatch Logs and (optionally) S3. A Lex-owned service
role assumes permissions.

**Enable conversation logs** (text-only example):

```bash
aws lexv2-models put-bot-locale \
  --bot-id "$BOT_ID" --locale-id en-US \
  --conversation-log-settings \
    '{"textLogSettings":{"enabled":true,"destination":"CloudWatchLogs","cloudWatchLogsLogGroupArn":"arn:aws:logs:us-east-1:123456789012:log-group:/aws/lex/OrderCoffeeBot"}}'
```

**KMS key policy must grant the Lex service-linked role:**

```json
{
  "Sid": "AllowLexToUseKey",
  "Effect": "Allow",
  "Principal": {"Service": "lexv2.amazonaws.com"},
  "Action": ["kms:GenerateDataKey", "kms:Decrypt"],
  "Resource": "*"
}
```

**Critical:** the Lex service role needs `logs:CreateLogStream`,
`logs:PutLogEvents` on the log group ARN, or delivery fails silently.

## Step 8 — Sentiment analysis

Lex V2 integrates with Amazon Comprehend to attach sentiment (POSITIVE,
NEGATIVE, NEUTRAL, MIXED) and sentiment score to each user turn. Sentiment
is returned in `sessionState.sentimentResponse` on the runtime response.
It is NOT used by Lex's NLU directly — your Lambda code hook or client
reads it and branches.

**Cost note:** Comprehend sentiment is billed per call. For high-volume
bots, sample sentiment rather than enabling it on every turn.

## Step 9 — Voice and Amazon Polly

Voice bots use Amazon Polly text-to-speech. Configure `voiceId` and
`engine-type` per locale.

```bash
aws lexv2-models update-bot-locale \
  --bot-id "$BOT_ID" --locale-id en-US \
  --voice-id "Joanna" --engine-type neural
```

**Voice ID selection:** Joanna and Matthew (US English, neural), Amy (UK
English), Nicole (Australian). Use `neural` for natural quality;
`standard` for lower cost. Phone integration requires Amazon Connect or
a PSTN provider (Twilio, Genesys) — Lex itself does not provision phone
numbers.

## Step 10 — Bot versioning and alias (blue-green)

Bot versions are snapshots of DRAFT. Aliases (resource links) point at
versions. Runtime clients reference aliases, not versions.

```bash
# Build the locale first (REQUIRED before versioning)
aws lexv2-models build-bot-locale --bot-id "$BOT_ID" --locale-id en-US
# Wait until status is Built

BOT_VERSION=$(aws lexv2-models create-bot-version \
  --bot-id "$BOT_ID" --description "Production release 2026-08-11" \
  --query 'botVersion' --output text)

ALIAS_ID=$(aws lexv2-models create-resource-link \
  --bot-id "$BOT_ID" --alias-name "prod" \
  --bot-version "$BOT_VERSION" --query 'resourceLinkId' --output text)
```

**Blue-green switch:**

```bash
aws lexv2-models update-resource-link \
  --bot-id "$BOT_ID" --alias-id "$ALIAS_ID" --bot-version "$NEW_VERSION"
```

**Rollback** — point the alias back to the previous version (single API
call). The runtime client (`recognize-text`, `recognize-utterance`)
ALWAYS specifies `botAliasId`. NEVER specify `botVersion` in runtime
calls.

## Step 11 — lexv2-models vs lexv2-runtime

| Service | Used for | Notable calls |
|---|---|---|
| `lexv2-models` | Build-time configuration | `create-bot`, `create-intent`, `create-slot`, `build-bot-locale`, `create-bot-version`, `create-resource-link` |
| `lexv2-runtime` | Runtime conversations | `recognize-text`, `recognize-utterance`, `start-conversation`, `put-session`, `delete-session` |

```bash
# Send text to the bot (runtime)
aws lexv2-runtime recognize-text \
  --bot-id "$BOT_ID" --bot-alias-id "$ALIAS_ID" \
  --locale-id en-US --session-id "user-1234" \
  --text "I'd like a large latte"
```

**Common mistake:** trying to call runtime APIs against the DRAFT
version. Runtime only works against an alias. Build, version, alias,
then converse.

## Step 12 — Channel integration (Twilio, Genesys, Slack)

Lex V2 supports integration with third-party messaging channels. Each
channel binds to an ALIAS, not a version.

| Channel | Integration | Credentials |
|---|---|---|
| Twilio (SMS, WhatsApp) | Twilio webhook invokes Lex runtime | Twilio Account SID + Auth Token |
| Genesys Cloud | Genesys Architect action calls Lex | Genesys token |
| Slack | Slack slash command → Lambda proxy → Lex | Slack Bot Token + Signing Secret |
| Facebook Messenger | Page subscription via webhook | Page Access Token |
| Web/Mobile (custom) | App calls recognize-text directly | None (AWS auth) |

**Slack pattern:** Slack Events API → API Gateway → Lambda proxy → Lex
recognize-text → response → Lambda proxy → Slack chat.postMessage.

**Critical:** channel credentials are stored in AWS Secrets Manager or
SSM Parameter Store — NEVER inline in the Lambda code.

## Step 13 — Recent features

- **Lex V2 Generative AI integration (2023-2024):** Built-in Amazon
  Bedrock fallback when NLU confidence is below threshold. Configure
  `generativeAIFallback` on the locale.
- **Amazon Q integration (2024-2025):** Amazon Q Business connectors
  wire as fulfillment backend for FAQ-style intents, eliminating custom
  Kendra indexes in common cases.
- **Improved built-in slot types (2024):** New `AMAZON.TypeOfFood`,
  `AMAZON.TypeOfSport`, `AMAZON.MusicRecording` reduce custom work.
- **Audio conversation logs to S3 (2024-2025):** S3 destinations in
  addition to CloudWatch Logs with KMS encryption on both.
- **Polly neural voice styles (2024-2025):** Style modulation (newscast,
  conversation, customer support) via `engine-type=neural` and
  `voice-style`.
- **Test workspace API (2023-2024):** Run conversation scripts against
  a bot version before alias promotion, formalizing blue-green QA.
- **Genesys Cloud CX connector (2024):** Official Genesys Cloud CX
  connector for Lex V2 simplifies call-center integrations.

## NEVER do these things

1. **NEVER assume slots elicit in declaration order.** Slots elicit in
   PRIORITY order (1 = highest). Required slots are auto-elicited;
   optional slots are NOT — they require a Lambda code hook.

2. **NEVER wire only FULFILLMENT_CODE_HOOK.** The DIALOG_CODE_HOOK fires
   after every turn and is the dialog manager. Without it, the bot
   cannot validate, branch, or enrich slots mid-conversation.

3. **NEVER point runtime clients at a bot version.** Always use an
   alias — aliases enable blue-green deployment and atomic rollback.

4. **NEVER forget the Lambda resource-based permission.** The Lambda
   must grant `lambda:InvokeFunction` to `lexv2.amazonaws.com` scoped
   to the bot's ARN, or the code hook silently fails.

5. **NEVER skip build-bot-locale before creating a version.** Versions
   snapshot the BUILT state; DRAFT-only locales are not versionable.

6. **NEVER set dataPrivacy.childDirected incorrectly.** It is IMMUTABLE
   after creation. Confirm COPPA classification before running create-bot.

7. **NEVER enable audio conversation logs without a KMS key.** Audio
   logs may contain PII. Use a CMK with a key policy granting the Lex
   service-linked role.

8. **NEVER use cross-region Lambda code hooks.** Lex invokes Lambda
   synchronously (user is waiting). Cross-region invocation adds latency
   and may hit the 30s timeout. Same region as the bot.

9. **NEVER assume sentiment analysis is free.** Comprehend is billed
   per call. Sample sentiment rather than enabling on every turn.

10. **NEVER inline channel credentials in Lambda code.** Store Twilio
    SIDs, Slack tokens, Genesys configs in Secrets Manager or SSM.

## Output format

```text
LEX_BOT: <bot-name> (<bot-id>) | locale: <locale-id> | alias: <alias-name> → <bot-version>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Bot: <bot-name> (<bot-id>), dataPrivacy childDirected=<true|false>
  [✓|✗] Locale: <locale-id> — Built (NLU threshold <value>, voice_id <voice>)
  [✓|✗] Intents: <intent-name-list>
  [✓|✗] Slots (priority order): <slot-name>:<slot-type>:<required|optional> (priority <n>)
  [✓|✗] Prompts: elicitation per required slot, confirmation, closing, failure
  [✓|✗] Code hook: DIALOG_CODE_HOOK=<enabled|disabled>, FULFILLMENT_CODE_HOOK=<enabled|disabled>, Lambda=<arn>
  [✓|✗] Lambda resource-based permission: lexv2.amazonaws.com granted on <arn>
  [✓|✗] Fulfillment mode: Lambda | ReturnIntent
  [✓|✗] Conversation logs: text=<on|off>, audio=<on|off>, destination=<CW Logs|S3>
  [✓|✗] KMS encryption: <key-id> | AWS-managed
  [✓|✗] Sentiment analysis: enabled | disabled
  [✓|✗] Voice: Polly voice_id=<voice>, engine=<standard|neural>
  [✓|✗] Bot version: <n> (status <Built>)
  [✓|✗] Alias: <alias-name> → version <n>
  [✓|✗] Channel integration: <channel-list with credentials source>
VERIFICATION_COMMANDS:
  aws lexv2-models describe-bot --bot-id <bot-id>
  aws lexv2-models describe-bot-locale --bot-id <bot-id> --locale-id <locale-id>
  aws lexv2-models describe-bot-version --bot-id <bot-id> --bot-version <n>
  aws lexv2-models describe-resource-link --bot-id <bot-id> --resource-link-id <alias-id>
  aws lexv2-runtime recognize-text --bot-id <bot-id> --bot-alias-id <alias-id> --locale-id <locale-id> --session-id test --text "test"
```

### Worked example — coffee ordering bot with Lambda code hook

```text
LEX_BOT: OrderCoffeeBot (bot-abc123) | locale: en-US | alias: prod → 1
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Bot: OrderCoffeeBot (bot-abc123), dataPrivacy childDirected=false
  [✓] Locale: en-US — Built (NLU threshold 0.40, voice_id Joanna)
  [✓] Intents: OrderCoffee, Greeting, Fallback
  [✓] Slots (priority order): CoffeeSize:CoffeeSizeType:required (priority 1), CoffeeDrink:CoffeeDrinkType:required (priority 2), CoffeeTemp:AMBIENT:optional (priority 3)
  [✓] Prompts: elicitation per required slot, confirmation, closing, failure
  [✓] Code hook: DIALOG_CODE_HOOK=enabled, FULFILLMENT_CODE_HOOK=enabled, Lambda=arn:aws:lambda:us-east-1:123456789012:function:OrderCoffeeFulfillment
  [✓] Lambda resource-based permission: lexv2.amazonaws.com granted on OrderCoffeeFulfillment
  [✓] Fulfillment mode: Lambda
  [✓] Conversation logs: text=on, audio=off, destination=CloudWatch Logs /aws/lex/OrderCoffeeBot
  [✓] KMS encryption: arn:aws:kms:us-east-1:123456789012:key/abc-def (CMK)
  [✓] Sentiment analysis: enabled (Comprehend)
  [✓] Voice: Polly voice_id=Joanna, engine=neural
  [✓] Bot version: 1 (status Built)
  [✓] Alias: prod → version 1
  [✓] Channel integration: Twilio (SMS via webhook, credentials in Secrets Manager: twilio/ordercoffee)
VERIFICATION_COMMANDS:
  aws lexv2-models describe-bot --bot-id bot-abc123
  aws lexv2-models describe-bot-locale --bot-id bot-abc123 --locale-id en-US
  aws lexv2-models describe-bot-version --bot-id bot-abc123 --bot-version 1
  aws lexv2-models describe-resource-link --bot-id bot-abc123 --resource-link-id alias-prod
  aws lexv2-runtime recognize-text --bot-id bot-abc123 --bot-alias-id alias-prod --locale-id en-US --session-id test-001 --text "I'd like a large latte"
```

## Error handling

### Locale stuck in Building
- A prior build failed. Check `describe-bot-locale` for errors. Common
  causes: malformed utterances referencing undefined slots, slot types
  with no values, duplicate intent names.

### Code hook never fires
- The Lambda resource-based permission is missing or scoped to the wrong
  bot ARN. Verify with `aws lambda get-policy`. Re-run `add-permission`
  with the correct `--source-arn`.

### Runtime returns "Invalid bot alias"
- The alias does not exist or points at a non-Built version. Build the
  locale, create a version, then create or update the alias.

### Conversation logs not delivered
- The Lex service role lacks CloudWatch Logs permissions or the KMS key
  policy does not grant `lexv2.amazonaws.com`. Create the log group first.

### Slot elicitation order is wrong
- Slot priorities are not set or are duplicated. Re-run `update-slot`
  with distinct priorities (1, 2, 3...).

### Voice bot audio quality is poor
- The engine is `standard`. Switch to `neural` for Polly neural voices.
  Verify the phone provider is not transcoding to low-bitrate.

## Domain

AWS CloudOps / Amazon Lex V2 Conversational Bot Provisioning &
Conversational AI Deployment.

## AWS documentation

- **Lex V2 Developer Guide** — https://docs.aws.amazon.com/lexv2/latest/dg/what-is.html
- **create-bot / create-intent / create-slot / create-slot-type** — https://docs.aws.amazon.com/lexv2/latest/APIReference/API_CreateBot.html
- **Lambda code hooks** — https://docs.aws.amazon.com/lexv2/latest/dg/lambda.html
- **Bot versions and aliases** — https://docs.aws.amazon.com/lexv2/latest/dg/versions.html
- **Conversation logs** — https://docs.aws.amazon.com/lexv2/latest/dg/conversation-logs.html
- **Built-in slot types** — https://docs.aws.amazon.com/lexv2/latest/dg/howitworks-slots.html
- **Polly voice IDs** — https://docs.aws.amazon.com/polly/latest/dg/voicelist.html
- **Channel integration** — https://docs.aws.amazon.com/lexv2/latest/dg/deploying.html
- **Sentiment analysis** — https://docs.aws.amazon.com/lexv2/latest/dg/sentiment-analysis.html
