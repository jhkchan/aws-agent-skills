# Advanced Patterns — Pinpoint Campaign Deployer

Deep-dive material moved out of the SKILL.md body so the procedure
stays scannable. Loaded on demand by the skill.

## Step 0: Expert knowledge — non-obvious behaviors


- **Channel enablement is silent.** A campaign on an unenabled channel
  produces zero sends — no error, no warning. Status shows `COMPLETED` with
  0 messages sent. Always verify channel before campaign creation.
- **Segments are dynamic by default.** Dimension-based segments resolve at
  send time. If attributes change between creation and send, different
  endpoints may be included. For fixed targeting, use imported (CSV).
- **Imported segments require S3.** The bucket MUST grant `s3:GetObject` to
  the Pinpoint service principal. CSV: one endpoint per line.
- **Quiet time blocks sends during a window.** Requires `StartTime`,
  `EndTime`, and `TimeZone`. Without timezone, quiet time is ambiguous.
- **Frequency caps are project-wide.** A cap of 3 = an endpoint receives at
  most 3 messages across ALL campaigns per calendar day.
- **Journeys use an activity graph model.** Each activity has a `Type`
  (CONDITIONAL_SPLIT, MULTIVARIATE_SPLIT, RANDOM_SPLIT, WAIT, SEND, END) and
  `NextActivity`. MUST be a DAG. Every path must reach END.
- **Yes-no split evaluates an event or attribute.** CONDITIONAL_SPLIT with
  `EvaluationDimension`. Branches: `TrueActivity` and `FalseActivity`.
- **Multivariate split distributes by percentage.** Percentages MUST sum to
  100. Each branch has a distinct treatment (template override).
- **Wait activities: time-based or event-based.** Time: `WaitTime` (e.g.,
  `"PT1H"`). Event: `WaitUntil` with optional timeout. Without timeout,
  blocks indefinitely.
- **In-app messaging (2024-2025):** campaigns/journeys send in-app messages
  via SDK. Layouts: BOTTOM_BANNER, TOP_BANNER, OVERLAYS, MIDDLE_BANNER.
- **ML-powered recommendations (2024-2025):** Pinpoint analyzes engagement
  and recommends lookalike audiences. Via `get-recommended-metrics`.
- **Event streams to Kinesis:** `put-event-stream` streams events. Stream
  MUST exist; Pinpoint role MUST have `kinesis:PutRecord`.

## Edge-case handling

- **Email channel not enabled.** PREREQUISITES_MISSING. Verify SES identity.
- **SMS origination missing.** PREREQUISITES_MISSING. Provision short/long code.
- **Segment resolves to 0.** PREREQUISITES_MISSING. Adjust dimensions.
- **Schedule in the past.** PREREQUISITES_MISSING. Use IMMEDIATE or future.
- **Quiet time without timezone.** PREREQUISITES_MISSING. Set TimeZone.
- **A/B percentages do not sum to 100.** PREREQUISITES_MISSING.
- **Journey with cycle.** PREREQUISITES_MISSING. Graph must be a DAG.
- **Journey activity with no NextActivity (non-END).** PREREQUISITES_MISSING.
- **Frequency cap 0.** PREREQUISITES_MISSING. Blocks all sends.

## Recent AWS features (2024-2026)

- **In-app messaging (2024-2025):** campaigns/journeys send in-app messages
  via SDK. Layouts: BOTTOM_BANNER, TOP_BANNER, OVERLAYS, CAROUSEL. Free.
- **ML-powered segment recommendations (2024-2025):** analyzes engagement
  and recommends lookalike audiences. Via `get-recommended-metrics`.
- **Journeys with multivariate and random split (2024-2025):** journey
  activities support MULTIVARIATE_SPLIT and RANDOM_SPLIT.
- **Event-based wait activities (2024):** WAIT can wait for a specific event
  (e.g., `app_open`) with optional timeout.
- **SES integration improvements (2024-2025):** Pinpoint email uses SESv2.
  Supports configuration sets, VDM, dedicated IP pools.
- **Baidu push channel (2024-2025):** push to Android in China via Baidu.
- **Journey versioning (2025):** version history and rollback support.

