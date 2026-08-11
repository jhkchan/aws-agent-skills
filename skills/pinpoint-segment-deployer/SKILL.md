---
name: pinpoint-segment-deployer
description: >-
  Provisions Amazon Pinpoint projects, segments, campaigns, journeys, and
  channels with production defaults. Segment-first model: dynamic segments
  (Dimensions: Demographic, Behavior, UserAttributes, Device, recency)
  recompute on every evaluation; static segments are imported (CSV/S3) and
  pinned. Campaigns are scheduled or event-triggered. Channels: email (SES
  verified identity), SMS (sender ID, long code, toll-free, 10DLC), push
  (APNs .p8 token, FCM API key), voice. Templates: email (HTML + Liquid),
  SMS, push. A/B testing with AdditionalTreatments and holdout percentage
  (sum to 100). Quiet time and project-wide frequency caps. Event
  streaming to Kinesis or Firehose-to-S3. Journeys: ENTRY,
  CONDITIONAL_SPLIT (yes-no on event/attribute), MULTIVARIATE_SPLIT,
  RANDOM_SPLIT, WAIT (time or event), CONTROL, SEND, END — DAG. SMS number
  types: sender ID (per-country), long code (DID/10DLC US), toll-free,
  short code. Emits READY_TO_DEPLOY with verification commands. Use when
  creating a Pinpoint project, building a dynamic or static segment,
  designing a multi-branch journey with event-conditional splits,
  configuring A/B tests with sample-size justification, setting up SMS
  with sender ID or long codes, wiring GCM/APNs push, or streaming events
  to Kinesis/S3.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). For live deployment: AWS CLI v2 with pinpoint access (and
  sesv2 for email identity, pinpoint-sms-voice for origination numbers).
  Works with Terraform aws_pinpoint_app, aws_pinpoint_segment,
  aws_pinpoint_campaign, aws_pinpoint_journey, aws_pinpoint_event_stream
  resources and CloudFormation AWS::Pinpoint::* templates.
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
  - ab test
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
    conditional or multivariate splits, configure an A/B test with
    sample-size justification, set up SMS with sender ID / long code /
    toll-free / 10DLC, configure APNs or FCM push channels, build
    scheduled or event-triggered campaigns, apply quiet time and
    frequency caps, configure message templates, or stream events to
    Kinesis or Firehose-to-S3. Do NOT invoke for Amazon SES standalone,
    Amazon SNS, or AWS Activate messaging.
---

# Pinpoint Segment Deployer

An AWS CloudOps agent skill that provisions Amazon Pinpoint segments,
journeys, campaigns, and channels with engagement-best-practice
defaults. Segment-first: segments define WHO is reached (dynamic
segments recompute on every evaluation; static segments are imported
and pinned), journeys define the multi-branch state machine (event-
conditional splits, multivariate splits, wait, send), campaigns
define the scheduled or event-triggered delivery, channels define
the transport. The skill captures targeting decisions, surfaces the
three expert heuristics (dynamic vs static recompute, journey event-
conditional branching, A/B test sample size), and emits a
READY_TO_DEPLOY checklist with verification commands.

## Activation keywords

create Pinpoint segment, dynamic segment, static segment, segment
dimensions, Pinpoint journey, conditional split journey,
multivariate journey, A/B test sample size, SMS sender ID, long
code, toll-free number, 10DLC, APNs push setup, FCM push setup,
Pinpoint event stream Kinesis, Pinpoint event stream S3, message
template, quiet time, frequency cap, holdout, event-triggered
campaign.

## STRICT output contract

When invoked with a Pinpoint-provisioning request, the agent MUST
respond with the READY_TO_DEPLOY checklist defined in the "Output
format" section using the literal all-caps labels
`PINPOINT_SEGMENT:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface with prose, headings, or
disclaimers — emit the block first. This contract is what
assertion-based evals and downstream pipelines rely on; deviating
breaks automation silently.

If any prerequisite is missing, the verdict is
`PREREQUISITES_MISSING` with a specific gap citation (marked
`[✗]`), and `READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Project creation | New Pinpoint application |
| Step 2 — Segment model (dynamic vs static) | Core targeting decision |
| Step 3 — Segment dimensions | Demographic, Behavior, UserAttributes, Device |
| Step 4 — Channels | Transport prerequisites |
| Step 5 — Templates | Content personalization |
| Step 6 — Campaigns | Scheduled vs event-triggered delivery |
| Step 7 — A/B testing, holdout, sample size | Experiment design |
| Step 8 — Quiet time and frequency caps | Compliance |
| Step 9 — Journeys | Multi-branch state machine |
| Step 10 — Event streaming | Telemetry |
| Step 11 — SMS number types | Sender ID vs long code vs toll-free |
| Step 12 — Push setup (APNs, FCM) | Mobile push credentials |
| Step 13 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/segments-and-dimensions.md | Segment dimension detail |
| references/journeys-and-ab-testing.md | Journey + A/B detail |

## Mindset

**One-line takeaway:** A Pinpoint deployment is segment-first.
Dynamic segments recompute on every campaign/journey evaluation
(endpoints enter and exit as attributes change); static segments
are imported and pinned. Journeys are DAGs of activities (ENTRY,
SEND, WAIT, CONDITIONAL_SPLIT, MULTIVARIATE_SPLIT, RANDOM_SPLIT,
CONTROL, END) where every path MUST reach END. A/B tests must have
a defensible sample size; underpowered experiments produce noise.

Three misconceptions dominate Pinpoint misdesign:

- **"A segment is a static list of endpoint IDs."** It is not. A
  segment is a dimension-based query that dynamically resolves at
  evaluation time. The endpoint set can change between sends
  without any segment update. Imported (CSV/S3) segments ARE
  static. Confusing the two produces "I added a user but the
  campaign didn't reach them" tickets.

- **"A journey is a linear email drip."** It is not. A journey is
  a directed acyclic graph. `CONDITIONAL_SPLIT` evaluates an event
  or attribute and routes endpoints down the YES or NO branch.
  `MULTIVARIATE_SPLIT` splits by percentage across branches. `WAIT`
  can be time-based OR event-based (wait until the endpoint
  performs a specific event, with an optional timeout). Misusing
  these activities produces journeys that trap endpoints in open
  states or skip the control group.

- **"Any A/B test is fine if the percentages add up."** They must
  add up, but the SAMPLE SIZE must also support the minimum
  detectable effect (MDE). An A/B test on 1,000 endpoints with a
  1% expected lift is underpowered — the result is noise. The
  skill surfaces a sample-size heuristic before emitting the
  create-campaign CLI.

## Configuration dependency graph

Pinpoint configurations are NOT independent. Project before
channels; channels verified before campaigns; segments must
resolve to >0 endpoints; journeys must be a DAG.

| Configuration | Hard dependencies (silent failure without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Project | None (root) | application-id immutable once created | channels, segments, campaigns, journeys, event stream |
| Email channel | SES verified identity in same region | campaign created before channel enabled sends 0 silently (COMPLETED, 0 sends) | email campaigns |
| SMS channel | Origination number (sender ID/long code/toll-free/short code/10DLC) | 0 SMS sent silently if no origination; US 10DLC requires campaign registry | SMS campaigns, voice |
| Push (iOS) | APNs .p8 token key, Key ID, Team ID, Bundle ID | invalid credentials = silent push failures | push campaigns |
| Push (Android) | FCM API key or service account JSON | legacy FCM key deprecation; prefer service account | push campaigns |
| Voice | Origination number (same pool as SMS) | spend limit required | voice campaigns |
| Segment (dynamic) | Project; dimensions defined | re-evaluates on every send; endpoint set changes | targeting |
| Segment (static) | Project; S3/CSV import job complete | pinned at import; does NOT auto-refresh | targeting |
| Template | Project; Liquid valid; channel matches | parse failures block campaign creation | message content |
| Campaign (scheduled) | Channel enabled; segment >0; template valid; schedule in future | past start = error; quiet time needs all 3 fields | sends at scheduled time |
| Campaign (event-triggered) | Event recorded; trigger criteria; segment optional | event must match exactly (name + attributes) | sends on event |
| Journey | Project; ≥1 ENTRY; all paths reach END; no cycles | activity graph validated at create | orchestrated engagement |
| Event stream | Kinesis or Firehose exists; IAM role with PutRecord/PutRecordBatch | ONE active stream per project (replace, not append) | telemetry |

**The dynamic-segment-recompute row is the one a baseline model
misses.** A model that treats segments as static lists will not
flag when a segment that resolved to 100K at design time resolves
to 80K at send time because users aged out of the Behavior
dimension. The procedure below forces an explicit decision on
segment type and verification of `get-segment-estimate`.

**Cross-dependency gotchas:**
- A campaign created BEFORE its channel is enabled sends 0 messages
  silently. The campaign shows COMPLETED with 0 sends — no error.
- A segment that resolves to 0 endpoints reaches no one. Verify
  via `get-segment-estimate` before wiring.
- A journey is rejected at create-time if any activity is missing
  `NextActivity` or no END exists.
- US SMS via long code requires 10DLC campaign registration.
  Sender IDs are not supported in the US.

## Expert heuristic: dynamic segment recompute vs static

A baseline model says "create the segment." The correct heuristic
recognizes that dynamic and static segments behave differently at
send time.

```text
Dynamic segment (Behavior DAY_7) — created at T0, resolves to 100K
  Campaign fires at T0+7d → segment re-evaluates at send time:
    ├── T0 endpoints no longer matching (dropped)
    ├── New endpoints now matching (added)
    └── Send count ≠ 100K (could be higher or lower)

Static segment (imported CSV snapshot at T0)
  Campaign fires at T0+7d → segment is STILL those exact 100K IDs
    └── Send count = 100K (or fewer if endpoints deleted)
```

**Key implication:** use dynamic segments when criteria should
track user state ("active in last 7 days"); use static for one-off
or snapshot-based campaigns ("Black Friday purchasers"). Re-verify
`get-segment-estimate` close to send time for dynamic segments.

## Expert heuristic: journey event-conditional branching

The `CONDITIONAL_SPLIT` activity evaluates an event (or attribute)
and routes endpoints down YES or NO. A baseline model treats this
as simple if/else. The correct heuristic recognizes three failure
modes:

```text
CONDITIONAL_SPLIT
  Condition: Event "Purchase", Attributes {category: "electronics"}
  WaitTime: 7 days (how long to wait for the event)
  YES (event occurred) → Send "Thanks" email
  NO (event did not occur within WaitTime) → Send "Still interested?"

Failure modes:
  1. Missing WaitTime → endpoint waits forever (open journey state)
  2. Condition too narrow (exact match on high-cardinality field) → ~all route NO
  3. Condition too broad (event name only) → ~all route YES
```

**Key implication:** always set a `WaitTime` on event-conditional
splits so endpoints are not trapped. Verify branch percentages via
journey execution metrics post-launch.

## Expert heuristic: A/B test sample size

A baseline model says "split 50/50." The correct heuristic
recognizes that sample size must support the MDE.

```text
Rule of thumb (α=0.05, β=0.20):
  ├── MDE 1% or less  → ≥10,000 endpoints per treatment
  ├── MDE 2-3%        → ≥5,000 endpoints per treatment
  ├── MDE 5% or more  → ≥1,000 endpoints per treatment
  └── MDE 10%+        → ≥300 endpoints per treatment

If segment too small for the stated MDE:
  ├── Reduce treatments (combine A/B/C into A/B)
  ├── Increase the MDE you commit to detect
  └── Hold out a smaller control (or none — reduced significance)
```

**Key implication:** A/B tests with underpowered sample sizes
produce noise, not signal. The skill surfaces the rule of thumb
before emitting create-campaign.

## Prerequisites (verify before provisioning)

| Prerequisite | Why | How to verify |
|---|---|---|
| Pinpoint project (application-id) | All resources are children of a project | `aws pinpoint get-app --application-id <id>` |
| Channel enabled | Campaign without verified channel sends 0 silently | Email: `sesv2 get-email-identity`; SMS: `pinpoint-sms-voice describe-phone-numbers`; Push: `pinpoint get-apns-channel` / `get-gcm-channel` |
| Segment resolves >0 | 0-endpoint segment reaches no one | `pinpoint get-segment-estimate` |
| Template parses | Parse failures block campaign creation | `pinpoint get-message-template` |
| Schedule in future (or IMMEDIATE) | Past start = error | Compare to current time |
| Quiet time complete | Missing fields = error | StartTime + EndTime + TimeZone all present |
| Frequency cap ≥ 1 | Cap of 0 blocks all sends | Confirm N/day per endpoint |
| A/B test sums to 100 (with holdout) | Otherwise create-campaign errors | Sum treatments + holdout |
| Journey is DAG (no cycles, all paths reach END) | Otherwise create-journey errors | Validate activity graph |
| IAM permissions | Operator needs create-campaign, create-journey, create-segment, channel update | Check attached policies |

If any prerequisite is missing, output
`VERDICT: PREREQUISITES_MISSING` and cite the specific gap.

## Step 1 — Project creation

A Pinpoint project (application) is the container for all
channels, segments, campaigns, journeys, and templates.

```bash
PROJECT_ID=$(aws pinpoint create-app \
  --create-application-request Name=my-pinpoint-project \
  --query 'ApplicationResponse.Id' --output text)
aws pinpoint get-app --application-id "$PROJECT_ID"
```

## Step 2 — Segment model (dynamic vs static)

| Type | Definition | Updates | Use case |
|---|---|---|---|
| Dynamic | Dimensions (Demographic, Behavior, UserAttributes, Device, recency) | Recomputes on every evaluation | "Active in last 7 days" |
| Static (Imported) | Imported endpoint IDs from CSV/S3 | Pinned at import; does NOT auto-refresh | "Black Friday purchasers" |

**Dynamic segment:**

```bash
SEGMENT_ID=$(aws pinpoint create-segment \
  --application-id "$PROJECT_ID" \
  --write-segment-request '{
    "Name": "active-mobile-7d",
    "SegmentGroups": {"Groups": [{"Dimensions": [
      {"Behavior": {"Recency": {"Duration": "DAY_7", "RecencyType": "ACTIVE"}}},
      {"Demographic": {"Channel": {"DimensionType": "INCLUSIVE", "Values": ["GCM","APNS"]}}}
    ], "SourceType": "ALL", "Type": "ANY"}], "Include": "ALL"}
  }' --query 'SegmentResponse.Id' --output text)
```

**Static segment (S3 import):**

```bash
aws pinpoint create-import-job --application-id "$PROJECT_ID" \
  --import-job-request '{"DefineSegment": true, "Format": "CSV",
    "RoleArn": "arn:aws:iam::123456789012:role/PinpointImportRole",
    "S3Url": "s3://my-bucket/segments/snapshot.csv",
    "SegmentName": "snapshot-purchasers"}'
```

Verify resolution: `aws pinpoint get-segment-estimate
--application-id "$PROJECT_ID" --segment-id "$SEGMENT_ID"`. See
`references/segments-and-dimensions.md` for the full dimension
model (operators, composition, Metrics, Location).

## Step 3 — Segment dimensions

| Dimension | Filter target | Example |
|---|---|---|
| Demographic | Channel, AppVersion, DeviceType, Make, Model, Platform | `Channel=GCM` |
| Behavior | Recency (ACTIVE/INACTIVE) + Duration (DAY_7, DAY_30) | `Recency=DAY_7 ACTIVE` |
| UserAttributes | Custom user-level (key-value) | `loyalty_tier=gold` |
| Attributes | Custom endpoint-level (key-value) | `last_viewed=electronics` |
| Location | Country, Region, PostalCode, City | `Country=US` |
| Metrics | Aggregate metrics (numeric) | `session_count > 5` |

Operators: `INCLUSIVE` (in list), `EXCLUSIVE` (not in list),
`CONTAINS` (substring), plus date/numeric operators.

Composition: `SourceType: ALL` (AND across dimensions) vs `ANY`
(OR); top-level `Include: ALL` vs `ANY` (across groups). **Common
mistake:** using `ANY` when `ALL` is intended. "US OR iOS" matches
every iOS user globally; "US AND iOS" matches only US iOS users.

## Step 4 — Channels

Each channel has prerequisites. Channels MUST be configured before
campaigns/journeys that use them.

| Channel | Prerequisite | Verify |
|---|---|---|
| Email | SES verified identity (same region) | `aws sesv2 get-email-identity --email-identity <domain>` |
| SMS | Origination number | `aws pinpoint-sms-voice describe-phone-numbers` |
| Push (iOS) | APNs .p8 token key, Key ID, Team ID, Bundle ID | `aws pinpoint get-apns-channel` |
| Push (Android) | FCM API key or service account | `aws pinpoint get-gcm-channel` |
| Voice | Origination number | `aws pinpoint-sms-voice describe-phone-numbers` |

```bash
# Email channel
aws pinpoint update-email-channel --application-id "$PROJECT_ID" \
  --email-channel-request FromAddress="no-reply@example.com",
    Identity="arn:aws:ses:us-east-1:123456789012:identity/example.com"

# SMS channel (long code)
aws pinpoint update-sms-channel --application-id "$PROJECT_ID" \
  --sms-channel-request ShortCode="+15551234567"
```

## Step 5 — Message templates

Templates use Liquid: `{{UserAttributes.X}}`, `{{Attributes.X}}`,
`{{Metrics.X}}`.

```bash
# Email (HTML + Liquid)
aws pinpoint create-email-template --template-name welcome-email \
  --email-template-request '{"Subject": "Welcome, {{UserAttributes.first_name}}!",
    "HtmlPart": "<html><body><h1>Hello {{UserAttributes.first_name}}</h1><p>Code: {{Attributes.otp_code}}</p></body></html>",
    "TextPart": "Welcome {{UserAttributes.first_name}}! Code: {{Attributes.otp_code}}."}'

# SMS
aws pinpoint create-sms-template --template-name otp-sms \
  --sms-template-request '{"Body": "Hi {{UserAttributes.first_name}}, code {{Attributes.otp_code}}"}'

# Push (APNS + GCM JSON)
aws pinpoint create-push-template --template-name promo-push \
  --push-template-request '{"APNS": "{\"aps\":{\"alert\":{\"title\":\"{{Attributes.title}}\"}}}","GCM": "{\"notification\":{\"title\":\"{{Attributes.title}}\"}}"}'
```

## Step 6 — Campaigns (scheduled vs event-triggered)

```bash
# Scheduled campaign
aws pinpoint create-campaign --application-id "$PROJECT_ID" \
  --write-campaign-request '{
    "Name": "weekly-promo",
    "SegmentId": "'"${SEGMENT_ID}"'",
    "MessageConfiguration": {"EmailConfig": {"TemplateInformation": {"Name": "welcome-email"}}},
    "Schedule": {"StartTime": "2026-09-01T13:00:00Z", "Frequency": "WEEKLY"},
    "HoldoutPercent": 10,
    "QuietTime": {"Start": "22:00", "End": "08:00", "TimeZone": "America/Los_Angeles"}}'

# Event-triggered campaign
aws pinpoint create-campaign --application-id "$PROJECT_ID" \
  --write-campaign-request '{
    "Name": "cart-abandonment",
    "SegmentId": "'"${SEGMENT_ID}"'",
    "MessageConfiguration": {"EmailConfig": {"TemplateInformation": {"Name": "cart-abandonment-email"}}},
    "Schedule": {"StartTime": "IMMEDIATE",
      "EventFilter": {"Dimensions": {"Event": {"EventType": {"DimensionType": "INCLUSIVE", "Values": ["cart_abandoned"]}}}, "FilterType": "ENDPOINT"}}}'
```

Verify: `aws pinpoint get-campaign --application-id "$PROJECT_ID"
--campaign-id <id>`.

## Step 7 — A/B testing, holdout, sample size

A/B tests use `AdditionalTreatments` + `HoldoutPercent`. Default
treatment share is the remainder: `100 - holdout -
sum(AdditionalTreatments.SizePercent)`. Each treatment MUST have a
distinct template.

```bash
aws pinpoint create-campaign --application-id "$PROJECT_ID" \
  --write-campaign-request '{
    "Name": "subject-line-ab",
    "SegmentId": "'"${SEGMENT_ID}"'",
    "HoldoutPercent": 20,
    "MessageConfiguration": {"EmailConfig": {"TemplateInformation": {"Name": "subject-a"}}},
    "AdditionalTreatments": [
      {"Id": "treatment-b", "SizePercent": 40, "MessageConfiguration": {"EmailConfig": {"TemplateInformation": {"Name": "subject-b"}}}},
      {"Id": "treatment-c", "SizePercent": 20, "MessageConfiguration": {"EmailConfig": {"TemplateInformation": {"Name": "subject-c"}}}}
    ]}'
# Math: holdout 20 + b 40 + c 20 = 80; default (subject-a) = 100 - 80 = 20. Sum = 100. Valid.
```

**Sample-size gate (apply before emitting create-campaign):**
verify segment size via `get-segment-estimate`. MDE ≤ 1% requires
≥10,000 per treatment; 2-3% requires ≥5,000; 5%+ requires ≥1,000.
If below threshold, emit `PREREQUISITES_MISSING` with a
recommendation.

## Step 8 — Quiet time and frequency caps

**Quiet time** (per-campaign or project-wide): no sends between
StartTime and EndTime in TimeZone. Messages queued during quiet
time are held until the window ends.

**Frequency cap** (project-wide via ApplicationSettings): max N
messages per endpoint per channel per day, and/or across all
channels.

```bash
aws pinpoint update-application-settings \
  --application-id "$PROJECT_ID" \
  --write-application-settings-request '{
    "Limits": {"Daily": 3, "Total": 10, "MessagesPerSecond": 50},
    "QuietTime": {"End": "08:00", "Start": "22:00"}}'
```

Frequency cap of 0 blocks ALL sends. Always verify ≥ 1.

## Step 9 — Journeys (conditional/multivariate/wait)

Journeys are DAGs of activities. Types: ENTRY, SEND, WAIT,
CONDITIONAL_SPLIT (yes/no), MULTIVARIATE_SPLIT (percentage A/B/C),
RANDOM_SPLIT (equal), CONTROL (holdout), END. Every path must
reach END. CONDITIONAL_SPLIT needs both `TrueActivity` and
`FalseActivity`; event conditions need a `WaitTime` (put a WAIT
activity before the split to gate the evaluation window).

```bash
aws pinpoint create-journey --application-id "$PROJECT_ID" \
  --write-journey-request '{
    "Name": "onboarding-7d",
    "StateMachine": {"StartActivity": "entry-activity", "Activities": {
      "entry-activity": {"ENTRY": {}, "NextActivity": "send-welcome"},
      "send-welcome": {"SEND": {"MessageConfig": {"EmailConfig": {"TemplateInformation": {"Name": "welcome-email"}}}}, "NextActivity": "wait-3d"},
      "wait-3d": {"WAIT": {"WaitTime": {"WaitFor": "PT3D"}}, "NextActivity": "purchase-split"},
      "purchase-split": {"CONDITIONAL_SPLIT": {
        "Condition": {"Conditions": [{"EventCondition": {"Dimensions": {"Event": {"EventType": {"DimensionType": "INCLUSIVE", "Values": ["purchase"]}}}, "MessageActivity": "purchase-thanks"}}], "Operator": "ALL"},
        "FalseActivity": "still-interested", "TrueActivity": "purchase-thanks"}},
      "purchase-thanks": {"SEND": {"MessageConfig": {"EmailConfig": {"TemplateInformation": {"Name": "thanks-email"}}}}, "NextActivity": "end"},
      "still-interested": {"MULTIVARIATE_SPLIT": {"Branches": [
        {"Percentage": 50, "NextActivity": "discount-email"},
        {"Percentage": 50, "NextActivity": "nudge-email"}]}},
      "discount-email": {"SEND": {"MessageConfig": {"EmailConfig": {"TemplateInformation": {"Name": "discount-email"}}}}, "NextActivity": "end"},
      "nudge-email": {"SEND": {"MessageConfig": {"EmailConfig": {"TemplateInformation": {"Name": "nudge-email"}}}}, "NextActivity": "end"},
      "end": {"END": {}}}}}'
```

Verify: `aws pinpoint get-journey` and
`get-journey-execution-metrics`. See
`references/journeys-and-ab-testing.md` for DAG validation rules,
the WaitTime failure modes, and MULTIVARIATE_SPLIT branch math.

## Step 10 — Event streaming (Kinesis / Firehose / S3)

Pinpoint emits engagement events (sends, opens, clicks, custom) to
a single active event stream per project. Targets: Kinesis Data
Streams (real-time), Kinesis Firehose (batched to S3/Redshift).

```bash
aws pinpoint put-event-stream --application-id "$PROJECT_ID" \
  --write-event-stream '{
    "DestinationStreamArn": "arn:aws:kinesis:us-east-1:123456789012:stream/pinpoint-events",
    "RoleArn": "arn:aws:iam::123456789012:role/PinpointKinesisRole"}'
```

IAM role needs `kinesis:PutRecord` (or `firehose:PutRecordBatch`)
with trust policy allowing `pinpoint.amazonaws.com`. **One active
stream per project** — calling `put-event-stream` replaces the
existing destination.

## Step 11 — SMS number types

| Type | Format | Countries | Notes |
|---|---|---|---|
| Sender ID | Alphanumeric (11 chars) | UK, EU, APAC (supported countries) | NOT supported in US; pre-registration in some countries |
| Long code (DID) | Standard phone number | US, CA, UK, etc. | US = 10DLC; requires campaign registry |
| Toll-free | +1 8xx | US, CA | Requires verification |
| Short code | 5-6 digits | US, CA | High throughput; expensive; lengthy provisioning |

```bash
# Sender ID (where supported — NOT US)
aws pinpoint update-sms-channel --application-id "$PROJECT_ID" \
  --sms-channel-request ShortCode="MyBrand"

# Long code (US 10DLC — requires campaign registry)
aws pinpoint-sms-voice request-phone-number \
  --iso-country-code US --message-type TRANSACTIONAL \
  --number-capabilities '[{"Inbound": true, "Outbound": true}]'
```

**Common mistake:** using a sender ID in the US. Not supported.
Use long code (10DLC), toll-free, or short code instead.

## Step 12 — Push setup (APNs, FCM)

**APNs (token-based, recommended):** requires `.p8` private key,
Key ID (10-char), Team ID (10-char), Bundle ID.

```bash
aws pinpoint update-apns-channel --application-id "$PROJECT_ID" \
  --apns-channel-request '{
    "BundleId": "com.example.app",
    "DefaultAuthenticationMethod": "TOKEN",
    "TokenKey": "'"$(cat AuthKey_ABC123DEFG.p8)"'",
    "KeyId": "ABC123DEFG", "TeamId": "TEAM123456"}'
```

**FCM:** API key (legacy, deprecated path) or service account JSON
(preferred).

```bash
aws pinpoint update-gcm-channel --application-id "$PROJECT_ID" \
  --gcm-channel-request ApiKey="AAAAxxxx..."
```

## Step 13 — Recent features

- **Journey dynamic entry (2023-2024):** re-evaluates entry
  conditions for dynamic segments on a schedule.
- **ML-powered segment recommendations (2023-2024):** lookalike
  audiences based on engagement patterns.
- **In-app messaging (2023-2024):** BOTTOM_BANNER, TOP_BANNER,
  OVERLAYS, CAROUSEL via mobile SDK.
- **AWS End User Messaging SMS (2024-2026):** next-gen SMS with
  simplified 10DLC registration and lower per-message pricing;
  Pinpoint SMS APIs consolidating into this service.
- **Journey multi-branch advanced conditions (2024-2025):**
  compound conditions on CONDITIONAL_SPLIT.
- **Template versioning (2024-2025):** rollback to previous
  template versions without re-creating.

## NEVER do these things

1. **NEVER create a campaign before its channel is enabled.**
   Sends 0 silently (COMPLETED with 0 sends). Verify channel first.
2. **NEVER ship a segment that resolves to 0 endpoints.** Always
   verify via `get-segment-estimate`.
3. **NEVER use a sender ID for US SMS.** Not supported. Use long
   code (10DLC), toll-free, or short code.
4. **NEVER ship an A/B test without a sample-size check.** Below
   ~1,000 per treatment (5%+ MDE) is underpowered — noise.
5. **NEVER build a journey with an open path.** Every activity
   needs `NextActivity` (except END); every path must reach END.
6. **NEVER build a CONDITIONAL_SPLIT without a WaitTime on event
   conditions.** Endpoints wait forever for an event that may
   never come.
7. **NEVER set a frequency cap of 0.** Blocks ALL sends. Verify
   cap ≥ 1 (or unset).
8. **NEVER assume a dynamic segment resolves to the same count at
   send time as at design time.** Recomputes on every evaluation.
9. **NEVER use the same template for two A/B treatments.** Each
   MUST have a distinct template.
10. **NEVER attempt a second event stream on a project.** One
    active stream — `put-event-stream` replaces silently.

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

- **Campaign sends 0 despite COMPLETED:** channel not enabled
  before campaign ran. Verify channel and re-run.
- **Segment resolves to 0:** dimensions too narrow or endpoints
  missing the filtered attributes. Verify dimension types
  (INCLUSIVE vs EXCLUSIVE) and `SourceType` (ALL vs ANY).
- **Journey creation fails ("invalid state machine"):** activity
  graph not a DAG. Every activity (except END) needs `NextActivity`;
  at least one END must exist; CONDITIONAL_SPLIT needs both
  TrueActivity and FalseActivity.
- **Conditional-split endpoints stuck:** event condition has no
  WaitTime. Set a finite wait so endpoints time out to the NO
  branch.
- **A/B test produces noise:** sample size below MDE threshold.
  Increase segment, reduce treatments, or accept higher MDE.
- **SMS not delivered in US:** sender ID used in US (not
  supported). Use 10DLC (with registry), toll-free, or short code.
- **Push silently fails:** APNs credentials invalid or FCM API key
  deprecated. Verify via `get-apns-channel` / `get-gcm-channel`.
- **Event stream replaced:** `put-event-stream` on a project with
  an existing stream REPLACES the destination. Verify before put.

## Domain

AWS CloudOps / Amazon Pinpoint Customer Engagement Provisioning —
Segments, Journeys, Campaigns, Channels, Templates, Event
Streaming.

## AWS documentation

- **Amazon Pinpoint Developer Guide** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/welcome.html
- **Creating segments** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/segments.html
- **Segment dimensions** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/segments-building.html
- **Importing segments** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/segments-importing.html
- **Creating journeys** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/journeys.html
- **Journey activities** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/journeys-activities.html
- **Campaigns (scheduled, event-triggered)** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/campaigns.html
- **A/B testing and holdout** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/campaigns-ab-testing.html
- **Message templates** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/templates.html
- **Email channel (SES)** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/channels-email.html
- **SMS channel** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/channels-sms.html
- **Push channel (APNs, FCM)** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/channels-mobile-push.html
- **Voice channel** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/channels-voice.html
- **SMS and voice settings** — https://docs.aws.amazon.com/pinpoint/latest/userguide/channels-sms-managing.html
- **Event streams (Kinesis, Firehose)** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/event-streams.html
- **Quiet time and frequency caps** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/settings-general.html
- **Pinpoint API reference** — https://docs.aws.amazon.com/pinpoint/latest/apireference/welcome.html
- **AWS End User Messaging SMS** — https://docs.aws.amazon.com/sms-voice/latest/userguide/what-is-sms-voice.html
