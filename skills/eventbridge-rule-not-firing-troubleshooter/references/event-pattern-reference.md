# EventBridge Event Pattern Reference Guide

Supplementary reference for the EventBridge Rule Not Firing
Troubleshooter skill. Loaded on-demand when a diagnostic needs exact
matching semantics, content-based filter operator behavior, JSON path
depth limits, or event structure validation.

## Event pattern matching model

An EventBridge event pattern is a declarative filter. Every key in the
pattern is a condition that the event MUST satisfy for the rule to fire.
All conditions are ANDed — there is no OR between top-level keys (use
`$or` for alternative branches, added in 2024).

### Top-level matched fields

| Pattern field | Event field | Match rule |
|---|---|---|
| `source` | `source` | Exact string (case-sensitive). Array = OR. |
| `detail-type` | `detail-type` | Exact string (case-sensitive). Array = OR. |
| `detail` | `detail` | Nested object matching. Content filters apply. |
| `account` | `account` | Exact string (12-digit account ID). Array = OR. |
| `region` | `region` | Exact string (e.g., "us-east-1"). Array = OR. |
| `resources` | `resources` | Exact ARN match. Array = OR. |

The `version`, `id`, and `time` fields are metadata and are NOT
pattern-matched.

### Exact-match semantics

```json
// Pattern
{"source": ["myapp.orders"]}

// Event that MATCHES
{"source": "myapp.orders", ...}

// Event that does NOT match
{"source": "myapp.orders.v2", ...}  // different string
{"source": "MyApp.Orders", ...}     // case difference
```

### Array = OR semantics

```json
// Pattern — matches if source is "a" OR "b"
{"source": ["a", "b"]}

// Matches: source = "a"
// Matches: source = "b"
// Does not match: source = "c"
```

## Content-based filtering operators

| Operator | Syntax | Works on | Example |
|---|---|---|---|
| `prefix` | `{"prefix": "abc"}` | String only | `{"source": [{"prefix": "aws."}]}` matches `"aws.ec2"`, `"aws.s3"` |
| `numeric` | `{"numeric": [op, val]}` | Number (JSON number type) | `{"numeric": [">=", 100]}` matches `150`, not `"150"` |
| `equals-ignore-case` | `{"equals-ignore-case": "abc"}` | String only | matches `"ABC"`, `"abc"`, `"AbC"` |
| `anything-but` | `{"anything-but": [vals]}` | String or number | `{"anything-but": ["cancelled"]}` matches everything except `"cancelled"` |
| `wildcard` | `{"wildcard": "abc-*"}` | String only | `{"wildcard": "ord-*"}` matches `"ord-123"`, not `"order-123"` |
| `cidr` | `{"cidr": "10.0.0.0/8"}` | String (IPv4 only) | matches `"10.1.2.3"`, not `"192.168.1.1"` |
| `exists` | `{"exists": true/false}` | Any type | `true` = field present; `false` = field absent |

### Common operator pitfalls

| Pattern | Event value | Result | Why |
|---|---|---|---|
| `{"prefix": "ord"}` | `123` (number) | No match | `prefix` works on strings only |
| `{"numeric": [">=", 100]}` | `"150"` (string) | No match | Value must be JSON number type |
| `{"exists": false}` | `{"field": null}` | No match | Field is present (value is null) — `exists: false` means ABSENT |
| `{"wildcard": "ord-?"}` | `"ord-1"` | No match | `?` is NOT supported; only `*` |
| `{"anything-but": ["x"]}` | (field missing) | No match | Missing field does not match anything-but |

## Nested JSON path depth limit

EventBridge resolves JSON paths in the `detail` object up to **10 levels**
deep. Paths at depth 11+ silently fail to resolve — the rule never fires.

```
$.detail                                    → depth 1
$.detail.a                                  → depth 2
$.detail.a.b                                → depth 3
$.detail.a.b.c                              → depth 4
$.detail.a.b.c.d                            → depth 5
$.detail.a.b.c.d.e                          → depth 6
$.detail.a.b.c.d.e.f                        → depth 7
$.detail.a.b.c.d.e.f.g                      → depth 8
$.detail.a.b.c.d.e.f.g.h                    → depth 9
$.detail.a.b.c.d.e.f.g.h.i                  → depth 10 (MAXIMUM)
$.detail.a.b.c.d.e.f.g.h.i.j                → depth 11 (FAILS SILENTLY)
```

**Mitigation:** Flatten deeply nested event structures before PutEvents,
or restructure the pattern to reference a shallower path.

## Event structure (canonical)

```json
{
  "version": "0",
  "id": "abc123-def456-...",
  "detail-type": "Order Created",
  "source": "myapp.orders",
  "account": "111111111111",
  "time": "2026-08-05T12:00:00Z",
  "region": "us-east-1",
  "resources": ["arn:aws:s3:::my-bucket/order-123"],
  "detail": {
    "orderId": "12345",
    "status": "confirmed",
    "amount": 150,
    "nested": {
      "customer": {
        "id": "cust-9912",
        "tier": "premium"
      }
    }
  }
}
```

### Pattern matching the above event

```json
{
  "source": ["myapp.orders"],
  "detail-type": ["Order Created"],
  "detail": {
    "status": ["confirmed"],
    "amount": [{"numeric": [">=", 100]}],
    "nested": {
      "customer": {
        "tier": ["premium"]
      }
    }
  }
}
```

## test-event-pattern API

The single most decisive probe in EventBridge diagnosis:

```bash
aws events test-event-pattern \
  --event-pattern '<pattern-json>' \
  --event '<event-json>' \
  --output json
```

Returns:
```json
{"Result": true}   // pattern matches event
{"Result": false}  // pattern does NOT match event
```

Always use this API before modifying a rule. Eyeball comparison is
wrong ~30% of the time due to case sensitivity, type mismatches, and
operator quirks.

## PutEvents response semantics

PutEvents returns HTTP 200 with a response body:

```json
{
  "FailedEntryCount": 0,
  "Entries": [{"EventId": "uuid-..."}]
}
```

- `FailedEntryCount: 0` means all entries were ingested onto the bus.
- This does NOT mean any rule fired. Rule matching is a separate step.
- A 200 response with `FailedEntryCount: 0` only confirms bus ingestion.

If `FailedEntryCount > 0`, the `Entries` array includes `ErrorCode` and
`ErrorMessage` for each failed entry.

## Pattern field match table (moved from SKILL.md)

| Pattern field | Event field | Match rule |
|---|---|---|
| `source` | `source` | Exact string match (case-sensitive). Array = OR. |
| `detail-type` | `detail-type` | Exact string match (case-sensitive). Array = OR. |
| `detail.{path}` | `detail.{path}` | Exact value match. Content filter operators apply. |
| `account` | `account` | Exact string match. Array = OR. |
| `region` | `region` | Exact string match. Array = OR. |
| `time` | `time` | Not matched as a pattern field (timestamp). Use content filters on `detail.time` if needed. |
| `resources` | `resources` | Exact ARN match. Array = OR. |

## Common pattern mismatch patterns (moved from SKILL.md)

Common mismatch patterns:

| Pattern | Event | Result | Fix |
|---|---|---|---|
| `source: ["myapp"]` | `source: "myapp.orders"` | No match | Use `source: ["myapp.orders"]` or `source: [{prefix: "myapp"}]` |
| `detail-type: ["Order Created"]` | `detail-type: "order created"` | No match | Case-sensitive — use exact casing |
| `detail: {status: ["confirmed"]}` | `detail: {status: "pending"}` | No match | Add "pending" to the array or change the condition |
| `detail: {amount: [100]}` | `detail: {amount: "100"}` | No match | Type mismatch — number vs string |
| `detail: {order: {id: ["123"]}}` | event has `detail.order.id = "123"` at depth 3 | Match (depth is within limit) | Verify depth ≤ 10 |

## Content filter operator validation tables (moved from SKILL.md)

| Operator | Syntax | Matches | Common error |
|---|---|---|---|
| `prefix` | `{"prefix": "ord"}` | Strings starting with "ord" | Applied to non-string value (number, boolean) |
| `numeric` | `{"numeric": [">=", 100]}` | Numbers ≥ 100 | Applied to string value `"100"` |
| `equals-ignore-case` | `{"equals-ignore-case": "abc"}` | String "abc" case-insensitive | Only works on strings, not numbers |
| `any-but` | `{"anything-but": ["cancelled"]}` | Any value except "cancelled" | Does not match null/undefined |
| `wildcard` | `{"wildcard": "ord-*"}` | Strings matching glob "ord-*" | Only `*` is supported (no `?`) |
| `cidr` | `{"cidr": "10.0.0.0/8"}` | IP addresses in CIDR range | Only IPv4 |
| `exists` | `{"exists": true}` | Field is present | `{"exists": false}` = field is absent |

Common content filter failure patterns:

| Pattern | Event | Result | Why |
|---|---|---|---|
| `{"prefix": "ord"}` on `detail.type` | `detail.type: 123` | No match | `prefix` works on strings only |
| `{"numeric": [">=", 100]}` on `detail.amount` | `detail.amount: "150"` | No match | Value is string, not number |
| `{"exists": true}` on `detail.optional` | Event has no `detail.optional` | No match | Field genuinely absent |
| `{"anything-but": ["x"]}` on `detail.tag` | Event has no `detail.tag` | No match | Missing field does not match anything-but |

## Nested depth limit illustration (moved from SKILL.md)

```text
detail                          → depth 1
detail.level1                   → depth 2
detail.level1.level2            → depth 3
...
detail.l1.l2.l3.l4.l5.l6.l7.l8.l9 → depth 10 (maximum)
detail.l1.l2.l3.l4.l5.l6.l7.l8.l9.l10 → depth 11 (FAILS SILENTLY)
```
