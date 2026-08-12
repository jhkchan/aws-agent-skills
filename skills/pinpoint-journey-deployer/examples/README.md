# End-to-End Example: Pinpoint Journey Deployment

A walkthrough showing how to use the `pinpoint-journey-deployer`
skill from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning an event-based Pinpoint journey for abandoned
cart recovery with a conditional split, wait activities, quiet time,
and journey limits. The journey needs:

- Pinpoint project: app-xyz789
- Journey name: AbandonedCartRecovery
- Entry: event-based on cart_abandoned event
- Activities: SendReminderEmail, Wait1Hour, ConditionalSplit
  (check purchase_completed), SendReminderSMS, Wait24Hours
- Quiet time: 22:00-08:00 UTC Mon-Fri
- Journey limits: dailyCap 50000, maxEndpointSend 3
- Schedule: start 2026-08-15T09:00:00Z

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-pinpoint-journey
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a Pinpoint journey for abandoned cart recovery.
      Event-based entry on cart_abandoned. Conditional split
      checking purchase_completed. Quiet time 10pm-8am UTC.
      Daily cap 50000."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a pinpoint journey"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
PINPOINT_JOURNEY: AbandonedCartRecovery (journey-abc123) | project: app-xyz789
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Pinpoint project: app-xyz789
  [✓] Entry strategy: Event-based (event: cart_abandoned)
  [✓] Activities: SendReminderEmail, Wait1Hour, CheckPurchase, SendReminderSMS, Wait24Hours
  [✓] Send channels: email=on, SMS=on, push=off, in-app=off
  [✓] Conditional splits: CheckPurchase evaluating event purchase_completed (YES→ExitConverted, NO→SendReminderSMS)
  [✓] Multivariate splits: none
  [✓] Wait activities: Wait1Hour (1 HOUR), Wait24Hours (24 HOURS)
  [✓] Holdout: none
  [✓] Schedule: start 2026-08-15T09:00:00Z, timezone UTC
  [✓] Quiet time: 22:00–08:00 on MON,TUE,WED,THU,FRI (HOLDS, not cancels)
  [✓] Journey limits: dailyCap=50000, maxEndpointSend=3
  [✓] Custom channel: none
  [✓] Message templates referenced: cart-reminder-email, cart-reminder-sms
  [✓] Analytics: conversion event=purchase_completed
VERIFICATION_COMMANDS:
  aws pinpoint describe-journey --application-id app-xyz789 --journey-id journey-abc123
  aws pinpoint get-journey-date-range-kpi --application-id app-xyz789 --journey-id journey-abc123 --kpi-name UniqueEndpoints --start-time 2026-08-15T00:00:00Z --end-time 2026-08-22T00:00:00Z
```

---

## Step 3 — Provisioning commands

```bash
# Create the journey
JOURNEY_ID=$(aws pinpoint create-journey \
  --application-id app-xyz789 \
  --write-journey-request '{
    "Name": "AbandonedCartRecovery",
    "StartActivity": "SendReminderEmail",
    "StartCondition": {
      "EventStartCondition": {"EventPastDays": 0}
    },
    "Activities": {
      "SendReminderEmail": {
        "SendEmail": {
          "MessageType": "PROMOTIONAL",
          "TemplateConfiguration": {"EmailTemplate": {"Name": "cart-reminder-email"}},
          "NextActivity": "Wait1Hour"
        }
      },
      "Wait1Hour": {
        "Wait": {
          "WaitTime": {"WaitDuration": "1", "WaitDurationUnit": "HOURS"},
          "NextActivity": "CheckPurchase"
        }
      },
      "CheckPurchase": {
        "ConditionalSplit": {
          "Condition": {
            "Conditions": [{
              "EventCondition": {
                "Dimensions": {"EventType": {"Values": ["purchase_completed"], "ComparisonOperator": "IN"}}
              }
            }],
            "Operator": "ALL"
          },
          "TrueActivity": "ExitConverted",
          "FalseActivity": "SendReminderSMS"
        }
      },
      "ExitConverted": {"Exit": {}},
      "SendReminderSMS": {
        "SendSMS": {
          "MessageType": "PROMOTIONAL",
          "TemplateConfiguration": {"SMSTemplate": {"Name": "cart-reminder-sms"}},
          "NextActivity": "Wait24Hours"
        }
      },
      "Wait24Hours": {
        "Wait": {
          "WaitTime": {"WaitDuration": "24", "WaitDurationUnit": "HOURS"},
          "NextActivity": "ExitJourney"
        }
      },
      "ExitJourney": {"Exit": {}}
    },
    "QuietTime": {
      "Start": "22:00",
      "End": "08:00",
      "DaysOfWeek": ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]
    },
    "Limits": {
      "DailyCap": 50000,
      "MaximumEndpointSend": 3
    },
    "Schedule": {
      "StartTime": "2026-08-15T09:00:00Z",
      "Timezone": "UTC"
    }
  }' \
  --query 'JourneyResponse.Id' --output text)

echo "Journey ID: $JOURNEY_ID"

# Activate the journey
aws pinpoint update-journey-state \
  --application-id app-xyz789 \
  --journey-id "$JOURNEY_ID" \
  --journey-state-request '{"State": "ACTIVE"}'
```

---

## Step 4 — Post-deployment verification

```bash
# Journey exists and is ACTIVE
aws pinpoint describe-journey \
  --application-id app-xyz789 \
  --journey-id "$JOURNEY_ID" \
  --query 'JourneyResponse.{Name:Name,State:State,StartActivity:StartActivity}'

# Check participant count (after journey has been running)
aws pinpoint get-journey-date-range-kpi \
  --application-id app-xyz789 \
  --journey-id "$JOURNEY_ID" \
  --kpi-name "UniqueEndpoints" \
  --start-time 2026-08-15T00:00:00Z \
  --end-time 2026-08-22T00:00:00Z

# Verify quiet time is configured
aws pinpoint describe-journey \
  --application-id app-xyz789 \
  --journey-id "$JOURNEY_ID" \
  --query 'JourneyResponse.QuietTime'
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Entry strategy | Defaults to segment-based | Event-based (cart_abandoned) | Behavioral trigger needs real-time entry, not bulk |
| Conditional split | Uses random/multivariate | Evaluates purchase_completed event | Conditional = event-based branching, not random |
| Quiet time | Assumes messages are dropped | Notes HOLDS not cancels | Held messages deliver when window closes |
| Wait interaction | Ignores quiet-time drift | Notes cadence shift risk | Duration waits drift with quiet-time holds |
| Journey limits | Omits or sets too high | dailyCap=50000, maxEndpointSend=3 | Cost control; prevents runaway spend |
| Template references | Forgets to create templates | Lists referenced templates | Send activities fail if template missing |
| Schedule timezone | Omits or defaults to UTC | Explicit UTC | Timezone mismatch causes off-schedule sends |

---

## Related artifacts

- **Skill definition:** `skills/pinpoint-journey-deployer/SKILL.md`
- **Activities and splits guide:** `skills/pinpoint-journey-deployer/references/activities-and-splits.md`
- **Schedule and limits guide:** `skills/pinpoint-journey-deployer/references/schedule-and-limits.md`
- **Slash command:** `commands/aws/deploy-pinpoint-journey.md`
- **Eval suite:** `skills/pinpoint-journey-deployer/evals/evals.json`
- **Legacy test cases:** `skills/pinpoint-journey-deployer/eval/test-cases.yaml`
