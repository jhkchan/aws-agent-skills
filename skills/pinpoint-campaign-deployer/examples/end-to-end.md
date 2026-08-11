# End-to-end usage scenario: pinpoint-campaign-deployer

A walkthrough showing the skill producing a deployment plan for a
production Pinpoint multi-step onboarding journey with conditional
branching, email channel via SES, quiet time enforcement, and Kinesis
event streaming. Demonstrates the READY_TO_DEPLOY verdict, pre-check
list, and ordered deploy-command sequence.

## Input (user prompt)

> Build a Pinpoint onboarding journey for our SaaS app. New users who
> sign up should get a welcome email immediately. After 24 hours, check
> if they've opened the app — if yes, end the journey (they're engaged).
> If no, send a nudge email with tips. After another 48 hours, if they
> still haven't opened the app, send a final re-engagement email. Use
> the email channel (SES identity `example.com`, verified). The segment
> is `seg-new-users` (12000 endpoints — signed up in last 7 days). Set
> quiet time to 22:00-08:00 America/New_York. Wire event streaming to
> Kinesis stream `pinpoint-events`.

## Expected behavior

1. **Pre-flight:** The skill validates the spec — project exists, email
   channel enabled with verified SES identity, segment resolves to >0
   endpoints, templates exist (or need creation), quiet time has
   timezone, journey activity graph is a valid DAG.
2. **Channel:** Email channel is enabled. SES identity `example.com` is
   verified (SUCCESS). No action needed — verify.
3. **Segment:** `seg-new-users` resolves to 12000 endpoints via
   `get-segment-estimate`. Passes >0 check.
4. **Templates:** `welcome-email`, `nudge-email`, and
   `reengagement-email` need to be created (or verified if existing).
5. **Journey graph:** ENTRY -> SEND welcome -> WAIT 24h ->
   CONDITIONAL_SPLIT (app_open?) -> True: END / False: SEND nudge ->
   WAIT 48h -> CONDITIONAL_SPLIT (app_open?) -> True: END / False:
   SEND reengagement -> END. Validated as DAG with all paths reaching
   END.
6. **Event stream:** Kinesis stream `pinpoint-events` exists. Role
   `PinpointStream` has `kinesis:PutRecord`.
7. **Verdict:** READY_TO_DEPLOY — all pre-checks pass.

## Expected output

```text
CAMPAIGN: onboarding-journey
VERDICT: READY_TO_DEPLOY
TARGET: onboarding-journey
PRE_CHECKS:
  - [PASS] Project app-abc123 exists (get-app returned)
  - [PASS] Email channel enabled, SES identity example.com verified SUCCESS
  - [PASS] Segment seg-new-users resolves to 12000 endpoints
  - [PASS] Templates welcome-email, nudge-email, reengagement-email parse
  - [PASS] Quiet time 22:00-08:00 America/New_York (timezone set)
  - [PASS] Journey graph: ENTRY -> SEND -> WAIT -> SPLIT -> END (DAG, all paths reach END)
  - [PASS] Kinesis stream pinpoint-events exists, role has kinesis:PutRecord
  - [PASS] IAM principal holds pinpoint:CreateJourney
STEPS:
  1. CONFIRM: About to create-journey onboarding-journey in project app-abc123 region us-east-1. 4-step onboarding flow for 12000 new users via email. Estimated cost: $1.20/email x 3 sends = $3.60 max per user. Proceed? (yes/no)
  2. aws pinpoint get-app --application-id app-abc123
  3. aws sesv2 get-email-identity --email-identity example.com
  4. aws pinpoint get-segment-estimate --application-id app-abc123 --segment-id seg-new-users
  5. aws pinpoint create-email-template --email-template-request '{"TemplateName":"welcome-email","Subject":"Welcome to the app, {{UserAttributes.FirstName}}!","HtmlPart":"<html>...</html>","TextPart":"Welcome!"}'
  6. aws pinpoint create-email-template --email-template-request '{"TemplateName":"nudge-email","Subject":"Quick tips to get started","HtmlPart":"<html>...</html>","TextPart":"Tips!"}'
  7. aws pinpoint create-email-template --email-template-request '{"TemplateName":"reengagement-email","Subject":"We miss you! Here is 20% off","HtmlPart":"<html>...</html>","TextPart":"20% off!"}'
  8. aws pinpoint put-event-stream --application-id app-abc123 --write-event-stream '{"DestinationStreamArn":"arn:aws:kinesis:us-east-1:111111111111:stream/pinpoint-events","RoleArn":"arn:aws:iam::111111111111:role/PinpointStream"}'
  9. aws pinpoint create-journey --application-id app-abc123 --write-journey-request '{...full activity graph...}'
POST_VERIFY:
  - (pending execution)
  - get-journey returns State=DRAFT (review then enable)
  - get-event-stream returns DestinationStreamArn matching pinpoint-events
CHANNEL: email
SEGMENT: seg-new-users (dynamic, 12000 endpoints)
TEMPLATE: welcome-email, nudge-email, reengagement-email (email)
SCHEDULE: event-based (entry on signup)
QUIET_TIME: 22:00-08:00 America/New_York
FREQUENCY_CAP: none (journey, not campaign)
JOURNEY: ENTRY -> SEND welcome -> WAIT 24h -> SPLIT(app_open?) -> True: END / False: SEND nudge -> WAIT 48h -> SPLIT(app_open?) -> True: END / False: SEND reengagement -> END
NOTES:
  - SES identity must remain verified — if it lapses, all sends fail.
  - Journey starts in DRAFT state — review then enable via update-journey.
  - Event-based WAITs have no timeout — endpoints that never open the app stay in the journey indefinitely.
  - Frequency cap is not set — ensure concurrent campaigns do not overwhelm users.
```

## Post-deployment verification

After running the deploy commands, verify the journey and event stream:

```bash
# Verify journey is in DRAFT state
aws pinpoint get-journey \
  --application-id app-abc123 --journey-id <journey-id> \
  --query 'JourneyResponse.State'
# Expect: "DRAFT"

# Verify email channel is enabled
aws pinpoint get-email-channel \
  --application-id app-abc123 \
  --query 'EmailChannelResponse.Enabled'
# Expect: true

# Verify segment endpoint count
aws pinpoint get-segment-estimate \
  --application-id app-abc123 --segment-id seg-new-users \
  --query 'SegmentSize'
# Expect: 12000

# Verify event stream
aws pinpoint get-event-stream \
  --application-id app-abc123 \
  --query 'EventStream.DestinationStreamArn'
# Expect: arn:aws:kinesis:us-east-1:111111111111:stream/pinpoint-events

# Enable the journey after review
aws pinpoint update-journey \
  --application-id app-abc123 --journey-id <journey-id> \
  --write-journey-request '{"State":"ACTIVE"}'
# Expect: JourneyResponse.State=ACTIVE
```

## Common pitfalls to verify after deployment

1. **Journey left in DRAFT state.** A DRAFT journey does not send any
   messages. After review, enable via `update-journey --write-journey-request
   '{"State":"ACTIVE"}'`. Verify the state changed to ACTIVE.
2. **CONDITIONAL_SPLIT evaluates wrong event.** The split must reference
   the exact event type (e.g., `app_open`, not `_session.start`). Verify
   the event name matches what the mobile SDK emits.
3. **WAIT activity without timeout.** An event-based WAIT without a
   timeout blocks indefinitely. Endpoints that never trigger the event
   stay stuck in the journey. Always set a timeout on event-based WAITs.
4. **SES identity lapses.** If DNS verification records are removed, the
   SES identity reverts to PENDING and all email sends fail silently.
   Monitor SES identity status via CloudWatch alarms.
5. **Frequency cap conflicts.** If a project-wide frequency cap is set,
   concurrent campaigns may reduce journey reach. Verify the cap does not
   interfere with the journey's expected send pattern.
