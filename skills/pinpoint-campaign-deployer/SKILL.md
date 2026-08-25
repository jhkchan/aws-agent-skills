---
name: pinpoint-campaign-deployer
description: Provisions Amazon Pinpoint campaigns and engagement workflows — project creation, channels (email, SMS, push, voice), segments (demographic, dynamic, imported), campaigns (schedule, quiet time, A/B test holdout), message templates (email, SMS, push with Liquid), journeys (multi-step with wait, yes-no split, multivariate, random split), event streams (Kinesis), ML-powered segment recommendations, and in-app messaging. Runs deterministic pre-checks (SES verified identities, SMS origination numbers, APNs/FCM credentials, segment resolution, template validation, IAM permissions for Kinesis), emits create-campaign and create-journey CLIs behind a CONFIRM gate, verifies via get-campaign. Emits READY_TO_DEPLOY | PREREQUISITES_MISSING. Use when provisioning Pinpoint projects, building multi-step journeys, or setting up cross-channel campaigns.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline plan classification. Live-account operations use aws pinpoint create-app, update-email-channel, update-sms-channel, update-apns-channel, update-gcm-channel, create-segment, create-campaign, create-journey, create-message-template, put-event-stream (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: AppIntegration
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: pinpoint, appintegration, deploy, campaign, journey, segment, multi-channel, messaging, personalization
  dependencies: aws-orchestrator
  keywords: Pinpoint, campaign, journey, segment, email channel, SMS channel, push channel, voice channel, message template, A/B test, holdout, quiet time, multivariate, in-app messaging, event stream, Kinesis, ML recommendations, demographic segment, dynamic segment, imported segment
  when_to_use: Provisioning a new Pinpoint project, configuring channels (email, SMS, push, voice), creating segments (demographic, dynamic, imported), building campaigns with schedules and quiet time, setting up A/B tests, creating multi-step journeys (wait, yes-no, multivariate), deploying message templates, wiring Kinesis event streams, or enabling ML-powered segment recommendations and in-app messaging.
  activation_triggers: create Pinpoint project, provision Pinpoint campaign, Pinpoint journey, Pinpoint segment, Pinpoint email channel, Pinpoint SMS channel, Pinpoint push notification, Pinpoint message template, A/B test campaign, Pinpoint in-app messaging, Pinpoint event stream Kinesis, ML segment recommendations, multivariate journey, pinpoint create-campaign
  invocation_schema: 'Input: either (a) a campaign or journey deployment intent (create, update) with target project id, channel, segment, templates, schedule, journey activity graph, and event stream target; OR (b) a project id for live-account update or validation. Output: deterministic CAMPAIGN/ VERDICT/PRE_CHECKS/STEPS/POST_VERIFY block per operation, where VERDICT is one of READY_TO_DEPLOY, PREREQUISITES_MISSING.'
---

# Pinpoint Campaign Deployer

## What this skill does

Provisions Amazon Pinpoint projects, channels, segments, campaigns, journeys,
and message templates with engagement-best-practice defaults — email channel
requires SES verified identities, SMS channel requires origination numbers
with spend limits, push channel requires valid APNs/FCM credentials, segments
use dimension-based targeting (not raw endpoint IDs), campaigns enforce
quiet-time windows and frequency caps, journeys use the activity graph model
(wait, conditional split, multivariate, random split), and templates use
Liquid for personalization. Runs deterministic pre-checks before any
state-changing CLI, emits the exact `create-campaign` and `create-journey`
CLIs behind a CONFIRM gate, and verifies via `get-campaign` and
`get-journey`. Every plan surfaces the channel-prerequisite ordering rule,
the segment-resolution check, the quiet-time enforcement, and the journey
activity graph validation.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **Quick reference** | Verdict thresholds + pre-check priority order + channel matrix | Before any operation |
| **Mindset** | Why channel prerequisites matter; segment vs endpoint targeting; journey graph model | Understanding the deployment model |
| **Pre-flight** | Campaign gate — SES identity, SMS origination, APNs/FCM, segment resolution | Before executing any CLI |
| **Process** | Per-operation: project, channels, segments, templates, campaigns, journeys, event stream | When choosing which operation |
| **STRICT output contract** | Required CAMPAIGN/VERDICT/PRE_CHECKS/STEPS/POST_VERIFY block | Formatting the response |
| **NEVER (top 5)** | Hard rules that prevent broken or non-compliant patterns | Review before deploy |
| **Expert heuristic** | Choosing journey vs campaign and channel per use case | Engagement strategy |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `PREREQUISITES_MISSING` | Any pre-check failed (SES identity not verified, SMS origination missing, APNs/FCM invalid, segment resolves to 0 endpoints, template parse failure, schedule in the past, quiet-time with no timezone, frequency cap 0, IAM permission missing, project name collision) | List failures, do NOT execute |
| `READY_TO_DEPLOY` | All pre-checks passed; awaiting CONFIRM gate | Emit exact CLI sequence, wait for operator yes |

**Priority order for pre-checks (apply in sequence, all must pass):**

1. **Project existence** — `get-app` returns the target project or no collision.
2. **Channel prerequisites** — target channel is enabled and verified:
   - Email: SES identity (domain or email) is `verified` in the same region.
   - SMS: origination number provisioned, SMS channel enabled with spend limit.
   - Push: APNs `.p8` token key + key ID + team ID; FCM API key or service account.
   - Voice: origination number provisioned, voice channel enabled.
3. **Segment resolution** — segment resolves to >0 endpoints (verify via
   `get-segment-estimate`). A 0-endpoint segment sends nothing.
4. **Message template** — template parses (Liquid valid), channel matches.
5. **Schedule** — start time is in the future (or `IMMEDIATE`). Timezone set.
6. **Quiet time** — if set, `StartTime`, `EndTime`, and `TimeZone` all present.
7. **Frequency cap** — if set, must be >= 1. Cap of 0 blocks all sends.
8. **A/B test** — if `AdditionalTreatments` set, each has distinct template.
   Holdout percentage 0-100. Treatment percentages + holdout sum to 100.
9. **Journey activity graph** — no cycles, every non-END activity has valid
   `NextActivity`, at least one `END` exists.
10. **IAM permissions** — operator holds `pinpoint:CreateCampaign`,
    `CreateJourney`, `CreateSegment`, and channel-specific update permissions.

## Mindset

**One-line takeaway:** a Pinpoint campaign is not "an email blast" — it is a
**channel-prerequisite-ordered deployment** where the channel MUST be
configured and verified BEFORE the campaign or journey, the segment MUST
resolve to >0 endpoints, and the journey activity graph is a state machine
with no cycles.

Three facts make Pinpoint provisioning different from "send a message":

- **Channels must be enabled and verified before campaigns.** The email
  channel requires a verified SES identity. SMS requires a provisioned
  origination number. Push requires valid APNs/FCM credentials. A campaign
  created before the channel is enabled sends nothing — silently. No error;
  the campaign shows `COMPLETED` with 0 sends.

- **Segments use dimension-based targeting, not raw endpoint IDs.** A segment
  defines criteria (demographic, device, behavior, custom attributes) that
  dynamically resolve. Dynamic segments update as attributes change. Imported
  segments (CSV/S3) are static. A segment that resolves to 0 endpoints reaches
  no one — always verify via `get-segment-estimate`.

- **Journeys are state machines, not linear sequences.** The activity graph
  supports conditional splits, multivariate splits, random splits, wait
  activities (time or event), and send activities. MUST be a DAG (no cycles).
  Every path must reach END. An open activity leaves endpoints stuck.

## Quick reference — channel prerequisite matrix

| Channel | Prerequisite | Verification | Notes |
|---|---|---|---|
| Email | SES verified identity | `sesv2 get-email-identity` | Must be `SUCCESS` in same region |
| SMS | Origination number | `pinpoint-phone-number describe-phone-numbers` | Monthly spend limit |
| Push (iOS) | APNs token key | `pinpoint update-apns-channel` | `.p8`, key ID, team ID |
| Push (Android) | FCM API key | `pinpoint update-gcm-channel` | Legacy key or service account |
| Voice | Origination number | `pinpoint-phone-number describe-phone-numbers` | Same pool as SMS |

## Pre-flight: campaign deployment gate

**Live-account pre-flight checks (skip if offline architecture plan):**
1. Verify IAM permissions for `pinpoint:CreateApp`, `CreateCampaign`,
   `CreateJourney`, `CreateSegment`, channel update operations.
2. Verify project: `aws pinpoint get-app --application-id <id>`
3. Email: `aws sesv2 get-email-identity --email-identity <domain>`
4. SMS: `aws pinpoint-phone-number describe-phone-numbers`
5. Segment: `aws pinpoint get-segment-estimate --application-id <id> --segment-id <seg>`

**If the deployment spec is incomplete**, output:

```text
CAMPAIGN: <name-or-unknown>
VERDICT: PREREQUISITES_MISSING
REASON: Deployment specification is missing required fields (<list>).
REQUIRED:
  - project_id (existing Pinpoint project application-id)
  - channel (email | sms | push | voice)
  - segment_id (segment that resolves to >0 endpoints)
  - message (template or inline message body)
  - schedule (immediate or future start time)
```

## Process — Architecture planning (apply in order)

### Step 0: Expert knowledge — non-obvious behaviors

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#step-0-expert-knowledge--non-obvious-behaviors).
> Non-obvious behaviors: silent channel enablement, dynamic vs imported segments, S3 import role, quiet time, frequency caps, journey graph rules, in-app messaging, ML recommendations, event streams.

### Step 1: Project creation

```bash
aws pinpoint create-app \
  --create-application-request '{"Name":"prod-engagement","QuietTime":{"StartTime":"22:00","EndTime":"08:00","TimeZone":"America/New_York"}}'
```

### Step 2: Channel configuration

**Email:**
```bash
aws pinpoint update-email-channel \
  --application-id <id> \
  --email-channel-request '{"FromAddress":"noreply@example.com","Identity":"arn:aws:ses:us-east-1:111111111111:identity/example.com"}'
```

**SMS:**
```bash
aws pinpoint update-sms-channel \
  --application-id <id> \
  --sms-channel-request '{"ShortCode":"12345","SenderId":"MYBRAND"}'
```

**APNs (iOS):**
```bash
aws pinpoint update-apns-channel \
  --application-id <id> \
  --apns-channel-request '{"BundleId":"com.example.app","TeamId":"ABCDE12345","TokenKey":"-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----","TokenKeyId":"ABC1234567"}'
```

**FCM (Android):**
```bash
aws pinpoint update-gcm-channel \
  --application-id <id> \
  --gcm-channel-request '{"ApiKey":"AAAA..."}'
```

### Step 3: Segment creation

**Demographic:**
```bash
aws pinpoint create-segment \
  --application-id <id> \
  --write-segment-request '{"Name":"premium-ios","SegmentGroups":{"Groups":[{"Dimensions":[{"DeviceType":{"DimensionType":"IN","Values":["ios"]}},{"Attributes":{"tier":{"DimensionType":"IN","Values":["premium"]}}}],"SourceType":"ANY"}]}}'
```

**Imported (S3):**
```bash
aws pinpoint create-import-job \
  --application-id <id> \
  --import-job-request '{"DefineSegment":true,"SegmentName":"imported","Format":"CSV","RoleArn":"arn:aws:iam::111111111111:role/PinpointImport","S3Url":"s3://bucket/list.csv"}'
```

**Verify resolution:** `aws pinpoint get-segment-estimate --application-id <id> --segment-id <seg>`

### Step 4: Message templates

**Email:**
```bash
aws pinpoint create-email-template \
  --email-template-request '{"TemplateName":"welcome","Subject":"Welcome {{UserAttributes.FirstName}}","HtmlPart":"<h1>Hi {{UserAttributes.FirstName}}</h1>","TextPart":"Hi, welcome!"}'
```

**SMS:**
```bash
aws pinpoint create-sms-template \
  --sms-template-request '{"TemplateName":"otp","Body":"Your code: {{Attributes.code}}"}'
```

Liquid personalization: `{{UserAttributes.X}}`, `{{Attributes.X}}`, `{{Location.X}}`.

### Step 5: Campaign creation

```bash
aws pinpoint create-campaign \
  --application-id <id> \
  --write-campaign-request '{"Name":"weekly-promo","SegmentId":"seg-abc","MessageConfiguration":{"EmailTemplate":{"Name":"promo-email"}},"Schedule":{"StartTime":"2026-08-15T10:00:00","Frequency":"WEEKLY","QuietTime":{"StartTime":"22:00","EndTime":"08:00","TimeZone":"America/New_York"}},"IsEnabled":true}'
```

**A/B test:**
```json
{
  "Name": "ab-subject",
  "SegmentId": "seg-abc",
  "HoldoutPercent": 10,
  "AdditionalTreatments": [
    {"Id":"b","MessageConfiguration":{"EmailTemplate":{"Name":"subject-b"}},"SizePercent":45},
    {"Id":"c","MessageConfiguration":{"EmailTemplate":{"Name":"subject-c"}},"SizePercent":45}
  ],
  "MessageConfiguration": {"EmailTemplate": {"Name": "subject-a"}},
  "Schedule": {"StartTime": "IMMEDIATE"}
}
```

`HoldoutPercent` = control (receives nothing). Treatments split the rest.

### Step 6: Journey creation

```bash
aws pinpoint create-journey \
  --application-id <id> \
  --write-journey-request '{
    "Name":"onboarding",
    "Activities":{
      "entry":{"Type":"ENTRY","NextActivity":"send-welcome"},
      "send-welcome":{"Type":"SEND","MessageConfiguration":{"EmailTemplate":{"Name":"welcome"}},"NextActivity":"wait-1d"},
      "wait-1d":{"Type":"WAIT","WaitTime":{"WaitTime":"PT24H"},"NextActivity":"check"},
      "check":{"Type":"CONDITIONAL_SPLIT","Condition":{"Conditions":[{"EventCondition":{"Dimensions":[{"EventType":"app_open"}]}}]},"TrueActivity":"end","FalseActivity":"nudge"},
      "nudge":{"Type":"SEND","MessageConfiguration":{"EmailTemplate":{"Name":"nudge"}},"NextActivity":"end"},
      "end":{"Type":"END"}
    },
    "StartActivity":"entry",
    "State":"DRAFT"
  }'
```

**Journey activity types:**
| Type | Purpose | Required |
|---|---|---|
| `ENTRY` | Entry point | `NextActivity` |
| `SEND` | Send message | `MessageConfiguration`, `NextActivity` |
| `WAIT` | Wait (time/event) | `WaitTime` or `WaitUntil`, `NextActivity` |
| `CONDITIONAL_SPLIT` | Yes-no branch | `Condition`, `TrueActivity`, `FalseActivity` |
| `MULTIVARIATE_SPLIT` | A/B/C branch | `Branches` (sum to 100) |
| `RANDOM_SPLIT` | Random branch | `Branches` (sum to 100) |
| `END` | End | (none) |

**Validate:** no cycles (DAG), every non-END has `NextActivity`, at least one END.

### Step 7: Event stream

```bash
aws pinpoint put-event-stream \
  --application-id <id> \
  --write-event-stream '{"DestinationStreamArn":"arn:aws:kinesis:us-east-1:111111111111:stream/pinpoint-events","RoleArn":"arn:aws:iam::111111111111:role/PinpointStream"}'
```

Role MUST trust `pinpoint.amazonaws.com` and grant `kinesis:PutRecord`.

### Step 8: In-app messaging

```json
{
  "MessageConfiguration": {
    "InAppMessage": {
      "Content": [{"Header":"Welcome!","Body":"Complete your profile.","Buttons":[{"Text":"Start","Action":{"Type":"LINK","Link":"https://app.example.com/onboarding"}}]}],
      "Layout": "BOTTOM_BANNER"
    }
  }
}
```

## STRICT output contract

### Required output structure

Every response MUST begin with this block — no preamble:

```text
CAMPAIGN: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
TARGET: <name> (campaign-id: <id> for updates)
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. CONFIRM: About to <operation> campaign <name> in project <id> region <region>. This will <consequence>. Proceed? (yes/no)
  2. <exact CLI command — no placeholders>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
CHANNEL: <email | sms | push | voice | multi>
SEGMENT: <segment-id> (<type>, <count> endpoints)
TEMPLATE: <template-name> (<channel>)
SCHEDULE: <immediate | scheduled>
QUIET_TIME: <start-end TZ | none>
FREQUENCY_CAP: <N/day | none>
AB_TEST: <holdout% + treatments | none>
JOURNEY: <graph summary | none>
NOTES: <strategy, cost, deliverability caveats>
```

### FORBIDDEN output patterns

- NEVER start with "Let me analyze…" — the VERDICT block is the FIRST line.
- NEVER use lowercase verdict values — emit `READY_TO_DEPLOY` or
  `PREREQUISITES_MISSING`.
- NEVER omit PRE_CHECKS — every pre-check must appear with `[PASS]` or
  `[FAIL]` and a specific reason.
- NEVER emit placeholder values in a READY_TO_DEPLOY plan.
- NEVER omit the CONFIRM gate as the first STEPS entry.
- NEVER claim success without verifying campaign is ENABLED via
  `get-campaign`.
- NEVER change CLI step order — channel first, segment second, template
  third, campaign last.
- NEVER silently allow frequency cap of 0 — block with [FAIL].

### Perfect example output

```text
CAMPAIGN: weekly-newsletter
VERDICT: READY_TO_DEPLOY
TARGET: weekly-newsletter
PRE_CHECKS:
  - [PASS] Project app-abc123 exists
  - [PASS] Email channel enabled, SES identity example.com verified
  - [PASS] Segment seg-all resolves to 128450 endpoints
  - [PASS] Template newsletter parses, Liquid valid
  - [PASS] Schedule 2026-08-15T10:00:00 WEEKLY (future)
  - [PASS] Quiet time 22:00-08:00 America/New_York
  - [PASS] Frequency cap 5/day
  - [PASS] IAM principal holds pinpoint:CreateCampaign
STEPS:
  1. CONFIRM: About to create-campaign weekly-newsletter in project app-abc123 region us-east-1. SEND weekly email to 128450 endpoints starting 2026-08-15. Estimated cost: $12.85 (128450 x $0.0001). Proceed? (yes/no)
  2. aws pinpoint get-app --application-id app-abc123
  3. aws sesv2 get-email-identity --email-identity example.com
  4. aws pinpoint get-segment-estimate --application-id app-abc123 --segment-id seg-all
  5. aws pinpoint create-email-template --email-template-request '{"TemplateName":"newsletter","Subject":"Your weekly digest","HtmlPart":"...","TextPart":"..."}'
  6. aws pinpoint create-campaign --application-id app-abc123 --write-campaign-request '{"Name":"weekly-newsletter","SegmentId":"seg-all","MessageConfiguration":{"EmailTemplate":{"Name":"newsletter"}},"Schedule":{"StartTime":"2026-08-15T10:00:00","Frequency":"WEEKLY","QuietTime":{"StartTime":"22:00","EndTime":"08:00","TimeZone":"America/New_York"}},"IsEnabled":true}'
POST_VERIFY:
  - (pending execution)
  - get-campaign returns State=SCHEDULED or COMPLETED
CHANNEL: email
SEGMENT: seg-all (demographic, 128450 endpoints)
TEMPLATE: newsletter (email)
SCHEDULE: 2026-08-15T10:00:00 WEEKLY
QUIET_TIME: 22:00-08:00 America/New_York
FREQUENCY_CAP: 5/day
NOTES:
  - SES identity must remain verified.
  - Frequency cap 5/day is project-wide — concurrent campaigns may reduce reach.
```

## NEVER (top 5)

1. **NEVER create a campaign before verifying the channel is enabled.**
   Pinpoint silently accepts the campaign and produces zero sends — no error.
   The email channel requires a verified SES identity; SMS requires a
   provisioned origination number; push requires valid APNs/FCM credentials.
   Always pre-check via `get-email-channel`, `get-sms-channel`, etc.

2. **NEVER target a segment without verifying it resolves to >0 endpoints.**
   Overly-restrictive dimensions or stale attributes can resolve to zero —
   the campaign sends nothing. Always verify via `get-segment-estimate`.

3. **NEVER deploy a journey without validating the activity graph.** A cycle
   (infinite loop), open activity (no `NextActivity` on non-END), or no END
   activity leaves endpoints stuck or looping. Validate: DAG, all paths reach
   END, all referenced activities exist.

4. **NEVER set a frequency cap of 0.** A cap of 0 blocks ALL sends across the
   project. Pinpoint accepts it. Always set >= 1 or omit entirely.

5. **NEVER use quiet time without a timezone.** Without `TimeZone`, quiet time
   is ambiguous — Pinpoint may default to UTC, wrong for most audiences.

## Expert heuristic: choosing journey vs campaign and channel per use case

```
Engagement pattern
   ├─ One-time broadcast (announcement, newsletter)?
   │    └─ Campaign (scheduled or immediate)
   │         Channel: email (low cost) or SMS (high open rate)
   │
   ├─ Multi-step lifecycle (onboarding, win-back, drip)?
   │    └─ Journey (activity graph)
   │         Entry: event or segment-based
   │         Activities: SEND -> WAIT -> CONDITIONAL_SPLIT -> SEND -> END
   │         Channel: multi (email + push + in-app)
   │
   ├─ A/B test (subject line, send time, creative)?
   │    └─ Campaign with AdditionalTreatments
   │         Holdout: 10-20%, 2-5 variants
   │
   └─ Real-time transactional (OTP, receipt)?
        └─ Campaign triggered by event
             Channel: SMS (urgent) or email (receipt)
             No frequency cap
```

**Channel selection rules:**
- **Email:** default for marketing, newsletters, receipts. $0.0001/send.
  Rich HTML, trackable. Requires SES warmup for high volume.
- **SMS:** urgent, high open rate. $0.00645/msg (US). Requires origination
  number and 10DLC/toll-free registration. Use for OTP, alerts.
- **Push:** free, requires app install. Best for re-engagement.
- **Voice:** highest cost, highest urgency. Critical alerts only.
- **In-app:** for active users (app open required). Onboarding, prompts.

ALWAYS emit the cost estimate. Email is cheap; SMS at scale is expensive
(128K messages = $826/US send). Recommend email-first, SMS for urgent.

## AWS documentation

- **Pinpoint Developer Guide** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/welcome.html
- **Campaigns** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/campaigns.html
- **Journeys** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/journeys.html
- **Segments** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/segments.html
- **Message templates** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/message-templates.html
- **Email channel** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/channels-email.html
- **SMS channel** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/channels-sms.html
- **Push notifications** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/channels-mobile-push.html
- **In-app messaging** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/channels-in-app.html
- **Event streams** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/event-streams.html
- **API Reference** — https://docs.aws.amazon.com/pinpoint/latest/apireference/welcome.html
- **CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/pinpoint/

## References (load on demand)

- [advanced-patterns](references/advanced-patterns.md) — Step 0 expert knowledge (non-obvious behaviors), edge-case catalog, recent AWS features (2024-2026)
- [diagnostic-commands](references/diagnostic-commands.md) — post-deployment verification commands (campaign, segment, channel, journey, event stream)
- [channels-and-segments-guide](references/channels-and-segments-guide.md) — channel and segment detail
- [journeys-guide](references/journeys-guide.md) — journey activity graph detail

## Domain

AWS CloudOps / Pinpoint Multi-Channel Customer Engagement Provisioning.
