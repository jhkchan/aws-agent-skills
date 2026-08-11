# Segments and Dimensions — Pinpoint Segment Deployer

Deep reference on dynamic vs static segments, dimension types
(Demographic, Behavior, UserAttributes, Attributes, Location, Metrics),
dimension operators (INCLUSIVE, EXCLUSIVE, CONTAINS), composition
(ALL vs ANY, group Include), and the dynamic-segment recompute
behavior. Loaded on demand by the skill — kept out of the main
SKILL.md body so the provisioning procedure stays scannable.

## Segment fundamentals

### Dynamic vs static — the core distinction

A Pinpoint segment is one of two types:

| Type | Definition | Updates | Created via |
|---|---|---|---|
| Dynamic | Defined by Dimensions (Demographic, Behavior, UserAttributes, etc.) | Recomputes on every evaluation (campaign send, journey entry, get-segment-estimate call) | `create-segment` with `SegmentGroups` |
| Static (Imported) | Imported endpoint IDs from CSV or S3 | Pinned at import; does NOT auto-refresh | `create-import-job` with `DefineSegment: true` |

**The recompute behavior is the critical distinction.** A dynamic
segment that resolved to 100,000 endpoints at design time may
resolve to 80,000 (or 120,000) at send time, because endpoints age
out of (or age into) the dimension criteria between evaluations.

```text
Dynamic segment lifecycle:
  T0 (creation):       resolves to endpoints matching dimensions at T0
  T0+7d (send time):   re-evaluates dimensions against current endpoint state
                       → some T0 endpoints no longer match (dropped)
                       → new endpoints now match (added)

Static segment lifecycle:
  T0 (import):         resolves to the exact endpoint IDs in the CSV/S3 snapshot
  T0+7d (send time):   still the same endpoint IDs (no re-evaluation)
```

### When to use dynamic vs static

| Use case | Segment type | Why |
|---|---|---|
| "Active in last 7 days" | Dynamic | Criteria should track user behavior over time |
| "US mobile users" | Dynamic | Demographic criteria; new users match as they sign up |
| "Loyalty tier = gold" | Dynamic | UserAttributes; tier changes propagate automatically |
| "Black Friday 2025 purchasers" | Static | One-time snapshot; the list of purchasers is fixed |
| "Churned users Q3" | Static | Historical cohort; the membership doesn't change |
| "Imported CRM list" | Static | External list; Pinpoint cannot re-evaluate external state |

## Dimension types

### Demographic

Filters on built-in endpoint attributes: Channel, AppVersion,
DeviceType, Make, Model, Platform.

```json
{
  "Demographic": {
    "Channel": {"DimensionType": "INCLUSIVE", "Values": ["GCM", "APNS"]},
    "DeviceType": {"DimensionType": "INCLUSIVE", "Values": ["ios", "android"]},
    "AppVersion": {"DimensionType": "INCLUSIVE", "Values": ["1.2.0", "1.2.1"]}
  }
}
```

### Behavior

Filters on recency of activity. `RecencyType` is `ACTIVE` (performed
an event recently) or `INACTIVE` (no event recently). `Duration` is
`DAY_1`, `DAY_3`, `DAY_7`, `DAY_14`, `DAY_30`.

```json
{
  "Behavior": {
    "Recency": {"Duration": "DAY_7", "RecencyType": "ACTIVE"}
  }
}
```

### UserAttributes

Filters on custom user-level attributes (set on the User object, not
the Endpoint). Key-value pairs with type and values.

```json
{
  "UserAttributes": {
    "loyalty_tier": {"DimensionType": "INCLUSIVE", "Values": ["gold", "platinum"]},
    "signup_date": {"DimensionType": "BEFORE", "Values": ["2025-01-01"]}
  }
}
```

### Attributes

Filters on custom endpoint-level attributes (set on the Endpoint
object). Different from UserAttributes — endpoint attributes are
per-device/per-channel.

```json
{
  "Attributes": {
    "last_viewed_category": {"DimensionType": "CONTAINS", "Values": ["electronics"]}
  }
}
```

### Location

Filters on geographic attributes: Country, Region, PostalCode, City.

```json
{
  "Location": {
    "Country": {"DimensionType": "INCLUSIVE", "Values": ["US", "CA"]}
  }
}
```

### Metrics

Filters on aggregate metrics (numeric attributes computed over
time): session count, total revenue, etc. Operators: GREATER_THAN,
LESS_THAN, BETWEEN.

```json
{
  "Metrics": {
    "session_count": {"ComparisonOperator": "GREATER_THAN", "Value": 5}
  }
}
```

## Dimension operators

| Operator | Applies to | Behavior |
|---|---|---|
| `INCLUSIVE` | All dimensions | Endpoint matches if attribute is IN the values list |
| `EXCLUSIVE` | All dimensions | Endpoint matches if attribute is NOT IN the values list |
| `CONTAINS` | String attributes only | Substring match (e.g., "electronics" matches "consumer_electronics") |
| `BEFORE` / `AFTER` / `BETWEEN` | Date attributes | Date comparison |
| `GREATER_THAN` / `LESS_THAN` / `BETWEEN` | Numeric (Metrics) | Numeric comparison |

## Composition: ALL vs ANY

Two composition levels exist:

1. **Within a group** (`SourceType`): does the endpoint need to match
   ALL dimensions in the group, or ANY of them?
2. **Across groups** (`Include`): does the endpoint need to match ALL
   groups, or ANY group?

```json
{
  "SegmentGroups": {
    "Groups": [
      {
        "Dimensions": [/* list of dimensions */],
        "SourceType": "ALL",  // ALL = AND, ANY = OR
        "Type": "ANY"
      }
    ],
    "Include": "ALL"  // ALL = must match all groups, ANY = any group
  }
}
```

**Common mistake:** using `ANY` when `ALL` is intended. "Users in US
OR DeviceType=iOS" matches every iOS user globally; "Users in US AND
DeviceType=iOS" matches only US iOS users. The default in many
console flows is `ANY`; verify before saving.

## Verifying segment resolution

Always verify segment resolution via `get-segment-estimate` BEFORE
wiring the segment into a campaign or journey. A 0-endpoint segment
reaches no one.

```bash
aws pinpoint get-segment-estimate \
  --application-id app-abc123 \
  --segment-id <segment-id> \
  --query 'SegmentResponse'
```

For dynamic segments, re-verify close to send time. The resolution
can change between design time and send time.

## Terraform example

```hcl
resource "aws_pinpoint_segment" "active_mobile" {
  application_id = aws_pinpoint_app.main.application_id
  name           = "active-mobile-7d"

  segment_groups {
    groups {
      source_type = "ALL"
      dimensions {
        behavior {
          recency {
            duration    = "DAY_7"
            recency_type = "ACTIVE"
          }
        }
      }
      dimensions {
        demographic {
          channel {
            dimension_type = "INCLUSIVE"
            values         = ["GCM", "APNS"]
          }
        }
      }
    }
    include = "ALL"
  }
}
```

## Common segment pitfalls

1. **Treating segments as static lists.** Dynamic segments recompute
   on every evaluation. The endpoint set at design time ≠ the
   endpoint set at send time. Re-verify via `get-segment-estimate`.

2. **Using ANY when ALL is intended.** "US OR iOS" matches every iOS
   user globally. "US AND iOS" matches only US iOS users. Verify
   `SourceType` and `Include` before saving.

3. **Filtering on an attribute no endpoint has.** A dimension
   filtering on `loyalty_tier=gold` resolves to 0 endpoints if no
   endpoint has `loyalty_tier` set. Verify endpoints have the
   required attributes via `get-endpoint` or attribute coverage
   reports.

4. **Imported segments do not auto-refresh.** A static segment
   imported from S3 is pinned at import time. To refresh, re-run the
   import job. Some operators expect the static segment to "pick up
   new endpoints" — it does not.

5. **Behavior dimension assumes Pinpoint SDK events.** The `Behavior`
   dimension requires events to be sent to Pinpoint via the mobile /
   web SDK. Without SDK events, the Behavior dimension resolves to 0
   endpoints.
