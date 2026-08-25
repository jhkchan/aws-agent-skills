---
name: pinpoint-journey-deployer
description: 'Provisions Amazon Pinpoint journeys with production defaults: journey creation (activity-based vs segment-based entry), conditional activity (yes/no split based on event attributes), multivariate split (random percentage), wait activity (time-based hold until a specific time or duration), send message (email/SMS/push/in-app), holdout percentage (suppress a fraction of participants for A/B control), journey schedule (start date/time, end, timezone), quiet time (hours and days of week during which messages are held), journey limits (max contacts, max per participant), rate limits, custom channel (Lambda webhook for non-native destinations), A/B test within journey (multivariate with holdout), journey analytics, and integration with segments and campaigns. Emits a READY_TO_DEPLOY. Triggers: create pinpoint journey, journey conditional split, journey wait activity, journey quiet time, journey holdout, multivariate split journey, journey schedule, journey limits, custom channel lambda, pinpoint journey analytics.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with pinpoint access (create-journey, update-journey, describe-journey, delete-journey), plus lambda:AddPermission for custom channel wiring and IAM permissions for segment and channel configuration. Works with Terraform aws_pinpoint_journey resource and CloudFormation AWS::Pinpoint::Journey templates.'
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
  tags: aws, pinpoint, journey, appintegration, cloudops, deploy, messaging, personalization, multivariate, quiet-time, holdout, ab-testing
  dependencies: aws-orchestrator
  keywords: aws, pinpoint, journey, appintegration, cloudops, deploy, provisioning, conditional split, multivariate split, wait activity, quiet time, holdout, journey schedule, journey limits, rate limit, custom channel, lambda webhook, a/b test, journey analytics, segment-based entry, event-based entry
  when_to_use: Invoke when the user wants to create an Amazon Pinpoint journey, configure conditional (yes/no) splits based on event attributes, set up wait activities (time-based holds), enable quiet time, define holdout percentages for A/B control, configure journey limits (max contacts, max per participant), build a multivariate split, wire a custom Lambda channel, or integrate with existing segments. Do NOT invoke for Pinpoint campaigns (single-message blasts — use pinpoint-campaign-deployer), Pinpoint segments (use pinpoint-segment-deployer), or Pinpoint channel configuration (email/SMS/push setup).
---

# Pinpoint Journey Deployer

An AWS CloudOps agent skill that provisions Amazon Pinpoint journeys
with correct defaults. The skill walks the operator through entry
strategy (event-based vs segment-based), activity types (conditional
split, multivariate split, wait, send message, holdout), journey
schedule, quiet time, journey limits, and custom channel integration.
It captures journey design decisions, explains why each default
matters, and emits a READY_TO_DEPLOY checklist with verification
commands.

## Activation keywords

create Pinpoint journey, journey conditional split, journey wait
activity, journey quiet time, journey holdout, multivariate split
journey, journey schedule, journey limits, custom channel Lambda,
Pinpoint journey analytics.

## STRICT output contract

When this skill is invoked with a Pinpoint journey provisioning request
(create a journey, configure conditional splits, wait activities,
quiet time, holdout, journey limits, or multivariate A/B test), the
agent MUST respond with the READY_TO_DEPLOY checklist defined in the
"Output format" section using the literal all-caps labels
`PINPOINT_JOURNEY:`, `VERDICT:`, `CHECKLIST:`, and
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
| Step 1 — Entry strategy (event-based vs segment-based) | Journey start |
| Step 2 — Send message activity | Email/SMS/push/in-app |
| Step 3 — Conditional split (yes/no) | Event-based branching |
| Step 4 — Multivariate split (random percentage) | A/B testing |
| Step 5 — Wait activity | Time-based hold |
| Step 6 — Holdout | A/B control group |
| Step 7 — Journey schedule | Start/end/timezone |
| Step 8 — Quiet time | Off-hours suppression |
| Step 9 — Journey limits | Max contacts and per-participant caps |
| Step 10 — Rate limits | Throughput control |
| Step 11 — Custom channel (Lambda webhook) | Non-native destinations |
| Step 12 — Journey analytics | Measurement |
| Step 13 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/activities-and-splits.md | Activity + split detail |
| references/schedule-and-limits.md | Schedule, quiet time, limits detail |

## Mindset

**One-line takeaway:** A Pinpoint journey is a multi-step workflow
graph. Participants enter via an event trigger (real-time) or a segment
(bulk), traverse activities (send message, wait, conditional split,
multivariate split, holdout), and exit when they complete the path or
convert. Quiet time holds but does NOT cancel activities. Journey
limits cap total and per-participant participation.

Three misconceptions dominate Pinpoint journey misdesign at provisioning
time:

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#common-misconceptions-from-mindset).
> Three journey-entry, split, and quiet-time misconceptions with correct models.

## Configuration dependency graph (novel heuristic)

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#configuration-dependency-graph-sequencing-notes).
> Why the dependency graph matters and how to sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Journey (create-journey) | Pinpoint project (application ID) exists; at least one activity defined | journey cannot start without a schedule; StartActivity must be set | journey container |
| Entry: event-based | event name defined; event recorded by at least one endpoint | if no endpoints have recorded the event, no participants enter | real-time trigger |
| Entry: segment-based | segment exists and is resolved (not empty) | segment is evaluated at start time — if empty at start, zero participants | bulk trigger |
| Send message (email) | email channel configured (SES or Pinpoint email); verified identity | if email channel not configured, send fails silently per participant | email delivery |
| Send message (SMS) | SMS channel configured; origination number or sender ID allocated | SMS costs apply per message; long codes have 1 MPS throughput | SMS delivery |
| Send message (push) | push channel configured (APNs cert, FCM API key); endpoint has device token | push tokens expire; stale tokens cause silent failures | push delivery |
| Conditional split | event name + attribute condition defined | if the event has no attributes, the yes branch never evaluates | event-based branching |
| Multivariate split | percentages must sum to 100 across all branches | random assignment is per-participant at entry; not adjustable mid-journey | A/B testing |
| Wait activity | duration or absolute time specified | wait is a HARD hold — no messages send during the wait | cadence control |
| Holdout | percentage (0-100) of participants suppressed | holdout is evaluated at ENTRY — suppressed participants never start the journey | A/B control group |
| Quiet time | start/end hour (UTC or local); days of week | quiet time HOLDS messages, does NOT cancel them | off-hours suppression |
| Journey schedule | start date/time; timezone | once a journey is started, the entry mode is locked (cannot switch event↔segment) | journey activation |
| Journey limits | total participant count; per-participant message cap | limits are SOFT caps — exceeded participants are queued, not rejected | throughput control |
| Custom channel | Lambda function ARN; Lambda resource-based permission granting Pinpoint | Lambda timeout must handle the webhook within 15 seconds | non-native destinations |

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#cross-dependency-gotchas).
> Baseline-miss rows and cross-dependency gotchas (entry strategy, splits, quiet time, limits, holdout).

## Expert heuristic: event-based vs segment-based entry

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#expert-heuristic-event-based-vs-segment-based-entry).
> Event-based = real-time behavioral trigger; segment-based = scheduled bulk.

## Expert heuristic: conditional split evaluates event attributes

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#expert-heuristic-conditional-split-evaluates-event-attributes).
> Conditional split evaluates an event attribute recorded during the journey (yes/no).

## Expert heuristic: quiet time holds, does not cancel

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#expert-heuristic-quiet-time-holds-does-not-cancel).
> Quiet time delays delivery; use absolute-time waits for precise cadence.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Pinpoint project (application ID) exists | Journey belongs to a project | `aws pinpoint get-app --application-id <id>` |
| Entry strategy confirmed (event-based or segment-based) | Determines trigger model and valid activities | Confirm with the operator |
| Segment exists and is resolved (if segment-based) | Empty segment = zero participants | `aws pinpoint get-segment --application-id <id> --segment-id <id>` |
| Event name defined (if event-based or conditional split) | Trigger/split depends on event | Confirm event is recorded by endpoints |
| Email channel configured (if send email activity) | Without SES/email channel, sends fail | `aws pinpoint get-email-channel --application-id <id>` |
| SMS channel configured (if send SMS activity) | Without SMS origination, sends fail | `aws pinpoint get-sms-channel --application-id <id>` |
| Push channel configured (if send push activity) | Without APNs/FCM, sends fail | `aws pinpoint get-apns-channel --application-id <id>` |
| Lambda function deployed (if custom channel) | Custom channel needs an existing Lambda | `aws lambda get-function --function-name <name>` |
| Lambda resource-based permission grants Pinpoint | Without it, custom channel invocation fails | `aws lambda get-policy --function-name <name>` |
| Timezone confirmed for schedule and quiet time | Mismatched timezones cause off-schedule sends | Confirm IANA timezone (e.g., America/New_York) |
| Journey limits decision (max contacts, per-participant) | Prevents runaway costs | Confirm with the operator |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Entry strategy (event-based vs segment-based)

The entry strategy is the most important journey decision. It
determines the trigger model.

| Mode | Trigger | When to use |
|---|---|---|
| Event-based | Participant records a specific event | Behavioral/reactive (abandoned cart, post-signup) |
| Segment-based | All segment members at scheduled start | Broadcast/proactive (newsletter, promo) |

**Event-based entry:**

```bash
aws pinpoint create-journey \
  --application-id "$APP_ID" \
  --write-journey-request '{
    "Name": "AbandonedCartRecovery",
    "StartActivity": "SendReminderEmail",
    "StartCondition": {"EventStartCondition": {"EventPastDays": 0}},
    "Activities": { ... }
  }'
```

**Segment-based entry:**

```bash
aws pinpoint create-journey \
  --application-id "$APP_ID" \
  --write-journey-request '{
    "Name": "WeeklyDigest",
    "StartActivity": "SendDigest",
    "StartCondition": {"SegmentStartCondition": {"SegmentId": "segment-active-users-123"}},
    "Activities": { ... }
  }'
```

**Critical:** the entry mode is locked once the journey starts. You
cannot switch between event-based and segment-based after activation.

## Step 2 — Send message activity

The send message activity dispatches a message via one of four
channels:

| Channel | Requirements | Throughput |
|---|---|---|
| Email | SES verified identity or Pinpoint email channel | High (SES limits) |
| SMS | Origination number or sender ID | 1 MPS (long code), 100+ MPS (shortcode) |
| Push | APNs cert + FCM API key; endpoint device token | High (APNs/FCM limits) |
| In-app | Mobile SDK integrated | Via SDK push |

> Moved to [references/activities-and-splits.md](references/activities-and-splits.md#step-2-send-message-activity-json-example).
> SendEmail activity JSON referencing a message template.

**Message templates:** reference a pre-created Pinpoint message template
by name. Templates support Liquid personalization (`{{User.UserAttributes.FirstName}}`).

## Step 3 — Conditional split (yes/no)

A conditional split evaluates whether a participant performed an event
during the journey. It branches into YES and NO paths.

> Moved to [references/activities-and-splits.md](references/activities-and-splits.md#step-3-conditional-split-yesno-json-example).
> ConditionalSplit activity JSON with EventCondition and True/False activities.

**Critical:** the conditional split evaluates events recorded DURING the
journey window. If the event was recorded before entry, it does not
count.

## Step 4 — Multivariate split (random percentage)

A multivariate split assigns participants randomly to branches by
percentage. Percentages MUST sum to 100.

> Moved to [references/activities-and-splits.md](references/activities-and-splits.md#step-4-multivariate-split-random-percentage-json-example).
> MultivariateSplit activity JSON with percentage branches summing to 100.

**For A/B testing:** pair with a holdout (Step 6) to measure lift
against a control group. **Common mistake:** confusing multivariate
split (random) with conditional split (event-based). Use conditional
for behavioral branching; multivariate for random A/B assignment.

## Step 5 — Wait activity

A wait activity holds the participant for a duration or until an
absolute time.

> Moved to [references/activities-and-splits.md](references/activities-and-splits.md#step-5-wait-activity-json-examples).
> Duration-based and absolute-time Wait activity JSON.

**Critical:** wait interacts with quiet time. If a wait ends during a
quiet period, the subsequent send is held. Use absolute-time waits for
precise cadence control.

## Step 6 — Holdout

A holdout suppresses a percentage of participants at entry — they never
start the journey. This is the control group for A/B lift measurement.

```json
{"Holdout": {"Percentage": 10, "NextActivity": "ExitHoldout"}}
```

**Holdout vs multivariate branch with no send:** holdout = participant
never enters the journey. Multivariate no-send = participant enters but
receives no message on that branch. For true A/B lift, use holdout.

## Step 7 — Journey schedule

The journey schedule defines when the journey starts and ends, and in
what timezone.

> Moved to [references/schedule-and-limits.md](references/schedule-and-limits.md#step-7-journey-schedule-json-example).
> Schedule JSON with StartTime, EndTime, and Timezone.

**Critical for segment-based journeys:** the StartTime is when all
segment members are added to the journey. For event-based journeys, the
StartTime is when the journey begins ACCEPTING events (participants
enter as they perform the event after StartTime).

## Step 8 — Quiet time

Quiet time holds message sends during configured hours and days.

> Moved to [references/schedule-and-limits.md](references/schedule-and-limits.md#step-8-quiet-time-json-example).
> QuietTime JSON with start/end hours and days of week.

**Critical:** quiet time HOLDS messages, it does NOT cancel them. When
the quiet window ends, held messages are delivered. This can shift the
effective journey cadence. If precise timing matters, design wait
activities to land outside quiet windows.

**Timezone:** quiet time is evaluated in the journey's timezone (set in
the schedule). If the participant base spans multiple timezones, the
quiet time applies uniformly — consider segmenting by timezone for
precise control.

## Step 9 — Journey limits

Journey limits cap total participation and per-participant messaging.

> Moved to [references/schedule-and-limits.md](references/schedule-and-limits.md#step-9-journey-limits-json-example).
> Limits JSON with DailyCap, MaximumEndpointSend, TotalParticipantCap.

| Limit | Purpose |
|---|---|
| `DailyCap` | Max messages per day across all participants |
| `MaximumEndpointSend` | Max messages to a single endpoint per journey |
| `TotalParticipantCap` | Max total participants across journey lifetime |

**Critical:** limits are evaluated at entry. Once in the journey,
participants traverse all activities regardless of caps.

## Step 10 — Rate limits

Rate limits control throughput to avoid overwhelming downstream
channels (SES, SMS providers). Configure at the Pinpoint account or
journey level.

```bash
aws pinpoint update-journey \
  --application-id "$APP_ID" \
  --journey-id "$JOURNEY_ID" \
  --write-journey-request '{
    "Name": "AbandonedCartRecovery",
    "QuietTime": {"Start": "22:00", "End": "08:00"},
    "Limits": {"DailyCap": 50000, "MaximumEndpointSend": 3}
  }'
```

**SMS throughput:** long codes (10DLC) are limited to 1 message per
second (MPS). Short codes support 100+ MPS. For high-volume SMS
journeys, ensure you have sufficient origination numbers.

## Step 11 — Custom channel (Lambda webhook)

The custom channel activity invokes a Lambda function for non-native
destinations (e.g., webhook to a third-party API, custom push provider).

```json
{
  "Custom": {
    "EndpointType": "Lambda",
    "LambdaFunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:CustomChannelHandler",
    "NextActivity": "WaitBeforeRetry"
  }
}
```

**Grant Pinpoint permission to invoke the Lambda:**

```bash
aws lambda add-permission \
  --function-name CustomChannelHandler \
  --statement-id PinpointInvokePermission \
  --action lambda:InvokeFunction \
  --principal pinpoint.amazonaws.com \
  --source-arn "arn:aws:mobiletargeting:us-east-1:123456789012:apps/$APP_ID/journeys/$JOURNEY_ID"
```

**Lambda timeout:** Pinpoint expects the Lambda to complete within 15
seconds. Long-running operations should be asynchronous (queue to SQS
or Step Functions).

## Step 12 — Journey analytics

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#step-12-journey-analytics-kpi-commands-and-metrics).
> get-journey-date-range-kpi command, KPI metric table, conversion tracking.

## Step 13 — Recent features

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#step-13-recent-features).
> Recent AWS features (2023-2026): journey-run API, in-app messages, cross-channel analytics, state management, ML send-time optimization, Q Business.

## NEVER do these things

1. **NEVER confuse conditional split with multivariate split.**
   Conditional evaluates an event attribute (yes/no). Multivariate is
   random percentage for A/B testing. Using random when you need
   behavioral branching means the journey never branches correctly.

2. **NEVER assume quiet time cancels messages.** Quiet time HOLDS
   messages. They are delivered when the quiet window closes. Design
   wait activities to account for quiet-time delay.

3. **NEVER switch entry mode after journey start.** Event-based vs
   segment-based is LOCKED at activation. Create a new journey if the
   entry strategy needs to change.

4. **NEVER forget the Lambda resource-based permission for custom
   channels.** Pinpoint must have `lambda:InvokeFunction` on the
   function scoped to the journey ARN. Without it, custom channel
   invocations fail silently.

5. **NEVER set multivariate percentages that do not sum to 100.** The
   API may accept misconfigured splits but the behavior is undefined.
   Always verify percentages sum to exactly 100.

6. **NEVER use duration-based waits when precise timing matters.**
   Duration-based waits drift with quiet time. Use absolute-time waits
   to anchor to specific clock times.

7. **NEVER assume a conditional split evaluates pre-entry events.** The
   condition evaluates events recorded DURING the journey. If the event
   happened before entry, the YES branch will not fire.

8. **NEVER exceed SMS throughput limits.** Long codes (10DLC) are
   limited to 1 MPS. High-volume SMS journeys need shortcodes or
   sender IDs. Monitor for throttling.

9. **NEVER forget to configure message templates before referencing
   them in send activities.** Send activities reference templates by
   name. If the template does not exist, the send fails per
   participant.

10. **NEVER assume journey limits retroactively remove participants.**
    Limits are evaluated at entry. Once in, participants traverse all
    activities regardless of caps.

## Output format

```text
PINPOINT_JOURNEY: <journey-name> (<journey-id>) | project: <app-id>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Pinpoint project: <app-id>
  [✓|✗] Entry strategy: Event-based (event: <name>) | Segment-based (segment: <id>)
  [✓|✗] Activities: <activity-name-list>
  [✓|✗] Send channels: email=<on|off>, SMS=<on|off>, push=<on|off>, in-app=<on|off>
  [✓|✗] Conditional splits: <split-name> evaluating event <event-name> (YES→<activity>, NO→<activity>)
  [✓|✗] Multivariate splits: <split-name> (<percentages>) — sums to 100
  [✓|✗] Wait activities: <wait-name> (<duration or absolute time>)
  [✓|✗] Holdout: <percentage>% suppressed at entry
  [✓|✗] Schedule: start <datetime>, end <datetime>, timezone <tz>
  [✓|✗] Quiet time: <start>–<end> on <days-of-week> (HOLDS, not cancels)
  [✓|✗] Journey limits: dailyCap=<n>, maxEndpointSend=<n>, totalParticipantCap=<n>
  [✓|✗] Custom channel: Lambda=<arn> (resource-based permission granted)
  [✓|✗] Message templates referenced: <template-name-list>
  [✓|✗] Analytics: conversion event=<event-name>
VERIFICATION_COMMANDS:
  aws pinpoint describe-journey --application-id <app-id> --journey-id <journey-id>
  aws pinpoint get-journey-date-range-kpi --application-id <app-id> --journey-id <journey-id> --kpi-name UniqueEndpoints --start-time <start> --end-time <end>
  aws lambda get-policy --function-name <custom-channel-lambda>
```

### Worked example — abandoned cart recovery journey

```text
PINPOINT_JOURNEY: AbandonedCartRecovery (journey-abc123) | project: app-xyz789
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Pinpoint project: app-xyz789
  [✓] Entry strategy: Event-based (event: cart_abandoned)
  [✓] Activities: SendReminderEmail, Wait24Hours, ConditionalSplit-CheckPurchase, SendReminderSMS, ExitConverted, ExitHoldout
  [✓] Send channels: email=on, SMS=on, push=off, in-app=off
  [✓] Conditional splits: CheckPurchase evaluating event purchase_completed (YES→ExitConverted, NO→SendReminderSMS)
  [✓] Multivariate splits: none
  [✓] Wait activities: Wait24Hours (24 HOURS duration)
  [✓] Holdout: 10% suppressed at entry (control group for A/B lift)
  [✓] Schedule: start 2026-08-15T09:00:00Z, end 2026-09-15T09:00:00Z, timezone UTC
  [✓] Quiet time: 22:00–08:00 on MON,TUE,WED,THU,FRI (HOLDS, not cancels)
  [✓] Journey limits: dailyCap=50000, maxEndpointSend=3, totalParticipantCap=500000
  [✓] Custom channel: none
  [✓] Message templates referenced: cart-reminder-email, cart-reminder-sms
  [✓] Analytics: conversion event=purchase_completed
VERIFICATION_COMMANDS:
  aws pinpoint describe-journey --application-id app-xyz789 --journey-id journey-abc123
  aws pinpoint get-journey-date-range-kpi --application-id app-xyz789 --journey-id journey-abc123 --kpi-name UniqueEndpoints --start-time 2026-08-15T00:00:00Z --end-time 2026-08-22T00:00:00Z
```

## Error handling

> Moved to [references/error-handling.md](references/error-handling.md#error-handling).
> Symptom-by-symptom fixes: participants not entering, split never YES, quiet-time holds, custom channel Lambda, percentages.
## References (load on demand)

- [advanced-patterns](references/advanced-patterns.md) — expert-heuristic deep dives, misconceptions, dependency-graph notes, recent AWS features (2023-2026)
- [diagnostic-commands](references/diagnostic-commands.md) — journey analytics KPI commands and metrics
- [error-handling](references/error-handling.md) — symptom-by-symptom troubleshooting
- [activities-and-splits](references/activities-and-splits.md) — activity and split detail, plus JSON examples per activity type (existing)
- [schedule-and-limits](references/schedule-and-limits.md) — schedule, quiet time, limits detail, plus JSON examples (existing)

## Domain

AWS CloudOps / Amazon Pinpoint Journey Provisioning & Customer
Engagement Workflow Deployment.

## AWS documentation

- **Pinpoint Developer Guide (Journeys)** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/journeys.html
- **create-journey** — https://docs.aws.amazon.com/pinpoint/latest/apireference/apps-application-id-journeys.html
- **Journey activities / Conditional splits / Multivariate splits** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/journeys-activities.html
- **Quiet time** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/journeys-quiettime.html
- **Holdout** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/journeys-holdout.html
- **Custom channel** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/journeys-custom.html
- **Journey analytics** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/analytics-journeys.html
- **Message templates** — https://docs.aws.amazon.com/pinpoint/latest/developerguide/templates.html
