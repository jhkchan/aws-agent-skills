# Intents and Slots — Lex Bot Deployer

Deep reference on intent modeling (sample utterances, slot priorities,
elicitation flow, confirmation/closing/failure prompts), slot types
(built-in AMAZON.* vs custom enumerations), slot resolution strategies,
and the dependency between intents, slots, and locale builds. Loaded on
demand by the skill — kept out of the main SKILL.md body so the
provisioning procedure stays scannable.

## Intent fundamentals

### Intent structure

An intent is the conversational state the bot can match. Each intent
has:

| Field | Purpose | Required |
|---|---|---|
| `intentName` | Unique identifier within the bot | Yes |
| `sampleUtterances` | Training phrases the NLU matches against | Yes (at least one) |
| `slots` | Typed parameters the intent collects | Optional (but most intents have slots) |
| `confirmationSetting` | Prompts before fulfillment | Optional |
| `closingSetting` | Prompts after fulfillment | Optional |
| `dialogCodeHook` | Lambda interception between turns | Optional |
| `fulfillmentCodeHook` | Lambda action at end of conversation | Optional |
| `inputContexts` / `outputContexts` | State activation/propagation | Optional |

### Sample utterances

Sample utterances train the NLU. They can reference slots inline using
`{SlotName}` syntax:

```json
[
  {"utterance": "I want a {CoffeeSize} {CoffeeDrink}"},
  {"utterance": "Can I get a coffee"},
  {"utterance": "Order me a {CoffeeDrink}"},
  {"utterance": "{CoffeeSize} {CoffeeDrink} please"}
]
```

**Best practices:**
- Provide at least 5-10 utterances per intent for good NLU coverage.
- Mix slot-referencing and plain utterances.
- Include variations (questions, commands, fragments).
- Avoid utterances that overlap heavily with other intents — this
  degrades NLU confidence scores.

### Intent priority

When multiple intents could match an utterance, Lex uses the NLU
confidence score (threshold set per-locale via
`nluIntentConfidenceThreshold`, typically 0.40-0.60). If no intent
exceeds the threshold, the `FallbackIntent` is triggered.

## Slot fundamentals

### Slot elicitation order (priority)

Slots elicit in **priority** order (1 = highest, must be unique within
the intent). Only **required** slots are auto-elicited. Optional slots
are only elicited when the Lambda code hook explicitly requests them.

```text
Intent: OrderCoffee
  Slots:
    CoffeeSize    priority 1, required  → auto-elicited first
    CoffeeDrink   priority 2, required  → auto-elicited second
    CoffeeTemp    priority 3, optional  → NOT auto-elicited

When the user says "I want a large latte":
  CoffeeSize = large (from utterance)
  CoffeeDrink = latte (from utterance)
  CoffeeTemp = not set (optional, not elicited unless code hook asks)
```

**Setting slot priority:**

```bash
aws lexv2-models create-slot \
  --bot-id "$BOT_ID" --bot-version DRAFT --locale-id en-US \
  --intent-id "$INTENT_ID" \
  --slot-name "CoffeeSize" \
  --slot-type-id "CoffeeSizeType" \
  --priority 1 \
  --value-elicitation-setting '...'
```

### Slot constraints

| Constraint | Behavior |
|---|---|
| `Required` | Auto-elicited in priority order; intent cannot fulfill until filled |
| `Optional` | NOT auto-elicited; must be requested by the Lambda code hook |

### Elicitation prompts

Each required slot has an elicitation prompt (`promptSpecification`):

```json
{
  "slotConstraint": "Required",
  "promptSpecification": {
    "messageGroups": [
      {
        "message": {
          "plainTextMessage": {
            "value": "What size would you like? Small, medium, or large?"
          }
        }
      }
    ],
    "maxRetries": 3,
    "allowInterrupt": true
  }
}
```

`maxRetries` is the number of re-prompts before the bot gives up and
raises the failure-handling branch.

## Slot types

### Built-in slot types

Lex V2 provides pretrained slot types prefixed `AMAZON.`:

| Slot Type | Resolves | Example |
|---|---|---|
| `AMAZON.Date` | Dates ("tomorrow", "Jan 5", "2026-01-05") | "next Friday" → 2026-08-14 |
| `AMAZON.Time` | Times ("3pm", "15:00") | "noon" → 12:00 |
| `AMAZON.Number` | Numeric values | "five" → 5 |
| `AMAZON.AlphaNumeric` | Mixed alphanumeric | "order123" |
| `AMAZON.City` | City names | "San Francisco" |
| `AMAZON.Country` | Country names | "Japan" |
| `AMAZON.Currency` | Monetary amounts | "fifty dollars" → 50 USD |
| `AMAZON.EmailAddress` | Email addresses | "user@example.com" |
| `AMAZON.PhoneNumber` | Phone numbers | "+1-555-1234" |
| `AMAZON.Ordinal` | Ordinal numbers | "third" → 3 |

**When to use built-in:** dates, numbers, cities, currencies, emails,
phone numbers. Amazon's pretrained NLU resolves these better than
custom types.

### Custom slot types

Custom slot types are enumerations you define for domain-specific
values:

```bash
SLOT_TYPE_ID=$(aws lexv2-models create-slot-type \
  --bot-id "$BOT_ID" --bot-version DRAFT --locale-id en-US \
  --slot-type-name "CoffeeDrinkType" \
  --slot-type-values \
    '[{"sampleValue":{"value":"latte"}},
      {"sampleValue":{"value":"cappuccino"}},
      {"sampleValue":{"value":"americano"}},
      {"sampleValue":{"value":"espresso"}},
      {"sampleValue":{"value":"mocha"}}]' \
  --value-selection-setting \
    '{"resolutionStrategy":"TopResolution","regexFilter":{"pattern":"^\\w+$"}}' \
  --query 'slotTypeId' --output text)
```

**Resolution strategies:**

| Strategy | Behavior |
|---|---|
| `TopResolution` | Returns the top match (highest confidence) |
| `OriginalValue` | Returns the user's original input (no normalization) |
| `Concatenation` | Concatenates multiple matched values |

**Synonyms** can be added per value:

```json
{
  "sampleValue": {"value": "latte"},
  "synonyms": [
    {"value": "cafe latte"},
    {"value": "cafe au lait"}
  ]
}
```

### When to use custom vs built-in

```text
Use built-in (AMAZON.*) when:
  ├── Date/time/number — Amazon's pretrained NLU is better
  ├── City/country — extensive coverage
  └── Email/phone — well-defined formats

Use custom when:
  ├── Domain-specific enumeration (product names, categories)
  ├── Business-specific terms (plan tiers, service types)
  └── You need synonyms or fuzzy matching for jargon
```

**Avoid reinventing built-ins.** A custom slot type for dates will have
much worse NLU than `AMAZON.Date`.

## Confirmation, closing, and failure prompts

### Confirmation prompt

Fires before fulfillment — typically for side-effectful intents:

```json
{
  "confirmationSetting": {
    "promptSpecification": {
      "messageGroups": [{
        "message": {
          "plainTextMessage": {
            "value": "I'll order a {CoffeeSize} {CoffeeDrink}. Should I go ahead?"
          }
        }
      }],
      "maxRetries": 2
    },
    "declinationResponse": {
      "messageGroups": [{
        "message": {
          "plainTextMessage": {
            "value": "Okay, I've cancelled that."
          }
        }
      }]
    }
  }
}
```

If the user declines, `declinationResponse` fires and the intent ends
without fulfillment.

### Closing prompt

Fires after fulfillment (success):

```json
{
  "closingSetting": {
    "closingResponse": {
      "messageGroups": [{
        "message": {
          "plainTextMessage": {
            "value": "Your {CoffeeSize} {CoffeeDrink} is on the way. Anything else?"
          }
        }
      }],
      "allowInterrupt": true
    }
  }
}
```

### Failure prompt

Fires when confirmation is denied or max retries exceeded:

```json
{
  "failureHandling": {
    "failureResponse": {
      "messageGroups": [{
        "message": {
          "plainTextMessage": {
            "value": "I'm having trouble understanding. Let me connect you to an agent."
          }
        }
      }]
    }
  }
}
```

## Locale rebuild requirement

Any change to intents, slots, or slot types lands in DRAFT. The locale
must be rebuilt before the change takes effect or can be versioned:

```bash
aws lexv2-models build-bot-locale \
  --bot-id "$BOT_ID" --locale-id en-US

# Poll until status is Built
aws lexv2-models describe-bot-locale \
  --bot-id "$BOT_ID" --locale-id en-US \
  --query 'botLocaleStatus'
```

**Common mistake:** editing an intent and immediately trying to
`create-bot-version` without rebuilding. The version will snapshot the
old DRAFT state.

## Terraform examples

```hcl
resource "aws_lexv2models_bot" "coffee" {
  name                        = "OrderCoffeeBot"
  description                 = "Coffee ordering bot"
  idle_session_ttl_in_seconds = 300
  role_arn                    = aws_iam_role.lex_bot.arn
  data_privacy {
    child_directed = false
  }
}

resource "aws_lexv2models_bot_locale" "en_us" {
  bot_id                           = aws_lexv2models_bot.coffee.id
  locale_id                        = "en-US"
  n_lu_intent_confidence_threshold = 0.40
  voice_id                         = "Joanna"
  engine_type                      = "neural"
}

resource "aws_lexv2models_slot_type" "drink_type" {
  bot_id      = aws_lexv2models_bot.coffee.id
  bot_version = "DRAFT"
  locale_id   = "en-US"
  name        = "CoffeeDrinkType"
  slot_type_values {
    sample_value {
      value = "latte"
    }
  }
  slot_type_values {
    sample_value {
      value = "cappuccino"
    }
  }
  value_selection_setting {
    resolution_strategy = "TopResolution"
  }
}

resource "aws_lexv2models_intent" "order" {
  bot_id      = aws_lexv2models_bot.coffee.id
  bot_version = "DRAFT"
  locale_id   = "en-US"
  name        = "OrderCoffee"
  sample_utterances {
    utterance = "I want a {CoffeeSize} {CoffeeDrink}"
  }
  dialog_code_hook {
    enabled = true
  }
  fulfillment_code_hook {
    enabled = true
  }
}
```

## Expert heuristic: slot elicitation priority (moved from SKILL.md)

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
