---
description: Provision an Amazon Pinpoint segment-first deployment (project, dynamic/static segment, dimensions, channels, templates, campaigns, journeys, A/B testing, SMS number types, push setup, event streaming). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create pinpoint segment"
  - "deploy pinpoint segment"
  - "dynamic segment"
  - "static segment"
  - "segment dimensions"
  - "pinpoint journey"
  - "conditional split journey"
  - "multivariate journey"
  - "ab test sample size"
  - "pinpoint sms sender id"
  - "pinpoint long code"
  - "pinpoint toll-free"
  - "pinpoint 10dlc"
  - "apns push setup"
  - "fcm push setup"
  - "pinpoint event stream kinesis"
  - "pinpoint event stream s3"
  - "pinpoint message template"
  - "pinpoint quiet time"
  - "pinpoint frequency cap"
  - "pinpoint holdout"
routes_to: pinpoint-segment-deployer
---

# /aws:deploy-pinpoint-segment

Activate the `pinpoint-segment-deployer` skill and produce a deployment
plan for a production-grade Amazon Pinpoint segment, journey, campaign,
or channel integration with engagement-best-practice defaults.

## What it does

The skill walks the segment-first provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Project creation (create-app)
2. Segment model — dynamic vs static (recompute on eval vs imported
   snapshot)
3. Segment dimensions — Demographic, Behavior, UserAttributes,
   Attributes, Location, Metrics
4. Channels — email (SES verified identity), SMS (sender ID, long
   code, toll-free, short code, 10DLC), push (APNs .p8 token, FCM
   API key / service account), voice (origination number)
5. Message templates — email (HTML + Liquid), SMS, push (APNS/GCM
   JSON)
6. Campaigns — scheduled vs event-triggered (Behavior trigger)
7. A/B testing — AdditionalTreatments + HoldoutPercent (sum to 100),
   sample-size gate by MDE
8. Quiet time (StartTime, EndTime, TimeZone) and project-wide
   frequency caps
9. Journeys — DAG of activities (ENTRY, SEND, WAIT,
   CONDITIONAL_SPLIT with WaitTime, MULTIVARIATE_SPLIT,
   RANDOM_SPLIT, CONTROL, END)
10. Event streaming — Kinesis Data Streams or Firehose-to-S3 (one
    active stream per project)
11. SMS number types — sender ID (per-country support), long code
    (10DLC US), toll-free (verification), short code
12. Push setup — APNs (.p8 token key, Key ID, Team ID, Bundle ID),
    FCM (API key or service account JSON)
13. Recent features — journey dynamic entry, ML segment
    recommendations, in-app messaging, AWS End User Messaging SMS

## When to use

- You need to create a Pinpoint project.
- You are building a dynamic or static segment.
- You are designing a multi-step journey with conditional or
  multivariate splits.
- You are setting up an A/B test with sample-size justification.
- You are configuring SMS (sender ID, long code, toll-free, 10DLC).
- You are configuring APNs or FCM push channels.
- You are wiring event streaming to Kinesis or Firehose-to-S3.
- You are applying quiet time or frequency caps.

## When NOT to use

- **Amazon SES standalone** — use SES skills for transactional email
  without Pinpoint engagement features.
- **Amazon SNS** — different service (fan-out notifications).
- **AWS Activate messaging** — different program.
- **Auditing existing Pinpoint projects** — use Pinpoint audit skills.

## How to invoke

### Slash command

```
/aws:deploy-pinpoint-segment
```

Then provide: project ID (existing or new), segment type (dynamic/
static) and dimensions, channel prerequisites (SES identity, SMS
origination, APNs/FCM credentials), templates, schedule, A/B test
parameters, journey activity graph, event stream target, SMS number
type, tags.

### Natural language

Any of these routes to the same skill:

- "create a dynamic segment with Behavior DAY_7 ACTIVE"
- "build a journey with conditional split on purchase event"
- "set up an A/B test with 3 treatments and 20% holdout"
- "configure SMS with a long code for US recipients"
- "wire event streaming to Kinesis"
- "configure APNs push with a .p8 token key"

### CLI routing

```bash
node cli/bin/cli.js route "create a pinpoint segment"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create Pinpoint
segments, journeys, campaigns, or channels. The output checklist
feeds into verification pipelines and downstream audit skills.

## Example

```
You: /aws:deploy-pinpoint-segment

     Create a Pinpoint dynamic segment on app-abc123 named
     active-mobile-7d. Behavior DAY_7 ACTIVE. Demographic Channel
     [GCM, APNS]. Build an onboarding-7d journey with a
     CONDITIONAL_SPLIT on purchase event (7-day wait).

Skill:
  PINPOINT_SEGMENT: app-abc123/seg-def456 (dynamic, 42500 endpoints)
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Segment: dynamic (Behavior DAY_7 ACTIVE + Channel GCM,APNS)
    [✓] Journey: onboarding-7d (DAG, WaitTime on CONDITIONAL_SPLIT)
    [✓] Channels: email, SMS, push verified
    [✓] A/B test: 20% holdout + 3 treatments (sample-size OK)
  VERIFICATION_COMMANDS:
    aws pinpoint get-segment-estimate --application-id app-abc123 --segment-id seg-def456
    aws pinpoint get-journey --application-id app-abc123 --journey-id jrn-xyz789
```

## References

- Skill definition: `skills/pinpoint-segment-deployer/SKILL.md`
- Segments and dimensions guide: `skills/pinpoint-segment-deployer/references/segments-and-dimensions.md`
- Journeys and A/B testing guide: `skills/pinpoint-segment-deployer/references/journeys-and-ab-testing.md`
- Eval suite: `skills/pinpoint-segment-deployer/evals/evals.json`
