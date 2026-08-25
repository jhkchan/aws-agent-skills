# Advanced Patterns — Pinpoint Journey Deployer

Deep-dive material moved out of the SKILL.md body so the procedure stays scannable. Loaded on demand.


## Common misconceptions (from Mindset)

- **"Journey entry is always segment-based."** It is NOT. Entry can be
  event-based (real-time trigger when a participant performs an event)
  or segment-based (bulk add of all segment members at the scheduled
  start time). A baseline model defaults to segment-based and misses
  real-time behavioral triggers. The correct model explicitly chooses
  based on whether the journey is reactive (event) or proactive
  (segment).

- **"Conditional split and multivariate split are the same."** They are
  NOT. A conditional split evaluates an EVENT ATTRIBUTE or dimension
  against the journey participant (yes/no branch — did the user perform
  the event?). A multivariate split assigns participants RANDOMLY by
  percentage (no condition — purely for A/B testing). Confusing them
  leads to journeys that either never branch (random instead of
  conditional) or bias results (conditional instead of random).

- **"Quiet time cancels pending messages."** It does NOT. Quiet time
  HOLDS message sends during the configured hours/days. When the quiet
  window ends, held messages are delivered. This means a participant
  may receive a message outside the intended journey cadence. A
  baseline model assumes quiet time drops the message; the correct
  model knows it merely delays it and designs wait activities
  accordingly.


## Configuration dependency graph — sequencing notes

Pinpoint journey configurations are NOT independent. The entry
strategy determines what activities are valid. Conditional splits need
event definitions. Multivariate splits need percentages summing to 100.
Send message activities need configured channels (email/SMS/push).
Quiet time needs timezone alignment with the schedule. Journey limits
need to respect downstream channel throughput. Use this graph to
sequence provisioning.


## Cross-dependency gotchas

**The entry-strategy and quiet-time rows are the ones a baseline model
misses.** Entry strategy determines the entire journey semantics
(real-time vs bulk). Quiet time holds but does not cancel — a baseline
assumes cancellation and designs wait activities incorrectly. The
procedure below forces explicit decisions on each.

**Cross-dependency gotchas:**
- A conditional split evaluates an event attribute. The event must be
  recorded by the participant DURING the journey (not before entry).
  If the event has no attributes, the yes branch never fires.
- Multivariate split percentages must sum to exactly 100. A
  misconfigured split (e.g., 50/40) will cause an API error or
  undefined behavior.
- Quiet time interacts with wait activities: if a wait ends during a
  quiet period, the subsequent send is held until the quiet window
  closes. This shifts the effective journey cadence.
- Journey limits are evaluated at entry. Once a participant is IN the
  journey, they traverse all activities regardless of the total cap.
- A holdout suppresses participants at entry — they never start the
  journey at all. This is different from a multivariate split branch
  that sends no message (the participant still enters the journey).


## Expert heuristic: event-based vs segment-based entry

A baseline model defaults to segment-based entry. The correct heuristic
recognizes the two modes serve fundamentally different use cases.

```text
Event-based (real-time): participant enters IMMEDIATELY when an event fires.
  Use case: reactive/behavioral (abandoned cart, post-purchase, signup).
  Example: "When user abandons cart, wait 1h, send email reminder"

Segment-based (bulk): all segment members enter at scheduled start time.
  Use case: proactive/broadcast (weekly newsletter, seasonal promo).
  Example: "Monday 9am, send digest to 'active_users' segment"

Key difference: event-based is 1:1 real-time; segment-based is 1:many scheduled.
```

**Key implication:** event-based is for behavioral triggers where timing
matters (the user just did something). Segment-based is for broadcasts
where the journey is time-scheduled.


## Expert heuristic: conditional split evaluates event attributes

A baseline model treats conditional split as a random branch. The
correct heuristic recognizes it evaluates an EVENT ATTRIBUTE against the
journey participant.

```text
Conditional split (abandoned cart recovery):
  Participant enters (event: cart_abandoned) → Wait 1 hour
  → Conditional split: Did participant perform "purchase_completed"?
      YES → Exit (converted — no reminder needed)
      NO  → Send email → Wait 24h → Send SMS

The split evaluates events recorded DURING the journey window, not before.
```

**Key implication:** the conditional split requires a defined event
with attributes. If the event is not recorded during the journey, the
NO branch always fires. This is the most common cause of "my journey
never branches yes."


## Expert heuristic: quiet time holds, does not cancel

A baseline model assumes quiet time drops messages. The correct
heuristic recognizes that quiet time DELAYS delivery.

```text
Journey: Send email → Wait 24h → Send SMS
Quiet time: 22:00–08:00 UTC, Mon–Fri

Scenario A: email at 10:00 → delivered ✓; wait ends next day 10:00 → SMS ✓
Scenario B: email at 23:00 → HELD; delivered 08:00 next day (9h late)
  → wait starts from delivery; SMS shifted by 9 hours

Messages are NOT cancelled — they are held until the quiet window closes.
```

**Key implication:** if precise timing matters (e.g., a 7-day onboarding
cadence), quiet time causes cumulative drift. Use absolute-time waits
rather than duration-based to anchor to specific times.


## Step 13 — Recent features

- **Journey-run API (2023-2024):** `create-journey-run` triggers a
  segment-based run on-demand without modifying the schedule.
- **In-app message channel in journeys (2024):** Send activity supports
  in-app messages via Mobile SDK, enabling multi-channel paths.
- **Cross-channel journey analytics (2024-2025):** Unified dashboard
  aggregating email, SMS, push, and in-app metrics per journey.
- **Journey state management (2024-2025):** Enhanced pause/resume/restart
  APIs allow modifying activities without losing participant state.
- **ML-powered send-time optimization (2025):** Optimizes send times per
  participant based on engagement patterns, replacing fixed waits.
- **Amazon Q Business integration (2025):** Pre-built journey templates
  for Q Business-powered customer service workflows.
