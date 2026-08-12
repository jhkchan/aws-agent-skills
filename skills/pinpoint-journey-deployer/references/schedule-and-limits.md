# Schedule, Quiet Time, and Limits — Pinpoint Journey Deployer

Deep reference on journey scheduling (start/end date/time, timezone
selection), quiet time (off-hours suppression, hold-not-cancel
semantics), journey limits (daily cap, per-endpoint cap, total
participant cap), rate limits (SMS throughput, SES limits), and
journey analytics (KPIs, conversion tracking, A/B measurement).
Loaded on demand by the skill — kept out of the main SKILL.md body so
the provisioning procedure stays scannable.

## Journey schedule

### Start and end times

```json
{
  "Schedule": {
    "StartTime": "2026-08-15T09:00:00Z",
    "EndTime": "2026-09-15T09:00:00Z",
    "Timezone": "UTC"
  }
}
```

### Schedule semantics by entry mode

| Entry mode | StartTime meaning | EndTime meaning |
|---|---|---|
| Event-based | Journey begins ACCEPTING event triggers | Journey stops accepting new event triggers |
| Segment-based | All segment members are added to the journey | No new participants; existing participants continue |

**Critical for segment-based:** StartTime is when all segment members
enter simultaneously (subject to rate limits). The segment is evaluated
at StartTime — if it is empty then, zero participants enter.

**Critical for event-based:** StartTime is when the journey STARTS
listening for the trigger event. Events recorded before StartTime do
not cause entry.

### Timezone

Always specify the timezone explicitly. Use IANA timezone names
(`America/New_York`, `Europe/London`, `Asia/Tokyo`) or `UTC`.

```json
{"Timezone": "America/New_York"}
```

If the participant base spans multiple timezones, the schedule and
quiet time apply uniformly. For precise multi-timezone delivery,
create separate journeys per timezone with different segments.

## Journey state

A journey transitions through these states:

| State | Description |
|---|---|
| `DRAFT` | Journey is being configured; not live |
| `ACTIVE` (via start) | Journey is running and accepting participants |
| `PAUSED` | Journey temporarily halted; no new participants enter, existing participants hold |
| `COMPLETED` | EndTime reached or all participants have exited |
| `CANCELLED` | Journey cancelled; no further activity |

```bash
# Start a journey
aws pinpoint update-journey-state \
  --application-id "$APP_ID" \
  --journey-id "$JOURNEY_ID" \
  --journey-state-request '{"State": "ACTIVE"}'

# Pause a journey
aws pinpoint update-journey-state \
  --application-id "$APP_ID" \
  --journey-id "$JOURNEY_ID" \
  --journey-state-request '{"State": "PAUSED"}'
```

**Critical:** the entry mode (event-based vs segment-based) is LOCKED
when the journey transitions from DRAFT to ACTIVE. You cannot switch
modes after activation.

## Quiet time

### Configuration

```json
{
  "QuietTime": {
    "Start": "22:00",
    "End": "08:00",
    "DaysOfWeek": ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]
  }
}
```

If `DaysOfWeek` is omitted, quiet time applies every day.

### Hold-not-cancel semantics

**The #1 misconception about quiet time.** Quiet time HOLDS messages.
It does NOT cancel them.

```text
Scenario: Quiet time 22:00-08:00, participant reaches send activity at 23:00

Baseline assumption: "The message is dropped — it's night time."
Correct behavior:   "The message is HELD. At 08:00, it is delivered."

Implication: The participant receives the message 9 hours late.
This shifts the entire downstream journey cadence.
```

### Quiet time and wait interaction

If a wait activity ends during quiet time, the subsequent send is
held. This creates cumulative drift:

```text
Planned cadence:  email → 24h wait → SMS → 24h wait → push

With quiet time 22:00-08:00:
  Day 1, 10:00: email sent ✓
  Day 2, 10:00: SMS sent ✓ (not in quiet time)
  Day 3, 10:00: push sent ✓

BUT if email is delayed to 23:00 (held until 08:00 next day):
  Day 1, 23:00: email attempted → HELD
  Day 2, 08:00: email delivered (9h late)
  Day 3, 08:00: SMS delivered (was supposed to be Day 2)
  Day 4, 08:00: push delivered (was supposed to be Day 3)

The entire journey shifted by ~1 day due to one quiet-time hold.
```

### Recommendation: absolute-time waits

For precise cadence, use absolute-time waits instead of duration:

```json
{"Wait": {"WaitTime": {"Until": "2026-08-16T09:00:00Z"}}}
```

This anchors the send to a specific clock time regardless of when the
previous activity completed.

## Journey limits

### Limit types

| Limit | Field | Purpose |
|---|---|---|
| Daily message cap | `DailyCap` | Max messages per day across all participants |
| Per-endpoint cap | `MaximumEndpointSend` | Max messages to a single endpoint in the journey |
| Total participant cap | `TotalParticipantCap` | Max total participants across the journey lifetime |

```json
{
  "Limits": {
    "DailyCap": 50000,
    "MaximumEndpointSend": 3,
    "TotalParticipantCap": 500000
  }
}
```

### Evaluation point

**Limits are evaluated at entry.** Once a participant is IN the
journey, they traverse all activities regardless of the caps. Caps
prevent new participants from entering once the limit is reached.

### Cost management

Journey limits are the primary cost control mechanism:

```text
Cost = (messages sent) × (per-message cost)

Without limits, a journey with 1M participants × 5 messages each
= 5M messages at $0.00645/SMS = $32,250

With DailyCap=50000, the journey sends at most 50K messages/day,
spreading cost over time and capping daily spend.
```

## Rate limits and channel throughput

### SMS throughput

| Origination type | Throughput | Use case |
|---|---|---|
| Long code (10DLC) | 1 MPS | Low-volume, conversational |
| Short code | 100+ MPS | High-volume, marketing |
| Sender ID | Varies by country | Brand identity (not all countries) |
| Toll-free | 3 MPS | US/Canada medium-volume |

For high-volume SMS journeys, ensure you have sufficient origination
numbers. Pinpoint will throttle if the throughput limit is exceeded.

### Email throughput (SES)

Email sends are subject to SES sending limits (per-day and per-second).
Verify your SES limits can handle the journey volume:

```bash
aws ses get-send-quota
# Check Max24HourSend and MaxSendRate
```

### Push throughput

Push notifications via APNs and FCM have high throughput limits but
are subject to provider rate limiting. Pinpoint handles batching
automatically.

## Journey analytics

### Key KPIs

| KPI | What it measures |
|---|---|
| `UniqueEndpoints` | Distinct participants who entered the journey |
| `TargetedEndpointCount` | Endpoints that received at least one message |
| `EndpointsContacted` | Endpoints contacted (attempted) |
| `DeliveryRate` | Percentage of sent messages successfully delivered |
| `OpenRate` | Email open rate (requires open tracking pixel) |
| `ClickRate` | Email click-through rate (requires click tracking) |
| `JourneyConversionRate` | Percentage of participants who converted |

### Querying journey KPIs

```bash
aws pinpoint get-journey-date-range-kpi \
  --application-id "$APP_ID" \
  --journey-id "$JOURNEY_ID" \
  --start-time 2026-08-15T00:00:00Z \
  --end-time 2026-08-22T00:00:00Z \
  --kpi-name "UniqueEndpoints"
```

### Conversion tracking

Define a conversion event (e.g., `purchase_completed`). Pinpoint
attributes conversions back to the journey:

```json
{
  "analytics": {
    "ConversionEvents": ["purchase_completed"]
  }
}
```

### A/B lift measurement

To measure lift from an A/B test with holdout:

```text
Journey participants (90% of entrants): 10,000
  Variant A (50%): 5,000 → 250 conversions = 5.0%
  Variant B (50%): 5,000 → 300 conversions = 6.0%

Holdout (10% of entrants): 1,000
  No messages → 30 conversions = 3.0%

Lift over holdout:
  Variant A lift: (5.0% - 3.0%) / 3.0% = 66.7%
  Variant B lift: (6.0% - 3.0%) / 3.0% = 100.0%

Variant B outperforms Variant A AND both outperform the holdout.
```

Without the holdout, you can only compare Variant A vs Variant B
(relative), not measure absolute lift over no intervention.
