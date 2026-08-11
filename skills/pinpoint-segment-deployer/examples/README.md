# End-to-End Example: Pinpoint Segment Deployment

A walkthrough showing how to use the `pinpoint-segment-deployer`
skill from invocation through verification. Mirrors the structured-
eval pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a Pinpoint dynamic segment with a multi-branch
journey for an onboarding campaign. The deployment needs:

- Project: app-abc123 (my-pinpoint-project)
- Segment: dynamic, Behavior DAY_7 ACTIVE + Demographic Channel
  [GCM, APNS], resolves to 42,500 endpoints
- Journey: onboarding-7d (ENTRY → welcome-email → WAIT 3d →
  CONDITIONAL_SPLIT on purchase event → END branches)
- Channels: email (SES verified), SMS (long code +1 555-123-4567,
  10DLC registered), push (APNs token, FCM service account)
- A/B test inside the journey: MULTIVARIATE_SPLIT 50/50
  (discount-email vs nudge-email)
- Quiet time: 22:00-08:00 America/Los_Angeles
- Frequency cap: 3/day per channel, 10/day total
- Event stream: Kinesis stream pinpoint-events

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-pinpoint-segment
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a Pinpoint dynamic segment on app-abc123 with Behavior
      DAY_7 ACTIVE and Demographic Channel [GCM, APNS]. Build an
      onboarding-7d journey with a CONDITIONAL_SPLIT on the
      purchase event. Email and SMS channels. Quiet time
      22:00-08:00 PT."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a pinpoint segment and journey"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
PINPOINT_SEGMENT: app-abc123/seg-def456 (dynamic, 42500 endpoints)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Project: app-abc123 (my-pinpoint-project)
  [✓] Segment: seg-def456 — dynamic (42,500 endpoints)
  [✓] Segment type: Dynamic (recompute on eval)
  [✓] Dimensions: Behavior(DAY_7 ACTIVE) + Demographic(Channel=GCM,APNS)
  [✓] Channel: multi (email verified, SMS verified, push verified)
  [✓] Template: welcome-email (Liquid valid, channel matches)
  [✓] Schedule: immediate
  [✓] Quiet time: 22:00-08:00 America/Los_Angeles
  [✓] Frequency cap: 3/day per channel, 10/day total
  [✓] A/B test: 20% holdout + 3 treatments (20%+40%+20%, sum=100, sample-size OK)
  [✓] Journey: onboarding-7d (DAG, all paths reach END, CONDITIONAL_SPLIT has WaitTime)
  [✓] Event stream: kinesis:us-east-1:123456789012:stream/pinpoint-events
  [✓] SMS number: long code 10DLC +1 555-123-4567 (campaign registry OK)
  [✓] Push: APNs (TOKEN), FCM (service account)
  [✓] Tags: Environment=production, Campaign=onboarding
VERIFICATION_COMMANDS:
  aws pinpoint get-app --application-id app-abc123
  aws pinpoint get-segment-estimate --application-id app-abc123 --segment-id seg-def456
  aws pinpoint get-journey --application-id app-abc123 --journey-id jrn-xyz789
  aws pinpoint get-event-stream --application-id app-abc123
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Verify the project
aws pinpoint get-app --application-id app-abc123

# Step 2: Create the dynamic segment
SEGMENT_ID=$(aws pinpoint create-segment \
  --application-id app-abc123 \
  --write-segment-request '{
    "Name": "active-mobile-7d",
    "SegmentGroups": {
      "Groups": [{
        "Dimensions": [
          {"Behavior": {"Recency": {"Duration": "DAY_7", "RecencyType": "ACTIVE"}}},
          {"Demographic": {"Channel": {"DimensionType": "INCLUSIVE", "Values": ["GCM","APNS"]}}}
        ],
        "SourceType": "ALL",
        "Type": "ANY"
      }],
      "Include": "ALL"
    }
  }' \
  --query 'SegmentResponse.Id' --output text)

# Step 3: Verify segment resolution
aws pinpoint get-segment-estimate \
  --application-id app-abc123 \
  --segment-id "$SEGMENT_ID"

# Step 4: Create the journey with CONDITIONAL_SPLIT (with WaitTime)
JOURNEY_ID=$(aws pinpoint create-journey \
  --application-id app-abc123 \
  --write-journey-request '{
    "Name": "onboarding-7d",
    "StateMachine": {
      "StartActivity": "entry-activity",
      "Activities": {
        "entry-activity": {"ENTRY": {}, "NextActivity": "send-welcome"},
        "send-welcome": {"SEND": {"MessageConfig": {"EmailConfig": {"TemplateInformation": {"Name": "welcome-email"}}}}, "NextActivity": "wait-3d"},
        "wait-3d": {"WAIT": {"WaitTime": {"WaitFor": "PT3D"}}, "NextActivity": "purchase-split"},
        "purchase-split": {
          "CONDITIONAL_SPLIT": {
            "Condition": {"Conditions": [{"EventCondition": {"Dimensions": {"Event": {"EventType": {"DimensionType": "INCLUSIVE", "Values": ["purchase"]}}}, "MessageActivity": "purchase-thanks"}}], "Operator": "ALL"},
            "FalseActivity": "still-interested",
            "TrueActivity": "purchase-thanks"
          }
        },
        "purchase-thanks": {"SEND": {"MessageConfig": {"EmailConfig": {"TemplateInformation": {"Name": "thanks-email"}}}}, "NextActivity": "end"},
        "still-interested": {
          "MULTIVARIATE_SPLIT": {
            "Branches": [
              {"Percentage": 50, "NextActivity": "discount-email"},
              {"Percentage": 50, "NextActivity": "nudge-email"}
            ]
          }
        },
        "discount-email": {"SEND": {"MessageConfig": {"EmailConfig": {"TemplateInformation": {"Name": "discount-email"}}}}, "NextActivity": "end"},
        "nudge-email": {"SEND": {"MessageConfig": {"EmailConfig": {"TemplateInformation": {"Name": "nudge-email"}}}}, "NextActivity": "end"},
        "end": {"END": {}}
      }
    }
  }' \
  --query 'JourneyResponse.Id' --output text)

# Step 5: Verify the journey
aws pinpoint get-journey --application-id app-abc123 --journey-id "$JOURNEY_ID"

# Step 6: Configure quiet time and frequency cap (project-wide)
aws pinpoint update-application-settings \
  --application-id app-abc123 \
  --write-application-settings-request '{
    "Limits": {"Daily": 3, "Total": 10, "MessagesPerSecond": 50},
    "QuietTime": {"End": "08:00", "Start": "22:00"}
  }'

# Step 7: Wire the event stream (Kinesis)
aws pinpoint put-event-stream \
  --application-id app-abc123 \
  --write-event-stream '{
    "DestinationStreamArn": "arn:aws:kinesis:us-east-1:123456789012:stream/pinpoint-events",
    "RoleArn": "arn:aws:iam::123456789012:role/PinpointKinesisRole"
  }'
```

---

## Step 4 — Post-deployment verification

```bash
# Segment resolution
aws pinpoint get-segment-estimate \
  --application-id app-abc123 \
  --segment-id "$SEGMENT_ID" \
  --query 'SegmentResponse'

# Journey execution metrics
aws pinpoint get-journey-execution-metrics \
  --application-id app-abc123 \
  --journey-id "$JOURNEY_ID"

# Event stream
aws pinpoint get-event-stream --application-id app-abc123

# Application settings (quiet time + frequency cap)
aws pinpoint get-application-settings --application-id app-abc123
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Segment type | Treats as static list | Dynamic (recompute on eval) | Dynamic segments re-evaluate at send time; count differs |
| CONDITIONAL_SPLIT | No WaitTime | WaitTime before split | Without it, endpoints route NO immediately |
| Journey DAG | Open paths | All paths reach END | Open paths trap endpoints |
| A/B sample size | Splits 50/50 | Sample-size gate | Underpowered tests produce noise |
| US SMS number | Sender ID | Long code 10DLC | Sender ID not supported in US |
| Event stream | Multiple streams | One active stream | put-event-stream replaces, not appends |
| Frequency cap | Cap of 0 | Cap ≥ 1 | Cap of 0 blocks all sends |

---

## Related artifacts

- **Skill definition:** `skills/pinpoint-segment-deployer/SKILL.md`
- **Segments and dimensions guide:** `skills/pinpoint-segment-deployer/references/segments-and-dimensions.md`
- **Journeys and A/B testing guide:** `skills/pinpoint-segment-deployer/references/journeys-and-ab-testing.md`
- **Slash command:** `commands/aws/deploy-pinpoint-segment.md`
- **Eval suite:** `skills/pinpoint-segment-deployer/evals/evals.json`
- **Legacy test cases:** `skills/pinpoint-segment-deployer/eval/test-cases.yaml`
