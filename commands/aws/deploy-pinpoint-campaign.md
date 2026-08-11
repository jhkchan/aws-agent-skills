---
description: Provision a production-grade Pinpoint campaign or journey with channels, segments, templates, quiet time, A/B testing, and event streaming.
nl_triggers:
  - "create Pinpoint project"
  - "provision Pinpoint campaign"
  - "Pinpoint journey"
  - "Pinpoint segment"
  - "Pinpoint email channel"
  - "Pinpoint SMS channel"
  - "Pinpoint push notification"
  - "Pinpoint message template"
  - "A/B test campaign"
  - "Pinpoint in-app messaging"
  - "Pinpoint event stream Kinesis"
  - "ML segment recommendations"
  - "multivariate journey"
  - "pinpoint create-campaign"
routes_to: pinpoint-campaign-deployer
---

# /aws:deploy-pinpoint-campaign

Activate the `pinpoint-campaign-deployer` skill and produce a deployment
plan for a production-grade Amazon Pinpoint campaign or multi-step journey.

## What it does

Reads a deployment specification (project, channel, segment, templates,
schedule, journey activity graph, event stream) and produces an ordered
deployment plan with:

1. Pre-flight specification gate — validates project existence, channel
   prerequisites (SES verified identity for email, origination number for
   SMS, APNs/FCM credentials for push), segment resolution (>0 endpoints),
   template format, schedule validity. Blocks deployment
   (PREREQUISITES_MISSING) on missing fields or invalid combinations.
2. Channel configuration — email (SES identity), SMS (origination number,
   spend limit), push (APNs token key, FCM API key), voice (origination
   number).
3. Segment creation — demographic (dimension-based), dynamic (event-based),
   imported (CSV or S3). Verified via get-segment-estimate.
4. Message templates — email, SMS, push with Liquid personalization
   ({{UserAttributes.X}}, {{Attributes.X}}).
5. Campaign creation — schedule (immediate or future), quiet time
   (StartTime, EndTime, TimeZone), frequency cap (project-wide).
6. A/B testing — holdout percentage (control group), additional treatments
   with distinct templates. Percentages + holdout sum to 100.
7. Journey creation — activity graph model: ENTRY, SEND, WAIT (time-based
   or event-based), CONDITIONAL_SPLIT (yes-no on event/attribute),
   MULTIVARIATE_SPLIT (A/B/C by percentage), RANDOM_SPLIT, END. Validated
   as DAG with all paths reaching END.
8. In-app messaging — BOTTOM_BANNER, TOP_BANNER, OVERLAYS, CAROUSEL
   layouts via mobile SDK.
9. Event streams — Kinesis stream or Firehose delivery stream. Role must
   have kinesis:PutRecord.
10. ML-powered recommendations — lookalike audience expansion based on
    engagement patterns.

Emits a deterministic deployment plan per campaign/journey:

```text
CAMPAIGN: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
PRE_CHECKS:
  - [PASS] <check>
  - [FAIL] <check> — <reason>
STEPS:
  1. CONFIRM: About to <operation> campaign <name>...
  2. <exact CLI command>
POST_VERIFY:
  - [PASS] <verification>
CHANNEL: email | sms | push | voice | multi
SEGMENT: <segment-id> (<type>, <count> endpoints)
SCHEDULE: immediate | scheduled
QUIET_TIME: <start-end TZ | none>
...
```

## When to invoke

Provide a deployment spec and ask any of:

- "create a Pinpoint email campaign"
- "build a multi-step onboarding journey"
- "set up an A/B test for subject lines"
- "configure SMS channel with an origination number"
- "import a segment from S3"
- "wire event streaming to Kinesis"
- "create a push notification campaign for iOS and Android"

A bare campaign name + channel + "deploy" also routes here via the
orchestrator.

## Inputs

- **Required:** project_id (existing Pinpoint project application-id),
  channel (email | sms | push | voice), segment_id (segment that resolves
  to >0 endpoints), message (template or inline message body), schedule
  (immediate or future start time).
- **Optional:** quiet_time (StartTime, EndTime, TimeZone), frequency_cap
  (project-wide N/day), ab_test (holdoutPercent, additionalTreatments),
  journey_activities (activity graph), event_stream_arn (Kinesis stream),
  in_app_message (layout, content).

## Outputs

- One VERDICT block per campaign/journey (READY_TO_DEPLOY or
  PREREQUISITES_MISSING).
- PRE_CHECKS with all validation checks ([PASS] or [FAIL]).
- STEPS with ordered `aws pinpoint` commands (channel verification first,
  segment second, template third, campaign/journey last).
- POST_VERIFY with verification commands.
- Architecture summary (CHANNEL, SEGMENT, TEMPLATE, SCHEDULE, QUIET_TIME,
  FREQUENCY_CAP, AB_TEST, JOURNEY).
- Cost estimate (email $0.0001/send, SMS $0.00645/msg US, push free).

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 1 Deploy specialist for Pinpoint).
- `/aws:audit-pinpoint-*` for post-deployment auditing (channel
  configuration, segment coverage, campaign effectiveness).
