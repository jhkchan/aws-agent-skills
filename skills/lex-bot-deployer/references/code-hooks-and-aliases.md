# Code Hooks and Aliases — Lex Bot Deployer

Deep reference on Lambda code hooks (DIALOG_CODE_HOOK vs
FULFILLMENT_CODE_HOOK, invocationSource branching, Lambda resource-based
permissions), bot versioning and aliases (blue-green deployment, atomic
rollback, build-then-version-then-alias sequencing), conversation logs
and KMS encryption, and the lexv2-models vs lexv2-runtime API split.
Loaded on demand by the skill — kept out of the main SKILL.md body so
the provisioning procedure stays scannable.

## Lambda code hooks

### Two independent hooks per intent

| Hook | invocationSource | When it fires | Purpose |
|---|---|---|---|
| `dialogCodeHook` | `DialogCodeHook` | After EVERY user turn | Validation, branching, slot enrichment, dynamic prompts |
| `fulfillmentCodeHook` | `FulfillmentCodeHook` | After confirmation, before Close | Final action (API call, DB write, email) |

These are **separate flags** on the intent. Enabling one does NOT
enable the other. A baseline model wires FULFILLMENT_CODE_HOOK only and
loses mid-conversation validation.

### The code hook event

Lex sends an event to the Lambda with `invocationSource` indicating
which hook fired:

```json
{
  "invocationSource": "DialogCodeHook",
  "botId": "bot-abc123",
  "intentName": "OrderCoffee",
  "sessionId": "user-1234",
  "sessionState": {
    "dialogAction": {"type": "ElicitSlot", "slotToElicit": "CoffeeSize"},
    "intent": {
      "name": "OrderCoffee",
      "slots": {
        "CoffeeSize": null,
        "CoffeeDrink": null,
        "CoffeeTemp": null
      }
    }
  },
  "inputTranscript": "I want a large latte"
}
```

### Lambda handler structure

Branch on `invocationSource` to separate validation from fulfillment:

```python
import json

def lambda_handler(event, context):
    invocation_source = event['invocationSource']
    session_state = event['sessionState']
    intent = session_state['intent']
    slots = intent.get('slots', {})

    if invocation_source == 'DialogCodeHook':
        return handle_dialog(event, slots, session_state)
    elif invocation_source == 'FulfillmentCodeHook':
        return handle_fulfillment(event, slots, session_state)

def handle_dialog(event, slots, session_state):
    # Validate slots, enrich, branch
    coffee_size = slots.get('CoffeeSize')
    if coffee_size and coffee_size['value']['interpretedValue'] == 'extra-large':
        # Reject unsupported value, re-elicit
        return {
            'sessionState': {
                'dialogAction': {
                    'type': 'ElicitSlot',
                    'slotToElicit': 'CoffeeSize'
                },
                'intent': session_state['intent']
            },
            'messages': [{
                'contentType': 'PlainText',
                'content': "Sorry, we don't offer extra-large. Small, medium, or large?"
            }]
        }

    # All validations pass — delegate back to Lex for next slot
    return {
        'sessionState': {
            'dialogAction': {'type': 'Delegate'},
            'intent': session_state['intent']
        }
    }

def handle_fulfillment(event, slots, session_state):
    # Perform the action (API call, DB write)
    coffee_size = slots['CoffeeSize']['value']['interpretedValue']
    coffee_drink = slots['CoffeeDrink']['value']['interpretedValue']
    # ... call downstream API ...

    return {
        'sessionState': {
            'dialogAction': {'type': 'Close'},
            'intent': {**session_state['intent'], 'state': 'Fulfilled'}
        },
        'messages': [{
            'contentType': 'PlainText',
            'content': f'Your {coffee_size} {coffee_drink} is confirmed!'
        }]
    }
```

### Dialog action types

The Lambda controls the conversation flow by returning a `dialogAction`:

| Type | Behavior |
|---|---|
| `Delegate` | Let Lex decide the next step (normal elicitation flow) |
| `ElicitSlot` | Ask the user for a specific slot (override priority order) |
| `ElicitIntent` | Switch to a different intent |
| `ConfirmIntent` | Prompt for confirmation of the current intent |
| `Close` | End the conversation (fulfilled or failed) |

### Lambda resource-based permission

The Lambda MUST grant `lambda:InvokeFunction` to `lexv2.amazonaws.com`
scoped to the bot's ARN. Without this, the code hook silently fails at
runtime (no error at configuration time):

```bash
aws lambda add-permission \
  --function-name OrderCoffeeFulfillment \
  --statement-id LexInvokePermission \
  --action lambda:InvokeFunction \
  --principal lexv2.amazonaws.com \
  --source-arn "arn:aws:lex:us-east-1:123456789012:bot/$BOT_ID"

# Verify
aws lambda get-policy --function-name OrderCoffeeFulfillment
```

**Critical:** the `--source-arn` must match the bot's ARN exactly. If
the bot ID changes (e.g., recreated), update the permission.

## Bot versioning

### Build-then-version sequence

Bot versions are snapshots of DRAFT. The locale must be `Built` before
versioning:

```bash
# 1. Build the locale
aws lexv2-models build-bot-locale \
  --bot-id "$BOT_ID" --locale-id en-US

# 2. Wait until status is Built
aws lexv2-models describe-bot-locale \
  --bot-id "$BOT_ID" --locale-id en-US \
  --query 'botLocaleStatus'
# Expected: "Built"

# 3. Create a bot version
BOT_VERSION=$(aws lexv2-models create-bot-version \
  --bot-id "$BOT_ID" \
  --description "Production release 2026-08-11" \
  --query 'botVersion' --output text)
```

A bot version snapshots ALL built locales simultaneously. If you have
en-US and es-ES locales, both are captured in the same version.

### Version immutability

Versions are immutable. To update a bot, edit DRAFT, rebuild, then
create a NEW version. You cannot modify an existing version.

```bash
# List all versions
aws lexv2-models list-bot-versions \
  --bot-id "$BOT_ID" \
  --query 'botVersionSummaries[*].{Version:botVersion,Status:botVersionStatus}' \
  --output table
```

## Aliases (resource links)

### What an alias is

An alias (formally "resource link") is a named pointer to a bot version.
Runtime clients reference the alias, not the version directly. This
indirection enables blue-green deployment:

```text
Bot: OrderCoffeeBot
  Version 1 (2026-08-01 snapshot)
  Version 2 (2026-08-05 snapshot)

Alias "prod"     → Version 1  (live traffic)
Alias "staging"  → Version 2  (QA traffic)
Alias "dev"      → DRAFT     (development)
```

### Creating an alias

```bash
ALIAS_ID=$(aws lexv2-models create-resource-link \
  --bot-id "$BOT_ID" \
  --alias-name "prod" \
  --bot-version "$BOT_VERSION" \
  --query 'resourceLinkId' --output text)
```

### Blue-green deployment

To shift the prod alias to a new version:

```bash
aws lexv2-models update-resource-link \
  --bot-id "$BOT_ID" \
  --alias-id "$ALIAS_ID" \
  --bot-version "$NEW_VERSION"
```

This is atomic — all clients referencing the alias immediately see the
new version. No client-side changes needed.

### Rollback

To roll back, point the alias back to the previous version (single API
call):

```bash
aws lexv2-models update-resource-link \
  --bot-id "$BOT_ID" \
  --alias-id "$ALIAS_ID" \
  --bot-version "$PREVIOUS_VERSION"
```

**Critical:** NEVER point runtime clients at a specific version. Always
use an alias. Binding clients to a version locks you in and requires
client-side changes for every update.

## Conversation logs

### Text and audio logs

Lex V2 can log both text transcripts and audio recordings of every
conversation. Logs are delivered to CloudWatch Logs and/or S3.

```bash
aws lexv2-models put-bot-locale \
  --bot-id "$BOT_ID" --locale-id en-US \
  --conversation-log-settings '{
    "textLogSettings": {
      "enabled": true,
      "destination": "CloudWatchLogs",
      "cloudWatchLogsLogGroupArn": "arn:aws:logs:us-east-1:123456789012:log-group:/aws/lex/OrderCoffeeBot"
    },
    "audioLogSettings": {
      "enabled": false
    }
  }'
```

### KMS encryption

For custom encryption, provide a CMK. The KMS key policy MUST grant the
Lex service-linked role:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowLexToUseKey",
      "Effect": "Allow",
      "Principal": {
        "Service": "lexv2.amazonaws.com"
      },
      "Action": [
        "kms:GenerateDataKey",
        "kms:Decrypt"
      ],
      "Resource": "*"
    }
  ]
}
```

Without the KMS policy, log delivery fails silently. Verify by checking
CloudWatch Logs after the first conversation.

### Lex service role for logs

The Lex-assumed role needs CloudWatch Logs permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:us-east-1:123456789012:log-group:/aws/lex/OrderCoffeeBot:*"
    }
  ]
}
```

## lexv2-models vs lexv2-runtime

| API | Purpose | Key calls |
|---|---|---|
| `lexv2-models` | Build-time: create bot, intents, slots, versions, aliases | `create-bot`, `create-intent`, `create-slot`, `build-bot-locale`, `create-bot-version`, `create-resource-link` |
| `lexv2-runtime` | Runtime: send user input, receive responses | `recognize-text`, `recognize-utterance`, `start-conversation`, `put-session`, `delete-session` |

**Runtime calls always reference `botAliasId`, never `botVersion`:**

```bash
aws lexv2-runtime recognize-text \
  --bot-id "$BOT_ID" \
  --bot-alias-id "$ALIAS_ID" \
  --locale-id en-US \
  --session-id "user-1234" \
  --text "I'd like a large latte"
```

## Terraform alias example

```hcl
resource "aws_lexv2models_bot_version" "v1" {
  bot_id      = aws_lexv2models_bot.coffee.id
  description = "Production release 1"
  depends_on  = [aws_lexv2models_bot_locale.en_us]
}

resource "aws_lexv2models_bot_alias" "prod" {
  bot_id      = aws_lexv2models_bot.coffee.id
  bot_version = aws_lexv2models_bot_version.v1.bot_version
  name        = "prod"
  description = "Production alias"
}
```

## Expert heuristic: Lambda code hook fires between every turn (moved from SKILL.md)

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

## Expert heuristic: alias enables blue-green bot deployment (moved from SKILL.md)

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

## lexv2-runtime recognize-text example (moved from SKILL.md)

```bash
# Send text to the bot (runtime)
aws lexv2-runtime recognize-text \
  --bot-id "$BOT_ID" --bot-alias-id "$ALIAS_ID" \
  --locale-id en-US --session-id "user-1234" \
  --text "I'd like a large latte"
```

## Grant Lex permission to invoke the Lambda (moved from SKILL.md)

**Grant Lex permission to invoke the Lambda:**

```bash
aws lambda add-permission \
  --function-name OrderCoffeeFulfillment \
  --statement-id LexInvokePermission \
  --action lambda:InvokeFunction \
  --principal lexv2.amazonaws.com \
  --source-arn "arn:aws:lex:us-east-1:123456789012:bot/$BOT_ID"
```
