---
name: pinpoint-segment-deployer
description: >-
  Provisions Amazon Pinpoint projects, segments, campaigns, journeys, and
  channels with production defaults. Segment-first model: dynamic segments
  (Dimensions: Demographic, Behavior, UserAttributes, Device attributes,
  recency) recompute on every evaluation; static segments are imported
  (CSV/S3) and pinned. Campaigns are scheduled or event-triggered
  (Behavior trigger: app/email/SMS/in-app events). Channels: email
  (SES verified identity), SMS (sender ID, long code, toll-free, 10DLC),
  push (APNs .p8 token, FCM API key), voice (origination number).
  Templates: email (HTML + Liquid), SMS (message body + Liquid), push
  (APNS/GCM JSON). A/B testing with AdditionalTreatments and holdout
  percentage (sum to 100). Quiet time (StartTime, EndTime, TimeZone) and
  project-wide frequency caps. Event streaming to Kinesis Data Streams or
  Kinesis Firehose (S3). Journeys: ENTRY, CONDITIONAL_SPLIT (yes-no on
  event/attribute), MULTIVARIATE_SPLIT (multi-branch A/B/C by percentage),
  RANDOM_SPLIT, WAIT (time or event-based), CONTROL, SEND, END — DAG,
  every path reaches END. SMS number types: sender ID (alphanumeric,
  per-country support), long code (DID, 10DLC US), toll-free, short code.
  Emits a READY_TO_DEPLOY checklist with verification commands. Use when
  creating a Pinpoint project, building a dynamic or static segment,
  designing a multi-branch journey with event-conditional splits,
  configuring A/B tests with sample size justification, setting up SMS
  with sender ID or long codes, wiring GCM/APNs push, or streaming events
  to Kinesis/S3. Triggers: create Pinpoint segment, dynamic segment,
  static segment, segment dimensions, Pinpoint journey, conditional
  split journey, multivariate journey, A/B test sample size, SMS sender
  ID, long code, toll-free number, APNs push setup, FCM push setup,
  Pinpoint event stream Kinesis, Pinpoint event stream S3.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live deployment: AWS CLI v2 with pinpoint access
  (and sesv2 for email identity verification, pinpoint-sms-voice for
  origination numbers). Works with Terraform aws_pinpoint_app,
  aws_pinpoint_segment, aws_pinpoint_campaign, aws_pinpoint_journey,
  aws_pinpoint_event_stream, aws_pinpoint_sms_channel,
  aws_pinpoint_email_channel, aws_pinpoint_apns_channel,
  aws_pinpoint_gcm_channel resources and CloudFormation
  AWS::Pinpoint::Segment / Campaign / Application templates.
keywords:
  - aws
  - pinpoint
  - segment
  - dynamic segment
  - static segment
  - dimensions
  - demographic
  - behavior
  - user attributes
  - journey
  - conditional split
  - multivariate split
  - random split
  - wait
  - event-triggered
  - scheduled campaign
  - email channel
  - sms channel
  - push channel
  - voice channel
  - sender id
  - long code
  - toll-free
  - 10dlc
  - apns
  - gcm
  - fcm
  - template
  - a/b test
  - holdout
  - quiet time
  - frequency cap
  - event stream
  - kinesis
  - firehose
  - s3
tags:
  - aws
  - pinpoint
  - segment
  - appintegration
  - deploy
  - messaging
  - personalization
  - multi-channel
  - journey
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: AppIntegration
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - pinpoint
    - segment
    - appintegration
    - deploy
    - messaging
    - personalization
    - multi-channel
    - journey
  dependencies:
    - aws-orchestrator
  keywords:
    - create pinpoint segment
    - dynamic segment
    - static segment
    - segment dimensions
    - pinpoint journey
    - conditional split journey
    - multivariate journey
    - ab test sample size
    - sms sender id
    - long code
    - toll-free number
    - apns push setup
    - fcm push setup
    - pinpoint event stream kinesis
    - pinpoint event stream s3
  when_to_use: >-
    Invoke when the user wants to create a Pinpoint project, build a
    dynamic or static segment (with Demographic/Behavior/UserAttributes/
    Device dimensions), design a multi-step journey with event-
    conditional branches or multivariate splits, configure an A/B test
    with sample size justification, set up SMS with sender ID / long
    code / toll-free / 10DLC, configure APNs or FCM push channels, build
    scheduled or event-triggered campaigns, apply quiet time and
    frequency caps, configure message templates (email HTML, SMS, push),
    or stream events to Kinesis Data Streams or Firehose-to-S3. Do NOT
    invoke for Amazon SES standalone (use ses skills), Amazon SNS (use
    sns skills), or AWS Activate messaging.
---

# Pinpoint Segment Deployer

An AWS CloudOps agent skill that provisions Amazon Pinpoint segments,
journeys, campaigns, and channels with engagement-best-practice
defaults. The skill is segment-first: segments define WHO is reached
(dynamic segments recompute on every evaluation; static segments are
imported and pinned), journeys define the multi-branch state machine
(event-conditional splits, multivariate splits, wait, send), campaigns
define the scheduled or event-triggered delivery, and channels define
the transport (email, SMS, push, voice). The skill captures topology
and targeting decisions, explains why each default matters, surfaces
the three expert heuristics (dynamic vs static recompute, journey
event-conditional branching, A/B test sample size), and emits a
READY_TO_DEPLOY checklist with copy-pasteable verification commands.

## Activation keywords

create Pinpoint segment, dynamic segment, static segment, segment
dimensions, Pinpoint journey, conditional split journey, multivariate
journey, A/B test sample size, SMS sender ID, long code, toll-free
number, 10DLC, APNs push setup, FCM push setup, Pinpoint event stream
Kinesis, Pinpoint event stream S3, message template, quiet time,
frequency cap, holdout, event-triggered campaign.

## STRICT output contract

When this skill is invoked with a Pinpoint-provisioning request
(create a project, build a segment, design a journey, configure a
channel, set up an A/B test, wire an event stream, or a partial
configuration), the agent MUST respond with the READY_TO_DEPLOY
checklist defined in the "Output format" section using the literal
all-caps labels `PINPOINT_SEGMENT:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels
breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Project creation | New Pinpoint application |
| Step 2 — Segment model (dynamic vs static) | Core targeting decision |
| Step 3 — Segment dimensions | Demographic, Behavior, UserAttributes, Device |
| Step 4 — Channels (email, SMS, push, voice) | Transport prerequisites |
| Step 5 — Message templates (HTML/SMS/push) | Content personalization |
| Step 6 — Campaigns (scheduled vs event-triggered) | Delivery model |
| Step 7 — A/B testing, holdout, sample size | Experiment design |
| Step 8 — Quiet time and frequency caps | Compliance |
| Step 9 — Journeys (conditional/multivariate/wait) | Multi-branch state machine |
| Step 10 — Event streaming (Kinesis / Firehose / S3) | Telemetry |
| Step 11 — SMS number types | Sender ID vs long code vs toll-free vs short code |
| Step 12 — Push setup (APNs, FCM) | Mobile push credentials |
| Step 13 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/segments-and-dimensions.md | Segment dimension detail |
| references/journeys-and-ab-testing.md | Journey + A/B detail |

## Mindset

**One-line takeaway:** A Pinpoint deployment is segment-first. Dynamic
segments recompute on every campaign/journey evaluation (endpoints
enter and exit as attributes change); static segments are imported and
pinned. Journeys are DAGs of activities (ENTRY, SEND, WAIT,
CONDITIONAL_SPLIT, MULTIVARIATE_SPLIT, RANDOM_SPLIT, CONTROL, END)
where every path MUST reach END. A/B tests must have a defensible
sample size; underpowered experiments produce noise.

Three misconceptions dominate Pinpoint misdesign at provisioning time:

- **"A segment is a static list of endpoint IDs."** It is not. A
  segment is a *dimension-based query* (Demographics, Behavior,
  UserAttributes, Device attributes, recency) that dynamically resolves
  to endpoints at evaluation time. The endpoint set can change between
  campaign sends without any segment update. Imported (CSV/S3)
  segments are the exception — they ARE static and pinned. Confusing
  the two produces "I added a user but the campaign didn't reach them"
  tickets.

- **"A journey is a linear email drip."** It is not. A journey is a
  directed acyclic graph (DAG) of activities. The
  `CONDITIONAL_SPLIT` activity evaluates an event or attribute and
  routes endpoints down the YES or NO branch. `MULTIVARIATE_SPLIT`
  splits by percentage across A/B/C/... branches. `WAIT` can be
  time-based OR event-based (wait until the endpoint performs a
  specific event, with an optional timeout). Misusing these activities
  produces journeys that trap endpoints in open states or skip the
  control group.

- **"Any A/B test is fine if the percentages add up."** They must add
  up, but the SAMPLE SIZE must also be large enough to detect the
  minimum detectable effect (MDE). An A/B test on 1,000 endpoints with
  a 1% expected lift is underpowered — the result is noise. The skill
  surfaces a sample-size heuristic (rule-of-thumb: ≥10,000 endpoints
  per treatment for sub-1% MDE; ≥1,000 for 5%+ MDE) before emitting
  the create-campaign CLI.

## Configuration dependency graph (novel heuristic)

Pinpoint configurations are NOT independent. The project must exist
before channels; channels must be verified before campaigns; segments
must resolve to >0 endpoints before they target anyone; journeys must
be a DAG. Use this graph to sequence provisioning.

| Configuration | Hard dependencies (silent failure without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Project (application) | None (root container) | application-id is immutable once created | channels, segments, campaigns, journeys, event stream |
| Email channel | SES verified identity in the same region | campaign created before email channel enabled sends 0 messages silently (COMPLETED with 0 sends) | email campaigns, email templates |
| SMS channel | Origination number (sender ID, long code, toll-free, short code, 10DLC) | campaign sends 0 SMS silently if no origination; US 10DLC requires campaign registry | SMS campaigns, SMS templates, voice |
| Push channel (iOS) | APNs .p8 token key, Key ID, Team ID, Bundle ID | invalid credentials produce silent push failures (delivery status not surfaced in Pinpoint real-time) | push campaigns, push templates |
| Push channel (Android) | FCM API key (legacy) or service account JSON | legacy FCM key deprecation; prefer service account | push campaigns, push templates |
| Voice channel | Origination number (same pool as SMS) | voice messages require spend limit set | voice campaigns |
| Segment (dynamic) | Project exists; dimensions defined | re-evaluates on every campaign send; endpoint set can change | targeting for campaigns and journeys |
| Segment (static/imported) | Project exists; S3 object or CSV import job complete | pinned at import time; does NOT auto-refresh | targeting for one-off or snapshot-based campaigns |
| Template | Project exists; Liquid syntax valid; channel format matches | parse failures block campaign creation | campaign message content |
| Campaign (scheduled) | Channel enabled; segment resolves >0; template valid; schedule in future | Start time in the past = error; quiet time needs StartTime+EndTime+TimeZone | sends at scheduled time |
| Campaign (event-triggered) | Event recorded; campaign trigger criteria; segment optional | event must match exactly (event name + attributes) | sends when event fires |
| Journey | Project exists; at least one ENTRY; all paths reach END; no cycles | activity graph is validated at create; missing END = error | multi-step orchestrated engagement |
| Event stream | Kinesis stream or Firehose delivery stream exists; IAM role with kinesis:PutRecord / firehose:PutRecordBatch | one active event stream per project (replace, not append) | telemetry to Kinesis/S3/Redshift |

**The dynamic-segment-recompute row is the one a baseline model
misses.** A model that treats segments as static lists will not flag
when a segment that resolved to 100K endpoints at design time resolves
to 80K at send time because users aged out of the Behavior dimension.
The procedure below forces an explicit decision on segment type
(dynamic vs static) and verification of `get-segment-estimate` at
multiple points.

**Cross-dependency gotchas:**
- A campaign created BEFORE its channel is enabled sends 0 messages
  silently. The campaign shows COMPLETED with 0 sends — no error.
- A segment that resolves to 0 endpoints reaches no one. Always
  verify via `get-segment-estimate` before wiring into a campaign or
  journey.
- A journey is rejected at create-time if any activity is missing
  `NextActivity` or if no END activity exists. Validate the DAG first.
- US SMS via long code requires 10DLC campaign registration (per-
  brand, per-campaign). Toll-free numbers require verification.
  Sender IDs are not supported in the US.

## Expert heuristic: dynamic segment recompute vs static

A baseline model says "create the segment." The correct heuristic
recognizes that dynamic and static segments behave fundamentally
differently at send time.

```text
Dynamic segment (Dimensions: Behavior last 7 days)
  Created at T0 → resolves to 100,000 endpoints
  Campaign fires at T0+7d
  At T0+7d, segment re-evaluates:
    ├── Some T0 endpoints no longer match (no Behavior event in last 7d) → dropped
    ├── New endpoints now match (performed Behavior event in last 7d) → added
    └── Send count ≠ 100,000 (could be higher or lower)

Static segment (imported CSV, snapshot at T0)
  Imported at T0 → resolves to 100,000 endpoint IDs (pinned)
  Campaign fires at T0+7d
  At T0+7d, segment is STILL those exact 100,000 endpoint IDs
    └── Send count = 100,000 (or fewer if endpoints were deleted)
```

**Key implication:** use dynamic segments when targeting criteria
should track user state (e.g., "active in last 7 days"); use static
segments for one-off or snapshot-based campaigns (e.g., "everyone who
purchased on Black Friday"). Re-verify `get-segment-estimate` close to
send time for dynamic segments.

## Expert heuristic: journey event-conditional branching

The `CONDITIONAL_SPLIT` activity evaluates an event (or attribute)
and routes endpoints down the YES or NO branch. A baseline model
treats this as a simple if/else. The correct heuristic recognizes
three failure modes:

```text
CONDITIONAL_SPLIT
  Type: CONDITIONAL_SPLIT
  Condition:
    Event: "Purchase"
    Attributes: { "category": "electronics" }
    WaitTime: 7 days (how long to wait for the event)
  YES (event occurred): → Send "Thanks for your purchase" email
  NO (event did not occur within WaitTime): → Send "Still interested?" email

Failure modes:
  1. Missing WaitTime → endpoint waits forever for an event that
     never comes (open journey state)
  2. Condition too narrow (e.g., requires exact attribute match on
     a high-cardinality field) → almost all endpoints route NO
  3. Condition too broad (e.g., event name only, no attribute filter)
     → almost all endpoints route YES
```

**Key implication:** always set a `WaitTime` (also called `Wait` /
`evaluateLater` depending on UI) on event-conditional splits so
endpoints are not trapped. Verify branch percentages via journey
execution metrics post-launch.

## Expert heuristic: A/B test sample size

A baseline model says "split 50/50." The correct heuristic recognizes
that sample size must support the minimum detectable effect (MDE).

```text
Rule of thumb (rough power-analysis at α=0.05, β=0.20):
  ├── MDE 1% or less  → ≥10,000 endpoints per treatment
  ├── MDE 2-3%        → ≥5,000 endpoints per treatment
  ├── MDE 5% or more  → ≥1,000 endpoints per treatment
  └── MDE 10%+        → ≥300 endpoints per treatment

If the segment resolves to fewer endpoints than the rule requires:
  ├── Reduce the number of treatments (combine A/B/C into A/B)
  ├── Increase the MDE you commit to detect
  └── Hold out a smaller control group (or none — accept reduced significance)
```

**Key implication:** A/B tests with underpowered sample sizes produce
noise, not signal. The skill surfaces the rule of thumb before
emitting the create-campaign CLI. If the segment is too small, the
skill recommends reducing treatments or accepting a higher MDE.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Pinpoint project (application-id) | All resources are children of a project | `aws pinpoint get-app --application-id <id>` |
| Channel enabled (for the target channel) | Campaign without a verified channel sends 0 silently | Email: `aws sesv2 get-email-identity`; SMS: `aws pinpoint-sms-voice describe-phone-numbers`; Push: `aws pinpoint get-apns-channel` / `get-gcm-channel` |
| Segment resolves to >0 endpoints | A 0-endpoint segment reaches no one | `aws pinpoint get-segment-estimate --application-id <id> --segment-id <seg>` |
| Template parses (Liquid valid, channel matches) | Parse failures block campaign creation | `aws pinpoint get-message-template --template-name <name>` |
| Schedule in the future (or IMMEDIATE) | Past start time = error | Compare to current time |
| Quiet time complete (StartTime, EndTime, TimeZone) | Missing fields = error | All three fields present |
| Frequency cap ≥ 1 (if set) | Cap of 0 blocks all sends | Confirm N/day per endpoint |
| A/B test percentages sum to 100 (with holdout) | Otherwise create-campaign errors | Sum treatments + holdout |
| Journey is a DAG (no cycles, all paths reach END) | Otherwise create-journey errors | Validate activity graph |
| IAM permissions | Operator needs create-campaign, create-journey, create-segment, channel update | `aws iam get-role-policy` or check attached policies |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Project creation

A Pinpoint project (also called an "application" or "app") is the
container for all channels, segments, campaigns, journeys, and
templates.

```bash
PROJECT_ID=$(aws pinpoint create-app \
  --create-application-request Name=my-pinpoint-project \
  --query 'ApplicationResponse.Id' --output text)

echo "Project: $PROJECT_ID"
```

Verify:

```bash
aws pinpoint get-app --application-id "$PROJECT_ID"
```

## Step 2 — Segment model (dynamic vs static)

The single most important targeting decision: dynamic or static.

| Segment type | Definition | Updates | Use case |
|---|---|---|---|
| Dynamic (Dimensions) | Defined by Demographic, Behavior, UserAttributes, Device, or recency criteria | Recomputes on every evaluation (campaign send, journey entry) | "Active in last 7 days", "US mobile users", "high-LTV" |
| Static (Imported) | Imported endpoint IDs from CSV or S3 | Pinned at import; does NOT auto-refresh | "Black Friday purchasers", "Churned users Q3" |

**Dynamic segment (with dimensions):**

```bash
SEGMENT_ID=$(aws pinpoint create-segment \
  --application-id "$PROJECT_ID" \
  --write-segment-request '{
    "Name": "active-us-mobile-7d",
    "SegmentGroups": {
      "Groups": [{
        "Dimensions": [
          {
            "Demographic": {
              "Channel": {"DimensionType": "INCLUSIVE", "Values": ["GCM","APNS"]}
            }
          },
          {
            "Behavior": {
              "Recency": {"Duration": "DAY_7", "RecencyType": "ACTIVE"}
            }
          },
          {
            "Demographic": {
              "AppVersion": {"DimensionType": "INCLUSIVE", "Values": ["1.2.0"]}
            }
          }
        ],
        "SourceSegments": [],
        "SourceType": "ALL",
        "Type": "ANY"
      }],
      "Include": "ALL"
    }
  }' \
  --query 'SegmentResponse.Id' --output text)
```

**Static segment (imported from S3):**

```bash
# Define the import job (one-time snapshot)
aws pinpoint create-import-job \
  --application-id "$PROJECT_ID" \
  --import-job-request '{
    "DefineSegment": true,
    "ExternalId": "black-friday-2025",
    "Format": "CSV",
    "RegisterEndpoints": true,
    "RoleArn": "arn:aws:iam::123456789012:role/PinpointImportRole",
    "S3Url": "s3://my-bucket/segments/black-friday.csv",
    "SegmentId": "'"${STATIC_SEGMENT_ID}"'",
    "SegmentName": "black-friday-2025-purchasers"
  }'
```

Verify resolution:

```bash
aws pinpoint get-segment-estimate \
  --application-id "$PROJECT_ID" \
  --segment-id "$SEGMENT_ID" \
  --query 'SegmentResponse'
```

## Step 3 — Segment dimensions

Dimensions define dynamic-segment criteria. Each dimension is a
filter on a specific endpoint attribute.

| Dimension | Filter target | Example values |
|---|---|---|
| Demographic | Channel, AppVersion, DeviceType, Make, Model, Platform | `Channel=GCM`, `DeviceType=ios` |
| Behavior | Recency (ACTIVE/INACTIVE) + Duration (DAY_7, DAY_30) | `Recency=DAY_7 ACTIVE` |
| UserAttributes | Custom user-level attributes (key-value) | `loyalty_tier=gold` |
| Attributes | Custom endpoint-level attributes (key-value) | `last_viewed_category=electronics` |
| Location | Country, Region, PostalCode, GPS | `Country=US` |
| Metrics | Aggregate metrics (e.g., session count, total revenue) | `session_count > 5` |

**Dimension operators:**
- `INCLUSIVE` — endpoint matches if attribute is in the values list.
- `EXCLUSIVE` — endpoint matches if attribute is NOT in the values
  list.
- `CONTAINS` — substring match (string attributes only).

**Composition:**
- `SourceType: ALL` — endpoint must match ALL dimensions.
- `SourceType: ANY` — endpoint matches if ANY dimension matches.
- `Include: ALL` (top level) — endpoint must match all groups.
- `Include: ANY` (top level) — endpoint matches if any group matches.

**Common mistake:** using `ANY` when `ALL` is intended. "Users in US
OR DeviceType=iOS" matches every iOS user globally; "Users in US AND
DeviceType=iOS" matches only US iOS users.

## Step 4 — Channels (email, SMS, push, voice)

Each channel has prerequisites. Channels MUST be configured before
campaigns/journeys that use them.

| Channel | Prerequisite | Verify |
|---|---|---|
| Email | SES verified identity (domain or email) in same region | `aws sesv2 get-email-identity --email-identity <domain>` |
| SMS | Origination number (sender ID, long code, toll-free, short code, 10DLC) | `aws pinpoint-sms-voice describe-phone-numbers` |
| Push (iOS) | APNs `.p8` token key, Key ID, Team ID, Bundle ID | `aws pinpoint get-apns-channel --application-id <id>` |
| Push (Android) | FCM API key or service account JSON | `aws pinpoint get-gcm-channel --application-id <id>` |
| Voice | Origination number (same pool as SMS) | `aws pinpoint-sms-voice describe-phone-numbers` |

**Email channel:**

```bash
aws pinpoint update-email-channel \
  --application-id "$PROJECT_ID" \
  --email-channel-request FromAddress="no-reply@example.com",
    Identity="arn:aws:ses:us-east-1:123456789012:identity/example.com",
    RoleArn="arn:aws:iam::123456789012:role/PinpointEmailRole"
```

**SMS channel:**

```bash
aws pinpoint update-sms-channel \
  --application-id "$PROJECT_ID" \
  --sms-channel-request ShortCode="+15551234567"
```

**APNs channel (iOS):**

```bash
aws pinpoint update-apns-channel \
  --application-id "$PROJECT_ID" \
  --apns-channel-request '{
    "BundleId": "com.example.app",
    "Certificate": "",
    "PrivateKey": "",
    "DefaultAuthenticationMethod": "TOKEN",
    "TokenKey": "-----BEGIN PRIVATE KEY-----\nMIG...-----END PRIVATE KEY-----",
    "KeyId": "ABC123DEFG",
    "TeamId": "TEAM123456"
  }'
```

**GCM channel (Android, FCM):**

```bash
aws pinpoint update-gcm-channel \
  --application-id "$PROJECT_ID" \
  --gcm-channel-request ApiKey="AAAAxxxx...",DefaultAuthenticationMethod="GCM"
```

## Step 5 — Message templates (email HTML/SMS/push)

Templates use Liquid personalization: `{{UserAttributes.X}}`,
`{{Attributes.X}}`, `{{Metrics.X}}`.

**Email template (HTML):**

```bash
aws pinpoint create-email-template \
  --email-template-request '{
    "Subject": "Welcome, {{UserAttributes.first_name}}!",
    "HtmlPart": "<html><body><h1>Hello {{UserAttributes.first_name}}</h1><p>Your code is {{Attributes.otp_code}}.</p></body></html>",
    "TextPart": "Welcome {{UserAttributes.first_name}}! Your code is {{Attributes.otp_code}}."
  }' \
  --template-name welcome-email
```

**SMS template:**

```bash
aws pinpoint create-sms-template \
  --sms-template-request '{
    "Body": "Hi {{UserAttributes.first_name}}, your order {{Attributes.order_id}} shipped!"
  }' \
  --template-name order-shipped-sms
```

**Push template (APNS + GCM JSON):**

```bash
aws pinpoint create-push-template \
  --push-template-request '{
    "APNS": "{\"aps\":{\"alert\":{\"title\":\"{{Attributes.title}}\",\"body\":\"{{Attributes.body}}\"}}}",
    "GCM": "{\"notification\":{\"title\":\"{{Attributes.title}}\",\"body\":\"{{Attributes.body}}\"}}"
  }' \
  --template-name promo-push
```

## Step 6 — Campaigns (scheduled vs event-triggered)

Campaigns deliver a message template to a segment via a channel, on a
schedule or triggered by an event.

**Scheduled campaign:**

```bash
aws pinpoint create-campaign \
  --application-id "$PROJECT_ID" \
  --write-campaign-request '{
    "Name": "weekly-promo",
    "SegmentId": "'"${SEGMENT_ID}"'",
    "MessageConfiguration": {"EmailConfig": {"TemplateInformation": {"Name": "welcome-email"}}},
    "Schedule": {
      "StartTime": "2026-09-01T13:00:00Z",
      "Frequency": "WEEKLY",
      "IsLocalTime": false
    },
    "HoldoutPercent": 10,
    "QuietTime": {"Start": "22:00", "End": "08:00", "TimeZone": "America/Los_Angeles"}
  }'
```

**Event-triggered campaign (Behavior trigger):**

```bash
aws pinpoint create-campaign \
  --application-id "$PROJECT_ID" \
  --write-campaign-request '{
    "Name": "cart-abandonment",
    "SegmentId": "'"${SEGMENT_ID}"'",
    "MessageConfiguration": {"EmailConfig": {"TemplateInformation": {"Name": "cart-abandonment-email"}}},
    "Schedule": {
      "StartTime": "IMMEDIATE",
      "EventFilter": {
        "Dimensions": {"Event": {"EventType": {"DimensionType": "INCLUSIVE", "Values": ["cart_abandoned"]}}},
        "FilterType": "ENDPOINT"
      }
    }
  }'
```

**Verify:**

```bash
aws pinpoint get-campaign --application-id "$PROJECT_ID" --campaign-id <campaign-id>
```

## Step 7 — A/B testing, holdout, sample size

A/B tests use `AdditionalTreatments` (additional message configs) and
`HoldoutPercent` (control group). Treatment percentages + holdout
must sum to 100.

```bash
aws pinpoint create-campaign \
  --application-id "$PROJECT_ID" \
  --write-campaign-request '{
    "Name": "subject-line-ab",
    "SegmentId": "'"${SEGMENT_ID}"'",
    "HoldoutPercent": 20,
    "MessageConfiguration": {
      "EmailConfig": {"TemplateInformation": {"Name": "subject-a"}}
    },
    "AdditionalTreatments": [
      {"Id": "treatment-b", "MessageConfiguration": {"EmailConfig": {"TemplateInformation": {"Name": "subject-b"}}}, "SizePercent": 40, "State": {"CampaignStatus": "SCHEDULED"}},
      {"Id": "treatment-c", "MessageConfiguration": {"EmailConfig": {"TemplateInformation": {"Name": "subject-c"}}}, "SizePercent": 20, "State": {"CampaignStatus": "SCHEDULED"}}
    ]
  }'
```

Percentages: holdout 20 + default 20 + treatment-b 40 + treatment-c
20 = 100.

**Sample-size gate (apply before emitting create-campaign):**
- Verify segment size via `get-segment-estimate`.
- If MDE ≤ 1%: require ≥10,000 endpoints per treatment. If fewer,
  reduce treatments or accept higher MDE.
- If MDE 2-5%: require ≥1,000 endpoints per treatment.
- If segment size is below threshold for the stated MDE, emit
  PREREQUISITES_MISSING with a recommendation.

## Step 8 — Quiet time and frequency caps

**Quiet time** (per-campaign): do not send between `StartTime` and
`EndTime` in `TimeZone`. Messages queued during quiet time are held
until the window ends.

**Frequency cap** (project-wide): max N messages per endpoint per
channel per day, and/or across all channels. Set at project level.

```bash
aws pinpoint update-apns-channel ... # (channel config)

# Frequency cap is part of the application settings
aws pinpoint put-event-stream ... # (event stream, separate concept)

# Configure via ApplicationSettings (frequency cap is set here)
aws pinpoint update-application-settings \
  --application-id "$PROJECT_ID" \
  --write-application-settings-request '{
    "Limits": {
      "Daily": 3,
      "Total": 10,
      "MessagesPerSecond": 50
    },
    "QuietTime": {"End": "08:00", "Start": "22:00"}
  }'
```

Frequency cap of 0 blocks ALL sends. Always verify ≥ 1.

## Step 9 — Journeys (conditional/multivariate/wait)

Journeys are DAGs of activities. Each activity has a `Type` and a
`NextActivity` (except END). Types:

| Type | Purpose | Branches |
|---|---|---|
| ENTRY | Journey entry condition (event-based or segment-based) | → NextActivity |
| SEND | Send a message on a channel | → NextActivity |
| WAIT | Wait for a duration or until an event | → NextActivity (or event-conditional) |
| CONDITIONAL_SPLIT | Yes/No branch on event or attribute | → YES branch / NO branch |
| MULTIVARIATE_SPLIT | Percentage-based A/B/C/... branches | → N branches |
| RANDOM_SPLIT | Equal percentage split | → N branches |
| CONTROL | Holds endpoint out of messaging (holdout) | → NextActivity |
| END | Terminal | (none) |

**Journey (with conditional split, multivariate split, wait):**

```bash
aws pinpoint create-journey \
  --application-id "$PROJECT_ID" \
  --write-journey-request '{
    "Name": "onboarding-7d",
    "StateMachine": {
      "StartActivity": "entry-activity",
      "Activities": {
        "entry-activity": {
          "ENTRY": {},
          "NextActivity": "send-welcome"
        },
        "send-welcome": {
          "SEND": {"MessageConfig": {"EmailConfig": {"TemplateInformation": {"Name": "welcome-email"}}}},
          "NextActivity": "wait-3d"
        },
        "wait-3d": {
          "WAIT": {"WaitTime": {"WaitFor": "PT3D"}},
          "NextActivity": "purchase-split"
        },
        "purchase-split": {
          "CONDITIONAL_SPLIT": {
            "Condition": {
              "Conditions": [{
                "EventCondition": {
                  "Dimensions": {"Event": {"EventType": {"DimensionType": "INCLUSIVE", "Values": ["purchase"]}}},
                  "MessageActivity": "purchase-thanks"
                }
              }],
              "Operator": "ALL"
            },
            "FalseActivity": "still-interested",
            "TrueActivity": "purchase-thanks"
          }
        },
        "purchase-thanks": {
          "SEND": {"MessageConfig": {"EmailConfig": {"TemplateInformation": {"Name": "thanks-email"}}}},
          "NextActivity": "end"
        },
        "still-interested": {
          "MULTIVARIATE_SPLIT": {
            "Branches": [
              {"Percentage": 50, "NextActivity": "discount-email"},
              {"Percentage": 50, "NextActivity": "nudge-email"}
            ]
          }
        },
        "discount-email": {
          "SEND": {"MessageConfig": {"EmailConfig": {"TemplateInformation": {"Name": "discount-email"}}}},
          "NextActivity": "end"
        },
        "nudge-email": {
          "SEND": {"MessageConfig": {"EmailConfig": {"TemplateInformation": {"Name": "nudge-email"}}}},
          "NextActivity": "end"
        },
        "end": {"END": {}}
      }
    }
  }'
```

**Verify:**

```bash
aws pinpoint get-journey --application-id "$PROJECT_ID" --journey-id <journey-id>
aws pinpoint get-journey-execution-metrics --application-id "$PROJECT_ID" --journey-id <journey-id>
```

## Step 10 — Event streaming (Kinesis / Firehose / S3)

Pinpoint emits engagement events (sends, opens, clicks, custom
events) to a single active event stream per project. Targets:

- **Kinesis Data Streams** — real-time processing (Lambda consumers,
  analytics).
- **Kinesis Data Firehose** — batched delivery to S3 (with optional
  Lambda transform), Redshift, OpenSearch.

```bash
aws pinpoint put-event-stream \
  --application-id "$PROJECT_ID" \
  --write-event-stream '{
    "DestinationStreamArn": "arn:aws:kinesis:us-east-1:123456789012:stream/pinpoint-events",
    "RoleArn": "arn:aws:iam::123456789012:role/PinpointKinesisRole"
  }'
```

**IAM role (Pinpoint → Kinesis):**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["kinesis:PutRecord", "kinesis:PutRecords"],
      "Resource": "arn:aws:kinesis:us-east-1:123456789012:stream/pinpoint-events"
    }
  ]
}
```

Trust policy allows `pinpoint.amazonaws.com`.

**Firehose-to-S3 alternative:**

```bash
# Create Firehose delivery stream to S3 first
aws firehose create-delivery-stream ... --s3-destination-configuration ...

# Then point Pinpoint at the Firehose stream
aws pinpoint put-event-stream \
  --application-id "$PROJECT_ID" \
  --write-event-stream '{
    "DestinationStreamArn": "arn:aws:firehose:us-east-1:123456789012:deliverystream/pinpoint-to-s3",
    "RoleArn": "arn:aws:iam::123456789012:role/PinpointFirehoseRole"
  }'
```

**One active event stream per project** — calling `put-event-stream`
on a project with an existing stream replaces it.

## Step 11 — SMS number types

| Number type | Format | Countries | Notes |
|---|---|---|---|
| Sender ID | Alphanumeric (11 chars) | Supported countries (UK, EU, APAC) | NOT supported in US; pre-registration required in some countries |
| Long code (DID) | Standard phone number | US, CA, UK, etc. | US = 10DLC; requires campaign registry |
| Toll-free | +1 8xx | US, CA | Requires verification |
| Short code | 5-6 digits | US, CA | High throughput; expensive; lengthy provisioning |

**Sender ID (alphanumeric):**

```bash
aws pinpoint update-sms-channel \
  --application-id "$PROJECT_ID" \
  --sms-channel-request ShortCode="MyBrand"
```

**Long code (10DLC) — US:**

```bash
# Request a long code
aws pinpoint-sms-voice request-phone-number \
  --iso-country-code US \
  --message-type TRANSACTIONAL \
  --number-capabilities '[{"Inbound": true, "Outbound": true}]'

# 10DLC registration (per-brand, per-campaign) required before sending
# Use the Pinpoint SMS Voice API or AWS End User Messaging SMS
```

**Toll-free:**

```bash
# Verify the toll-free number before sending
aws pinpoint-sms-voice describe-phone-numbers
```

**Common mistake:** using a sender ID in the US. Sender IDs are not
supported in the US. Use a long code (10DLC), toll-free, or short
code instead.

## Step 12 — Push setup (APNs, FCM)

**APNs (iOS) — token-based authentication (recommended):**

Requires:
- `.p8` private key file (downloaded from Apple Developer portal).
- Key ID (10-character identifier).
- Team ID (10-character identifier).
- Bundle ID (app's iOS bundle identifier).

```bash
aws pinpoint update-apns-channel \
  --application-id "$PROJECT_ID" \
  --apns-channel-request '{
    "BundleId": "com.example.app",
    "DefaultAuthenticationMethod": "TOKEN",
    "TokenKey": "'"$(cat AuthKey_ABC123DEFG.p8 | tr "\n" " " | sed "s/ /\\\n/g")"'",
    "KeyId": "ABC123DEFG",
    "TeamId": "TEAM123456"
  }'
```

**FCM (Android) — API key or service account:**

```bash
# Legacy API key (deprecated path)
aws pinpoint update-gcm-channel \
  --application-id "$PROJECT_ID" \
  --gcm-channel-request ApiKey="AAAAxxxx..."

# Preferred: service account JSON (modern FCM v1)
# Convert the service account JSON to the format expected by Pinpoint
```

**Verify:**

```bash
aws pinpoint get-apns-channel --application-id "$PROJECT_ID"
aws pinpoint get-gcm-channel --application-id "$PROJECT_ID"
```

## Step 13 — Recent features

**Recent AWS features (2023-2026):**

- **Journey dynamic entry (2023-2024):** Journeys can now re-evaluate
  entry conditions for dynamic segments on a schedule, allowing
  endpoints to enter mid-journey as they match the segment.

- **ML-powered segment recommendations (2023-2024):** Pinpoint can
  suggest lookalike audiences based on engagement patterns, expanding
  segments to similar endpoints.

- **In-app messaging (2023-2024):** Native in-app message layouts
  (BOTTOM_BANNER, TOP_BANNER, OVERLAYS, CAROUSEL) via the mobile SDK.

- **AWS End User Messaging SMS (2024-2026):** The next-generation SMS
  service with simplified 10DLC campaign registration, lower per-
  message pricing, and improved throughput. Pinpoint SMS APIs are
  being consolidated into AWS End User Messaging SMS.

- **Journey multi-branch advanced conditions (2024-2025):** Enhanced
  CONDITIONAL_SPLIT with compound conditions (multiple events /
  attributes), enabling finer-grained routing without nesting
  multiple splits.

- **Template versioning (2024-2025):** Message templates support
  versioning, enabling rollback to previous template versions without
  re-creating the template.

## NEVER do these things

1. **NEVER create a campaign before its channel is enabled.** A
   campaign created before the channel is enabled sends 0 messages
   silently (COMPLETED with 0 sends). Always verify the channel first.

2. **NEVER ship a segment that resolves to 0 endpoints.** Always
   verify via `get-segment-estimate` before wiring the segment into a
   campaign or journey. A 0-endpoint segment reaches no one.

3. **NEVER use a sender ID for US SMS.** Sender IDs are not supported
   in the US. Use a long code (10DLC, with campaign registry), toll-
   free (with verification), or short code instead.

4. **NEVER ship an A/B test without a sample-size check.** An A/B
   test on fewer than ~1,000 endpoints per treatment (for 5%+ MDE)
   is underpowered — the result is noise. Reduce treatments or
   accept a higher MDE.

5. **NEVER build a journey with an open path.** Every activity must
   have a `NextActivity` (except END). Every path must reach END.
   Open activities trap endpoints in journey limbo.

6. **NEVER build a CONDITIONAL_SPLIT without a WaitTime on the
   event condition.** Without a WaitTime, endpoints wait forever
   for an event that may never come. Always set the timeout.

7. **NEVER set a frequency cap of 0.** Cap of 0 blocks ALL sends.
   Always verify the cap is ≥ 1 (or unset).

8. **NEVER assume a dynamic segment resolves to the same endpoint
   count at send time as at design time.** Dynamic segments
   recompute on every evaluation. Re-verify `get-segment-estimate`
   close to send time for dynamic segments.

9. **NEVER use the same template for two A/B treatments.** Each
   treatment MUST have a distinct template (or distinct template
   version). Identical templates produce identical results — the
   test measures noise.

10. **NEVER attempt to create a second event stream on a project.**
    One active event stream per project — calling `put-event-stream`
    replaces the existing stream, silently changing the destination.

## Output format

```text
PINPOINT_SEGMENT: <project-id>/<segment-id> (<type>, <count> endpoints)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Project: <application-id> (<name>)
  [✓|✗] Segment: <segment-id> — <dynamic|static> (<count> endpoints)
  [✓|✗] Segment type: Dynamic (recompute on eval) | Static (imported snapshot)
  [✓|✗] Dimensions: <Demographic/Behavior/UserAttributes/...>
  [✓|✗] Channel: <email|sms|push|voice|multi> — <verified|not verified>
  [✓|✗] Template: <name> (Liquid valid, channel matches)
  [✓|✗] Schedule: immediate | <ISO time> <freq>
  [✓|✗] Quiet time: <start-end TZ> | none
  [✓|✗] Frequency cap: <N/day per channel>, <N/day total> | none
  [✓|✗] A/B test: <holdout>% holdout + <treatments> (sum=100, sample-size OK)
  [✓|✗] Journey: <name> (DAG, all paths reach END)
  [✓|✗] Event stream: <kinesis | firehose-to-s3> | none
  [✓|✗] SMS number: <sender ID | long code | toll-free | short code>
  [✓|✗] Push: APNs (<token|cert>), FCM (<api key|service account>)
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws pinpoint get-app --application-id <application-id>
  aws pinpoint get-segment-estimate --application-id <application-id> --segment-id <segment-id>
  aws pinpoint get-campaign --application-id <application-id> --campaign-id <campaign-id>
  aws pinpoint get-journey --application-id <application-id> --journey-id <journey-id>
  aws pinpoint get-event-stream --application-id <application-id>
```

### Worked example — dynamic segment with conditional-split journey

```text
PINPOINT_SEGMENT: app-abc123/seg-def456 (dynamic, 42500 endpoints)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Project: app-abc123 (my-pinpoint-project)
  [✓] Segment: seg-def456 — dynamic (42,500 endpoints)
  [✓] Segment type: Dynamic (recompute on eval)
  [✓] Dimensions: Behavior(DAY_7 ACTIVE) + Demographic(Channel=GCM,APNS) + UserAttributes(loyalty_tier=gold)
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

## Error handling

### Campaign sends 0 messages despite COMPLETED status
- Channel was not enabled before the campaign ran. Verify the channel
  (email SES identity, SMS origination, APNs/FCM credentials) and re-
  enable. Re-run the campaign or schedule a new send.

### Segment resolves to 0 endpoints
- Dimensions are too narrow, or endpoints are missing the attributes
  the dimensions filter on. Verify dimension types (INCLUSIVE vs
  EXCLUSIVE), SourceType (ALL vs ANY), and that endpoints have the
  required attributes. Re-run `get-segment-estimate` after fixes.

### Journey creation fails with "invalid state machine"
- The activity graph is not a DAG. Verify every activity (except END)
  has a `NextActivity`. Verify at least one END exists. Verify
  CONDITIONAL_SPLIT has both `TrueActivity` and `FalseActivity`.

### Conditional-split endpoints stuck in waiting
- The event condition has no `WaitTime` (or `evaluateLater`). Set a
  finite wait time so endpoints time out and route to the NO branch.

### A/B test produces noise (no significant winner)
- Sample size is below the threshold for the MDE. Either increase
  the segment, reduce the number of treatments, or accept a higher
  MDE.

### SMS messages not delivered in the US
- Sender ID used in the US (not supported). Use 10DLC (with campaign
  registry), toll-free (with verification), or short code. Verify
  origination via `aws pinpoint-sms-voice describe-phone-numbers`.

### Push notifications silently fail
- APNs credentials invalid (wrong Key ID, Team ID, or expired token
  key). FCM API key deprecated (use service account). Verify via
  `get-apns-channel` and `get-gcm-channel`.

### Event stream replacement
- `put-event-stream` on a project with an existing stream REPLACES
  the destination. Verify the existing stream before calling put.

## Domain

AWS CloudOps / Amazon Pinpoint Customer Engagement Provisioning —
Segments, Journeys, Campaigns, Channels, Templates, and Event
Streaming.

## AWS documentation

- **Amazon Pinpoint Developer Guide** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/welcome.html
- **Creating segments** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/segments.html
- **Segment dimensions (Demographic, Behavior, UserAttributes)** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/segments-building.html
- **Importing segments (S3/CSV)** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/segments-importing.html
- **Creating journeys** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/journeys.html
- **Journey activities (CONDITIONAL_SPLIT, MULTIVARIATE_SPLIT, WAIT)** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/journeys-activities.html
- **Campaigns (scheduled, event-triggered)** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/campaigns.html
- **A/B testing and holdout** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/campaigns-ab-testing.html
- **Message templates** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/templates.html
- **Email channel (SES)** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/channels-email.html
- **SMS channel** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/channels-sms.html
- **Push channel (APNs, FCM)** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/channels-mobile-push.html
- **Voice channel** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/channels-voice.html
- **SMS and voice settings (sender ID, long codes, toll-free)** — https://docs.aws.amazon.com/pinpoint/latest/userguide/channels-sms-managing.html
- **Event streams (Kinesis, Firehose)** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/event-streams.html
- **Quiet time and frequency caps** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/settings-general.html
- **Pinpoint API reference** — https://docs.aws.amazon.com/pinpoint/latest/apireference/welcome.html
- **AWS End User Messaging SMS** — https://docs.aws.amazon.com/sms-voice/latest/userguide/what-is-sms-voice.html
