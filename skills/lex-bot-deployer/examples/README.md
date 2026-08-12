# End-to-End Example: Lex V2 Bot Deployment

A walkthrough showing how to use the `lex-bot-deployer` skill
from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a Lex V2 coffee-ordering conversational bot with
custom slot types, explicit slot priorities, a Lambda dialog and
fulfillment code hook, conversation logs with KMS encryption, and
blue-green alias deployment. The bot needs:

- Bot name: OrderCoffeeBot
- Locale: en-US (NLU threshold 0.40)
- Intents: OrderCoffee, Greeting, Fallback
- Slots: CoffeeSize (priority 1, required), CoffeeDrink (priority 2,
  required), CoffeeTemp (priority 3, optional)
- Code hooks: DIALOG_CODE_HOOK + FULFILLMENT_CODE_HOOK
- Lambda: OrderCoffeeFulfillment
- Conversation logs: text to CloudWatch Logs
- KMS CMK for encryption
- Bot version 1, alias prod

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-lex-bot
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a Lex V2 bot named OrderCoffeeBot in us-east-1.
      Locale en-US. Three intents. Wire both dialog and
      fulfillment code hooks to OrderCoffeeFulfillment Lambda.
      Build, version 1, alias prod."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a lex v2 bot"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

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

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the bot
BOT_ID=$(aws lexv2-models create-bot \
  --bot-name "OrderCoffeeBot" \
  --data-privacy childDirected=false \
  --idle-session-ttl-in-seconds 300 \
  --role-arn arn:aws:iam::123456789012:role/lex-v2-bot-role \
  --query 'botId' --output text)

# Step 2: Create the locale
aws lexv2-models create-bot-locale \
  --bot-id "$BOT_ID" --locale-id en-US \
  --n-lu-intent-confidence-threshold 0.40

# Step 3: Create custom slot types
DRINK_TYPE_ID=$(aws lexv2-models create-slot-type \
  --bot-id "$BOT_ID" --bot-version DRAFT --locale-id en-US \
  --slot-type-name "CoffeeDrinkType" \
  --slot-type-values \
    '[{"sampleValue":{"value":"latte"}},{"sampleValue":{"value":"cappuccino"}},{"sampleValue":{"value":"americano"}}]' \
  --value-selection-setting '{"resolutionStrategy":"TopResolution"}' \
  --query 'slotTypeId' --output text)

SIZE_TYPE_ID=$(aws lexv2-models create-slot-type \
  --bot-id "$BOT_ID" --bot-version DRAFT --locale-id en-US \
  --slot-type-name "CoffeeSizeType" \
  --slot-type-values \
    '[{"sampleValue":{"value":"small"}},{"sampleValue":{"value":"medium"}},{"sampleValue":{"value":"large"}}]' \
  --value-selection-setting '{"resolutionStrategy":"TopResolution"}' \
  --query 'slotTypeId' --output text)

# Step 4: Create the intent with both code hooks
INTENT_ID=$(aws lexv2-models create-intent \
  --bot-id "$BOT_ID" --bot-version DRAFT --locale-id en-US \
  --intent-name "OrderCoffee" \
  --sample-utterances \
    '[{"utterance":"I want a {CoffeeSize} {CoffeeDrink}"},{"utterance":"Can I get a coffee"}]' \
  --dialog-code-hook '{"enabled":true}' \
  --fulfillment-code-hook '{"enabled":true}' \
  --query 'intentId' --output text)

# Step 5: Create slots with explicit priorities
aws lexv2-models create-slot \
  --bot-id "$BOT_ID" --bot-version DRAFT --locale-id en-US \
  --intent-id "$INTENT_ID" --slot-name "CoffeeSize" \
  --slot-type-id "$SIZE_TYPE_ID" --priority 1 \
  --value-elicitation-setting \
    '{"slotConstraint":"Required","promptSpecification":{"messageGroups":[{"message":{"plainTextMessage":{"value":"What size? Small, medium, or large?"}}}],"maxRetries":3}}'

aws lexv2-models create-slot \
  --bot-id "$BOT_ID" --bot-version DRAFT --locale-id en-US \
  --intent-id "$INTENT_ID" --slot-name "CoffeeDrink" \
  --slot-type-id "$DRINK_TYPE_ID" --priority 2 \
  --value-elicitation-setting \
    '{"slotConstraint":"Required","promptSpecification":{"messageGroups":[{"message":{"plainTextMessage":{"value":"What kind of coffee? Latte, cappuccino, or americano?"}}}],"maxRetries":3}}'

# Step 6: Grant Lex permission to invoke the Lambda — CRITICAL
aws lambda add-permission \
  --function-name OrderCoffeeFulfillment \
  --statement-id LexInvokePermission \
  --action lambda:InvokeFunction \
  --principal lexv2.amazonaws.com \
  --source-arn "arn:aws:lex:us-east-1:123456789012:bot/$BOT_ID"

# Step 7: Build the locale (REQUIRED before versioning)
aws lexv2-models build-bot-locale --bot-id "$BOT_ID" --locale-id en-US
# Wait until status is Built

# Step 8: Create bot version
BOT_VERSION=$(aws lexv2-models create-bot-version \
  --bot-id "$BOT_ID" --description "Production release 1" \
  --query 'botVersion' --output text)

# Step 9: Create alias (blue-green endpoint)
ALIAS_ID=$(aws lexv2-models create-resource-link \
  --bot-id "$BOT_ID" --alias-name "prod" \
  --bot-version "$BOT_VERSION" --query 'resourceLinkId' --output text)
```

---

## Step 4 — Post-deployment verification

```bash
# Bot exists and is configured
aws lexv2-models describe-bot --bot-id "$BOT_ID"

# Locale is Built
aws lexv2-models describe-bot-locale \
  --bot-id "$BOT_ID" --locale-id en-US \
  --query 'botLocaleStatus'
# Expected: "Built"

# Version exists
aws lexv2-models describe-bot-version \
  --bot-id "$BOT_ID" --bot-version 1

# Alias points at the version
aws lexv2-models describe-resource-link \
  --bot-id "$BOT_ID" --resource-link-id "$ALIAS_ID"

# Lambda permission is set
aws lambda get-policy --function-name OrderCoffeeFulfillment

# Runtime smoke test
aws lexv2-runtime recognize-text \
  --bot-id "$BOT_ID" --bot-alias-id "$ALIAS_ID" \
  --locale-id en-US --session-id "smoke-test-001" \
  --text "I'd like a large latte"
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Slot priorities | Declares slots unordered | Explicit priority 1, 2, 3 | Elicitation order is priority-based; unordered = undefined |
| Code hooks | Wires fulfillment only | Both DIALOG + FULFILLMENT | Dialog hook is the dialog manager (validates, branches) |
| Lambda permission | Skips add-permission | Grants lexv2.amazonaws.com | Without it, code hook silently fails at runtime |
| Build locale | Skips build-bot-locale | Builds before versioning | Versions snapshot BUILT state only |
| Alias | Binds client to version | Creates alias prod → version | Alias enables blue-green + atomic rollback |
| Conversation logs | No KMS key | CMK with Lex service role | PII protection for audio/text logs |
| dataPrivacy | Not considered | Confirms childDirected=false | IMMUTABLE after creation |

---

## Related artifacts

- **Skill definition:** `skills/lex-bot-deployer/SKILL.md`
- **Intents and slots guide:** `skills/lex-bot-deployer/references/intents-and-slots.md`
- **Code hooks and aliases guide:** `skills/lex-bot-deployer/references/code-hooks-and-aliases.md`
- **Slash command:** `commands/aws/deploy-lex-bot.md`
- **Eval suite:** `skills/lex-bot-deployer/evals/evals.json`
- **Legacy test cases:** `skills/lex-bot-deployer/eval/test-cases.yaml`
