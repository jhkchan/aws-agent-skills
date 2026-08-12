---
description: Provision an Amazon Lex V2 conversational bot with production-grade defaults (bot creation, locale setup, intents with slot priorities, custom and built-in slot types, elicitation/confirmation/closing prompts, Lambda dialog and fulfillment code hooks, conversation logs with KMS, voice via Amazon Polly, sentiment analysis, bot version and alias for blue-green deployment, channel integration). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create lex bot"
  - "deploy lex bot"
  - "lex v2 bot"
  - "lex intent"
  - "lex slot type"
  - "lex code hook"
  - "lex lambda"
  - "lex conversation logs"
  - "lex polly voice"
  - "lex bot version"
  - "lex bot alias"
  - "lexv2-models"
  - "lexv2-runtime"
  - "lex channel integration"
  - "lex twilio"
  - "lex slack"
  - "conversational bot"
routes_to: lex-bot-deployer
---

# /aws:deploy-lex-bot

Activate the `lex-bot-deployer` skill and provision an Amazon Lex V2
conversational bot with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Bot, locale, and voice (create-bot, create-bot-locale)
2. Intents, utterances, and slots (create-intent, create-slot)
3. Slot types — built-in vs custom (create-slot-type)
4. Prompt configuration (elicitation, confirmation, closing, failure)
5. Lambda code hook — dialog + fulfillment (DIALOG_CODE_HOOK, FULFILLMENT_CODE_HOOK)
6. Fulfillment mode (Lambda or ReturnIntent)
7. Conversation logs and KMS encryption
8. Sentiment analysis (Amazon Comprehend)
9. Voice and Amazon Polly integration
10. Bot versioning and alias (blue-green deployment)
11. lexv2-models vs lexv2-runtime API separation
12. Channel integration (Twilio, Genesys, Slack)

## When to use

- You need to create a Lex V2 conversational bot.
- You are configuring intents with slots and elicitation prompts.
- You need to wire a Lambda dialog or fulfillment code hook.
- You want voice (Amazon Polly) or sentiment analysis.
- You need bot versioning and alias for blue-green deployment.
- You need conversation logs with KMS encryption.
- You are integrating a messaging channel (Twilio, Slack, Genesys).

## When NOT to use

- **Amazon Lex V1** — the legacy `build-bot` API is different. Use V1-
  specific tooling.
- **Amazon Connect flows** — use connect-instance-deployer for contact
  flow design (even though Connect can invoke Lex V2 bots).
- **Amazon Alexa skills** — different runtime and skill model.
- **Bedrock conversational AI** — use bedrock skills for foundation model
  chat without intent modeling.

## How to invoke

### Slash command

```
/aws:deploy-lex-bot
```

Then provide: bot name, locale ID, intent list, slot definitions with
priorities, slot types, Lambda function name, prompt text, voice_id,
sentiment decision, log destination, KMS key ID, version/alias names,
and channel integration details.

### Natural language

Any of these routes to the same skill:

- "create a Lex V2 bot named OrderCoffeeBot"
- "configure intents and slots for my Lex bot"
- "wire a Lambda code hook to my Lex bot"
- "enable Polly voice on my Lex bot"
- "publish a bot version and alias for blue-green"
- "enable conversation logs with KMS encryption"
- "integrate Twilio SMS with my Lex bot"

### CLI routing

```bash
node cli/bin/cli.js route "create a lex v2 bot"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create Lex V2
conversational bots. The output checklist feeds into verification
pipelines and downstream audit skills.

## Example

```
You: /aws:deploy-lex-bot

     Create a Lex V2 bot named OrderCoffeeBot in us-east-1.
     Locale en-US. Three intents: OrderCoffee, Greeting, Fallback.
     Wire both dialog and fulfillment code hooks to
     OrderCoffeeFulfillment Lambda. Build, version 1, alias prod.

Skill:
  LEX_BOT: OrderCoffeeBot (bot-abc123) | locale: en-US | alias: prod → 1
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Bot: OrderCoffeeBot (bot-abc123)
    [✓] Locale: en-US — Built
    [✓] Code hook: DIALOG_CODE_HOOK=enabled, FULFILLMENT_CODE_HOOK=enabled
    [✓] Lambda permission: lexv2.amazonaws.com granted
    [✓] Bot version: 1, Alias: prod → 1
  VERIFICATION_COMMANDS:
    aws lexv2-models describe-bot --bot-id bot-abc123
    aws lexv2-runtime recognize-text --bot-id bot-abc123 --bot-alias-id alias-prod --locale-id en-US --session-id test --text "test"
```

## References

- Skill definition: `skills/lex-bot-deployer/SKILL.md`
- Intents and slots guide: `skills/lex-bot-deployer/references/intents-and-slots.md`
- Code hooks and aliases guide: `skills/lex-bot-deployer/references/code-hooks-and-aliases.md`
- Eval suite: `skills/lex-bot-deployer/evals/evals.json`
