# Journeys, A/B Testing, and Event Streams Reference

Supplementary reference for the Pinpoint Campaign Deployer skill. Use when
designing multi-step journeys, configuring A/B test campaigns, or wiring
Kinesis event streams.

## Journey activity graph model

A journey is a directed acyclic graph (DAG) of activities. Each activity has
a `Type` and a `NextActivity`. The graph starts at the `StartActivity` and
must reach at least one `END` activity on every path.

### Activity types

| Type | Purpose | Key fields |
|---|---|---|
| `ENTRY` | Journey entry point | `NextActivity` |
| `SEND` | Send a message | `MessageConfiguration`, `NextActivity` |
| `WAIT` | Wait (time or event) | `WaitTime` or `WaitUntil`, `NextActivity` |
| `CONDITIONAL_SPLIT` | Yes-no branch on event/attribute | `Condition`, `TrueActivity`, `FalseActivity` |
| `MULTIVARIATE_SPLIT` | A/B/C branch by percentage | `Branches` (percentages sum to 100) |
| `RANDOM_SPLIT` | Random branch by percentage | `Branches` (percentages sum to 100) |
| `END` | Journey end | (none) |

### Journey entry

Journeys can be entered in two ways:

1. **Event-based:** an endpoint performs a specific event (e.g., `signup`).
   The journey starts for each matching endpoint in real time.
2. **Segment-based:** endpoints in a segment enter the journey when it
   starts. The journey runs once per endpoint.

```json
{
  "Name": "onboarding-flow",
  "StartActivity": "entry",
  "Activities": {
    "entry": {"Type": "ENTRY", "NextActivity": "send-welcome"}
  }
}
```

### WAIT activity

**Time-based:**
```json
{
  "wait-1day": {
    "Type": "WAIT",
    "WaitTime": {"WaitTime": "PT24H"},
    "NextActivity": "check-engaged"
  }
}
```

Duration format: ISO 8601 (`PT1H` = 1 hour, `PT24H` = 24 hours, `P7D` = 7 days).

**Event-based (2024):**
```json
{
  "wait-for-purchase": {
    "Type": "WAIT",
    "WaitUntil": {
      "Event": {"EventType": "purchase"},
      "Timeout": "P7D"
    },
    "NextActivity": "purchase-received"
  }
}
```

An event-based WAIT blocks until the event occurs or the timeout expires.
Without a timeout, the WAIT blocks indefinitely. Always set a timeout.

### CONDITIONAL_SPLIT (yes-no)

```json
{
  "check-engaged": {
    "Type": "CONDITIONAL_SPLIT",
    "Condition": {
      "Conditions": [{
        "EventCondition": {
          "Dimensions": [{"EventType": "app_open", "DimensionType": "IN"}],
          "SegmentDimensions": {"Recency": {"DimensionType": "BEFORE", "Amount": "1"}}
        }
      }],
      "Operator": "ALL"
    },
    "TrueActivity": "send-tips",
    "FalseActivity": "send-nudge",
    "EvaluationDimension": null
  }
}
```

**Branches:**
- `TrueActivity`: endpoint matches the condition.
- `FalseActivity`: endpoint does NOT match.

**Condition types:**
- `EventCondition`: endpoint has performed a specific event.
- `SegmentCondition`: endpoint is in a specific segment.
- `AttributeCondition`: endpoint/user has a specific attribute value.

### MULTIVARIATE_SPLIT (A/B/C)

```json
{
  "ab-test": {
    "Type": "MULTIVARIATE_SPLIT",
    "Branches": [
      {"Id": "variant-a", "Percentage": 34, "NextActivity": "send-a"},
      {"Id": "variant-b", "Percentage": 33, "NextActivity": "send-b"},
      {"Id": "variant-c", "Percentage": 33, "NextActivity": "send-c"}
    ]
  }
}
```

Percentages MUST sum to 100. Each branch routes to a distinct SEND activity
with a different message template.

### RANDOM_SPLIT

```json
{
  "random-split": {
    "Type": "RANDOM_SPLIT",
    "Branches": [
      {"Id": "path-1", "Percentage": 50, "NextActivity": "send-path1"},
      {"Id": "path-2", "Percentage": 50, "NextActivity": "send-path2"}
    ]
  }
}
```

RANDOM_SPLIT differs from MULTIVARIATE_SPLIT in that the split is purely
random with no condition evaluation. Use RANDOM_SPLIT for simple holdout
testing; use MULTIVARIATE_SPLIT when tracking variant performance.

### SEND activity

```json
{
  "send-welcome": {
    "Type": "SEND",
    "MessageConfiguration": {
      "EmailTemplate": {"Name": "welcome-email"},
      "PushTemplate": {"Name": "welcome-push"}
    },
    "NextActivity": "wait-1day"
  }
}
```

A SEND can include multiple channels — Pinpoint sends to each endpoint via
its registered channel. If an endpoint has both email and push, it receives
both.

### Journey validation checklist

Before deploying a journey, validate:

1. **DAG (no cycles):** trace every path from ENTRY to END. If any path
   loops back, the journey is invalid.
2. **Every non-END activity has `NextActivity`:** an open activity leaves
   endpoints stuck.
3. **At least one `END` activity:** every path must terminate.
4. **All referenced activities exist:** every `NextActivity`, `TrueActivity`,
   `FalseActivity`, and `Branches[].NextActivity` must reference an activity
   in the `Activities` map.
5. **MULTIVARIATE/RANDOM percentages sum to 100.**
6. **Event-based WAITs have a timeout** (unless intentional indefinite wait).

## A/B test campaigns

### Campaign-level A/B test (holdout + treatments)

```json
{
  "Name": "subject-line-test",
  "SegmentId": "seg-all",
  "HoldoutPercent": 10,
  "AdditionalTreatments": [
    {"Id": "b", "MessageConfiguration": {"EmailTemplate": {"Name": "subject-b"}}, "SizePercent": 45},
    {"Id": "c", "MessageConfiguration": {"EmailTemplate": {"Name": "subject-c"}}, "SizePercent": 45}
  ],
  "MessageConfiguration": {"EmailTemplate": {"Name": "subject-a"}},
  "Schedule": {"StartTime": "IMMEDIATE"}
}
```

**How it works:**
1. `HoldoutPercent` (10%) receives NOTHING (control group).
2. The remaining 90% is split across treatments: 45% treatment-b, 45%
   treatment-c. The default message (treatment-a) gets 0% unless explicitly
   allocated.
3. To include treatment-a: set `SizePercent: 30` on treatments b and c (30
   + 30 + 30 = 90, leaving 30 for the default treatment-a).

**Treatment percentages + holdout MUST sum to 100.**

### Journey-level A/B test (multivariate split)

Use a MULTIVARIATE_SPLIT activity at the start of the journey to split
endpoints into variants. Each variant follows a different path with
different messaging. Measure conversion at the END activity.

### Measurement

| Metric | Email | SMS | Push |
|---|---|---|---|
| Send | CloudWatch, event stream | CloudWatch, event stream | CloudWatch, event stream |
| Delivery | SES bounce/complaint | Delivery receipt | APNs/FCM feedback |
| Open | Email open pixel | N/A | App foreground |
| Click | Link redirect tracking | Short link tracking | Deep link open |
| Conversion | Custom event via SDK | Custom event via SDK | Custom event via SDK |

Use the event stream to Kinesis for real-time measurement. Pinpoint
analytics dashboards show aggregate open/click/conversion rates per
treatment.

## Event streams (Kinesis)

### Configuration

```bash
aws pinpoint put-event-stream \
  --application-id <id> \
  --write-event-stream '{
    "DestinationStreamArn": "arn:aws:kinesis:us-east-1:111111111111:stream/pinpoint-events",
    "RoleArn": "arn:aws:iam::111111111111:role/PinpointEventStream"
  }'
```

### IAM role requirements

The role MUST trust `pinpoint.amazonaws.com` and grant:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["kinesis:PutRecord", "kinesis:PutRecords"],
    "Resource": "arn:aws:kinesis:us-east-1:111111111111:stream/pinpoint-events"
  }]
}
```

### Event types

The stream captures:

| Event category | Events |
|---|---|
| Campaign | `_campaign.send`, `_campaign.open`, `_campaign.click`, `_campaign.delivered`, `_campaign.bounce` |
| Journey | `_journey.send`, `_journey.open`, `_journey.click` |
| Custom | Any custom event emitted via the SDK (e.g., `purchase`, `app_open`) |
| Session | `_session.start`, `_session.stop` |

### Event schema (Kinesis record)

```json
{
  "event_type": "_campaign.open",
  "event_timestamp": "2026-08-10T12:00:00Z",
  "arrival_timestamp": "2026-08-10T12:00:01Z",
  "application": {"app_id": "app-abc123"},
  "client": {"client_id": "endpoint-xyz"},
  "session": {"session_id": "sess-123"},
  "attributes": {"campaign_id": "camp-456", "campaign_activity_id": "act-789"},
  "metrics": {}
}
```

Consume the stream with Kinesis Data Analytics, Firehose (to S3/OpenSearch),
or a Lambda function for real-time processing.

## In-app messaging

### Configuration within a campaign

```json
{
  "MessageConfiguration": {
    "InAppMessage": {
      "Content": [{
        "Header": "Welcome!",
        "Body": "Complete your profile to get started.",
        "Buttons": [{
          "Text": "Get Started",
          "Action": {"Type": "DEEP_LINK", "Link": "myapp://onboarding"}
        }],
        "BackgroundColor": "#FFFFFF",
        "TextColor": "#000000",
        "ImageURL": "https://cdn.example.com/welcome.png"
      }],
      "Layout": "BOTTOM_BANNER",
      "Duration": 300
    }
  }
}
```

### Layouts

| Layout | Description |
|---|---|
| `BOTTOM_BANNER` | Banner at bottom of screen |
| `TOP_BANNER` | Banner at top of screen |
| `MIDDLE_BANNER` | Centered card |
| `OVERLAYS` | Full-screen overlay |
| `CAROUSEL` | Swipeable carousel of content blocks |

`Duration` is in seconds (how long the message stays visible before
auto-dismissing). Requires Pinpoint mobile SDK integration (iOS, Android).

## ML-powered segment recommendations

```bash
aws pinpoint get-recommended-metrics \
  --application-id <id> \
  --recommended-action '{"SourceSegmentId": "seg-engaged", "RecommendationStrategy": "SIMILAR"}'
```

Pinpoint analyzes campaign engagement data (opens, clicks, conversions) and
identifies endpoints with similar behavioral patterns to an existing
segment. The recommended segment can be saved and used in campaigns.

**Use cases:**
- Audience expansion: find lookalike users similar to high-value customers.
- Win-back: find users similar to those who recently churned.
- Lookalike targeting: expand a seed segment for broader reach.

Recommendations require at least 30 days of campaign engagement data to
produce meaningful results.
