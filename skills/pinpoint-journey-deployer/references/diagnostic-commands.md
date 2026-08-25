# Diagnostic Commands — Pinpoint Journey Deployer

Diagnostic and measurement command listings moved out of the SKILL.md body. Loaded on demand.


## Step 12 — Journey analytics: KPI commands and metrics

Pinpoint provides journey-level analytics including participant count,
message delivery rates, open/click rates (email), and conversion
tracking (via event attribution).

```bash
aws pinpoint get-journey-date-range-kpi \
  --application-id "$APP_ID" \
  --journey-id "$JOURNEY_ID" \
  --start-time 2026-08-15T00:00:00Z \
  --end-time 2026-08-22T00:00:00Z \
  --kpi-name "UniqueEndpoints"
```

**Key metrics:**

| Metric | What it measures |
|---|---|
| `UniqueEndpoints` | Distinct participants in the journey |
| `TargetedEndpointCount` | Endpoints that received at least one message |
| `DeliveryRate` | Percentage of sent messages successfully delivered |
| `OpenRate` | Email open rate (requires open tracking) |
| `ClickRate` | Email click-through rate (requires click tracking) |
| `JourneyConversionRate` | Percentage of participants who converted |

**Conversion tracking:** define a conversion event (e.g.,
"purchase_completed") and Pinpoint attributes conversions back to the
journey. Use this to measure lift against the holdout group.
