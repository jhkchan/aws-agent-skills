# Activities and Splits — Pinpoint Journey Deployer

Deep reference on journey activities (send message, wait, custom
channel), conditional splits (event-attribute evaluation, yes/no
branching), multivariate splits (random percentage, A/B testing),
holdout (control group suppression), and the dependency between
activities, events, and channels. Loaded on demand by the skill —
kept out of the main SKILL.md body so the provisioning procedure
stays scannable.

## Activity types

A Pinpoint journey is a directed graph of activities. Each activity
has a type and a `NextActivity` pointer (except terminal activities).

| Activity | Purpose | NextActivity |
|---|---|---|
| `SendEmail` / `SendSMS` / `SendPush` / `SendInApp` | Dispatch a message | Required (or terminal) |
| `Wait` | Hold participant for duration or until absolute time | Required |
| `ConditionalSplit` | Branch based on event attribute (yes/no) | True + False activities |
| `MultivariateSplit` | Branch randomly by percentage | One per branch |
| `Holdout` | Suppress percentage at entry (control group) | Terminal |
| `Custom` | Invoke Lambda webhook | Required |
| `RandomSplit` (legacy) | Alias for multivariate | One per branch |

## Send message activities

### Email send

```json
{
  "SendEmail": {
    "MessageType": "PROMOTIONAL",
    "TemplateConfiguration": {
      "EmailTemplate": {
        "Name": "cart-reminder-email",
        "Version": "1"
      }
    },
    "NextActivity": "Wait24Hours"
  }
}
```

**MessageType:** `TRANSACTIONAL` (critical, bypasses some filters) or
`PROMOTIONAL` (marketing, subject to quiet time and opt-outs).

**Templates:** reference a pre-created Pinpoint message template by
name. Templates support Liquid personalization:
- `{{User.UserAttributes.FirstName}}` — user attribute
- `{{Attributes.ItemName}}` — event attribute
- `{{Metrics.CartValue}}` — event metric

### SMS send

```json
{
  "SendSMS": {
    "MessageType": "PROMOTIONAL",
    "SenderId": "MyBrand",
    "TemplateConfiguration": {
      "SMSTemplate": {"Name": "cart-reminder-sms"}
    },
    "NextActivity": "ExitJourney"
  }
}
```

**SMS throughput:** long codes (10DLC) = 1 MPS; short codes = 100+ MPS.
For high-volume SMS journeys, ensure sufficient origination numbers.

### Push send

```json
{
  "SendPush": {
    "TemplateConfiguration": {
      "PushTemplate": {"Name": "checkout-push"}
    },
    "NextActivity": "ExitJourney"
  }
}
```

**Prerequisites:** APNs certificate and FCM API key configured on the
Pinpoint project. Endpoints must have valid device tokens. Tokens
expire — stale tokens cause silent failures.

## Conditional split

A conditional split evaluates whether a participant performed an event
during the journey. It branches into YES and NO paths.

### Structure

```json
{
  "ConditionalSplit": {
    "Condition": {
      "Conditions": [
        {
          "EventCondition": {
            "Dimensions": {
              "EventType": {
                "Values": ["purchase_completed"],
                "ComparisonOperator": "IN"
              },
              "Attributes": {
                "category": {
                  "Values": ["electronics"],
                  "ComparisonOperator": "IN"
                }
              }
            }
          }
        }
      ],
      "Operator": "ALL"
    },
    "TrueActivity": "ExitConverted",
    "FalseActivity": "SendReminderSMS"
  }
}
```

### Event evaluation window

The conditional split evaluates events recorded DURING the journey
window. Events recorded before the participant entered the journey do
NOT count. This is critical for abandoned cart flows:

```text
Participant enters journey (cart_abandoned event recorded)
  → Wait 1 hour
  → Conditional split: Did participant record "purchase_completed"?
      The split checks events recorded SINCE journey entry.
      If the participant completed purchase BEFORE entering the journey,
      the YES branch does NOT fire.
```

### Multiple conditions

Use `Operator: "ALL"` (AND) or `"ANY"` (OR) to combine conditions:

```json
{
  "Conditions": [
    {"EventCondition": {"Dimensions": {"EventType": {"Values": ["purchase_completed"]}}}},
    {"EventCondition": {"Dimensions": {"EventType": {"Values": ["add_to_cart"]}}}}
  ],
  "Operator": "ANY"
}
```

This evaluates: did the participant record purchase_completed OR
add_to_cart during the journey?

### Segment-based conditions

Conditional splits can also evaluate segment membership instead of
events:

```json
{
  "SegmentCondition": {
    "SegmentId": "segment-vip-users-123"
  }
}
```

This branches based on whether the participant is in the specified
segment at evaluation time.

## Multivariate split

A multivariate split assigns participants randomly to branches by
percentage. Percentages MUST sum to exactly 100.

### Structure

```json
{
  "MultivariateSplit": {
    "Tests": [
      {
        "Branches": [
          {"Percentage": 33, "NextActivity": "SendVariantA"},
          {"Percentage": 33, "NextActivity": "SendVariantB"},
          {"Percentage": 34, "NextActivity": "SendVariantC"}
        ]
      }
    ]
  }
}
```

### A/B testing best practices

- Pair with a holdout to measure absolute lift (not just relative).
- Test ONE variable at a time (subject line, send time, template).
- Run for at least 7 days for statistical significance.
- Use journey analytics to compare conversion rates across branches.

### Multivariate vs conditional

```text
Multivariate split: RANDOM assignment for testing.
  "50% get variant A, 50% get variant B" — no condition, pure random.

Conditional split: BEHAVIORAL branching based on events.
  "Did the user purchase? YES→exit, NO→remind" — evaluates an event.
```

## Holdout

A holdout suppresses a percentage of participants at entry. They never
start the journey. This is the control group for A/B lift measurement.

```json
{
  "Holdout": {
    "Percentage": 10,
    "NextActivity": "ExitHoldout"
  }
}
```

### Holdout placement

Place the holdout as the FIRST activity in the journey, before any
message send. This ensures the control group receives zero journey
messages:

```text
Entry → Holdout (10%) → ExitHoldout
                 ↓ (90%)
         SendVariantA (first message)
```

### Holdout vs multivariate no-send branch

```text
Holdout: participant is SUPPRESSED at entry — never enters the journey.
  Use for: A/B lift measurement (true control group).

Multivariate no-send branch: participant enters the journey but gets
  no message on one branch (may receive later messages on other branches).
  Use for: testing message content variants.
```

## Wait activity

### Duration-based wait

```json
{
  "Wait": {
    "WaitTime": {"WaitDuration": "24", "WaitDurationUnit": "HOURS"},
    "NextActivity": "SendFollowUp"
  }
}
```

Units: `SECONDS`, `MINUTES`, `HOURS`, `DAYS`.

### Absolute-time wait

```json
{
  "Wait": {
    "WaitTime": {"Until": "2026-08-15T09:00:00Z"},
    "NextActivity": "SendMorningEmail"
  }
}
```

### Wait and quiet time interaction

Waits interact with quiet time. If a wait ends during a quiet period,
the subsequent send is held:

```text
Wait ends at 23:00 (inside quiet time 22:00-08:00)
  → Send held until 08:00
  → Effective send time: 08:00 (9 hours late)
```

**Recommendation:** use absolute-time waits to anchor sends to specific
clock times, avoiding drift from quiet-time delays.

## Custom channel

```json
{
  "Custom": {
    "EndpointType": "Lambda",
    "LambdaFunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:CustomChannelHandler",
    "NextActivity": "WaitBeforeRetry"
  }
}
```

**Lambda event payload:** Pinpoint sends the endpoint data, journey
context, and activity configuration. The Lambda can dispatch to
webhooks, third-party APIs, or internal systems.

**Timeout:** Pinpoint expects the Lambda to complete within 15 seconds.
For long-running operations, queue to SQS or Step Functions and return
immediately.

## Terraform example

```hcl
resource "aws_pinpoint_journey" "cart_recovery" {
  application_id = aws_pinpoint_app.shop.app_id
  name           = "AbandonedCartRecovery"

  activities = {
    SendReminderEmail = {
      email = {
        message_type = "PROMOTIONAL"
        template {
          name    = "cart-reminder-email"
          version = "1"
        }
        next_activity = "Wait1Hour"
      }
    }
    Wait1Hour = {
      wait = {
        wait_time {
          wait_duration = "1"
          wait_unit     = "HOURS"
        }
        next_activity = "CheckPurchase"
      }
    }
  }

  start_activity  = "SendReminderEmail"
  start_condition {
    event_start_condition {
      event_past_days = 0
    }
  }

  quiet_time {
    start = "22:00"
    end   = "08:00"
  }

  limits {
    daily_cap            = 50000
    maximum_endpoint_send = 3
  }
}
```
