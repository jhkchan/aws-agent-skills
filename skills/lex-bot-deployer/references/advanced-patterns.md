# Advanced patterns — lex-bot-deployer

Mindset misconceptions, the configuration dependency graph, and recent AWS features, moved verbatim from SKILL.md for progressive disclosure. Load on demand.

## Mindset — one-line takeaway and three misconceptions (moved from SKILL.md)

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

## Configuration dependency graph (moved from SKILL.md)

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

## Step 13 — Recent features (moved from SKILL.md)

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
