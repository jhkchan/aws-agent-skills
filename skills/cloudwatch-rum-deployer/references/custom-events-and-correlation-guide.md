# Custom events, metrics, and X-Ray correlation — deep reference

This reference expands the SKILL.md custom event, custom metric,
X-Ray correlation, and Application Signals client correlation
sections with the event schemas, extraction semantics, header
propagation, and full NEVER list. Load when recording custom
events, configuring custom metrics, or wiring client/server
trace correlation.

## Custom event schema

### Required fields

```typescript
{
  type: '<event_type>',
  data: { /* arbitrary JSON, <= 64 KB serialized */ }
}
```

### `type` rules

- Alphanumeric + underscore only (`^[a-zA-Z0-9_]+$`).
- Hyphens, spaces, and special characters are rejected silently.
- Establish a convention: `<domain>_<action>` (e.g.,
  `checkout_complete`, `signup_submit`, `payment_failed`).
- Case-sensitive — `Checkout_Complete` and `checkout_complete`
  are different event types.

### `data` rules

- Any valid JSON object.
- Max 64 KB after serialization.
- Nested paths are addressable via JSON path in
  `put-metrics-destination` (e.g.,
  `$.event.data.cartValue`).

### Recording patterns

```typescript
// CDN pattern
cwr('recordEvent', {
  type: 'checkout_complete',
  data: { cartValue: 142.50, itemCount: 3, paymentMethod: 'card' }
});

// npm pattern
awsRum?.recordEvent({
  type: 'checkout_complete',
  data: { cartValue: 142.50, itemCount: 3, paymentMethod: 'card' }
});
```

### Built-in event types

The SDK records these automatically when the corresponding
telemetry is enabled:

| Event type | Telemetry | Source |
|---|---|---|
| `com.amazon.rum.performance-navigation` | performance | PerformanceNavigationTiming |
| `com.amazon.rum.performance-resource` | performance | PerformanceResourceTiming |
| `com.amazon.rum.lcp` | performance | LargestContentfulPaint |
| `com.amazon.rum.fid` | performance | FirstInputDelay |
| `com.amazon.rum.cls` | performance | CumulativeLayoutShift |
| `com.amazon.rum.inp` | performance | InteractionToNextPaint |
| `com.amazon.rum.http_request` | http | fetch / XHR |
| `com.amazon.rum.error` | errors | window.onerror + unhandledrejection |
| `com.amazon.rum.page_view` | (always) | page load + SPA route change |

Do NOT use these prefixes for custom events — they collide with
built-in extraction.

## Custom metric extraction

`put-metrics-destination` configures CloudWatch to derive a
metric from the custom event stream server-side. The metric
appears in the `AWS/RUM` namespace with dimensions
`ApplicationName` and `RumEventName`.

### CLI

```bash
aws rum put-metrics-destination \
  --app-monitor-name checkout-web-prod \
  --metric-definition-namespace AWS/RUM \
  --metric-definition-name CartValueTotal \
  --metric-definition-value-key '$.event.data.cartValue' \
  --region us-east-1
```

### Extraction semantics

- One value per event — the JSON path in `valueKey`.
- The path uses JSONPath-ish syntax (`$.event.data.<field>`).
- If the field is missing or non-numeric, the event is skipped
  (no metric emitted).
- Dimensions are FIXED: `ApplicationName` + `RumEventName`. You
  cannot add custom dimensions via `put-metrics-destination`.
- Up to 100 metric definitions per app monitor.

### Querying the derived metric

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/RUM \
  --metric-name CartValueTotal \
  --dimensions Name=ApplicationName,Value=checkout-web-prod \
               Name=RumEventName,Value=checkout_complete \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum,SampleCount,Average \
  --region us-east-1
```

### Alarming on the derived metric

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name checkout-cart-value-anomaly \
  --namespace AWS/RUM \
  --metric-name CartValueTotal \
  --dimensions Name=ApplicationName,Value=checkout-web-prod \
               Name=RumEventName,Value=checkout_complete \
  --period 300 --evaluation-periods 2 \
  --threshold 1000 --comparison-operator GreaterThanThreshold \
  --statistic Sum \
  --alarm-actions arn:aws:sns:us-east-1:111122223333:oncall
```

## X-Ray trace correlation — header propagation

RUM with `enableXRay: true` generates a client-side trace ID and
emits a client-side segment. The server joins the same trace by
reading the `X-Amzn-Trace-Id` header.

### Header format

```http
X-Amzn-Trace-Id: Root=1-<8hex>-<24hex>;Parent=<16hex>;Sampled=1
```

- `Root` — the trace ID (8 hex timestamp + 24 hex random).
- `Parent` — the parent segment ID (16 hex).
- `Sampled` — `1` if the trace is sampled; `0` otherwise.

### Server-side propagation by runtime

**Node.js (AWS X-Ray SDK):**

```javascript
const AWSXRay = require('aws-xray-sdk');
const app = AWSXRay.express.openSegment('checkout-api');
app.use(app);  // automatically reads X-Amzn-Trace-Id
```

**Python (Django):**

```python
from aws_xray_sdk.core import patch_all
from aws_xray_sdk.ext.django.middleware import XRayMiddleware

patch_all()
# Add XRayMiddleware to MIDDLEWARE in settings.py
```

**Java (Spring):**

```xml
<!-- aws-xray-recorder-sdk-spring configured via filter -->
<filter>
  <filter-name>AWSXRayServletFilter</filter-name>
  <filter-class>com.amazonaws.xray.javax.package.AWSXRayServletFilter</filter-class>
</filter>
```

**Go:**

```go
import "github.com/aws/aws-xray-sdk-go/xray"

func handler(w http.ResponseWriter, r *http.Request) {
    ctx := xray.GetSegment(r.Context())
    // ctx carries the trace propagated from X-Amzn-Trace-Id
}
```

### Sampling rule strategy

- **Default rule** — `FixedRate=0.05` (5%) is sufficient for
  most services. Raise to 0.5 (50%) for low-traffic endpoints.
- **Never use 0%.** A 0% sampling rule on the server blanks
  every client/server correlation; the client trace lands but
  the server trace does not.
- **Per-service rules** — for high-volume services, define a
  service-specific sampling rule with a lower `FixedRate`.

### Verifying correlation

```bash
aws xray get-trace-summaries \
  --start-time $(date -u -d '10 min ago' +%s) \
  --end-time $(date -u +%s) \
  --filter-expression 'service.id = "checkout-api"' \
  --region us-east-1 | jq '.TraceSummaries | length'
```

Each trace should show a client-side segment (`origin: "RUM"`)
connected to a server-side segment (`origin: "EC2" | "ECS" |
"EKS" | "Lambda"`).

## Application Signals client correlation

When RUM and Application Signals cover the same service
endpoint, CloudWatch auto-populates the
`AWS/ApplicationSignalsClient` namespace:

- **`ClientURL`** — the page origin (from RUM).
- **`ServiceName`** — the server-side service
  (`AWS_SERVICE_NAME`).
- **`Environment`** — the server-side environment.

### Verifying correlation

```bash
aws cloudwatch list-metrics --namespace AWS/ApplicationSignalsClient \
  --dimensions Name=ServiceName,Value=checkout-api \
  --region us-east-1
```

If the namespace stays empty after 15 minutes of traffic:

1. Confirm Application Signals is enabled on the server
   (`aws application-signals list-services` returns
   `checkout-api`).
2. Confirm X-Ray sampling rule `FixedRate > 0`.
3. Confirm the RUM domain matches the server endpoint that
   Application Signals discovered.
4. Confirm the RUM app monitor and the server workload are in
   the SAME Region.

### SLOs from client metrics

Application Signals SLOs can reference client-side metrics in
`AWS/ApplicationSignalsClient`:

```yaml
Type: AWS::ApplicationSignals::ServiceLevelObjective
Properties:
  Name: checkout-client-latency-slo
  Goal:
    Interval:
      RollingInterval: { DurationUnit: DAY, Duration: 28 }
    AttainmentGoal: 0.99
  RequestBasedSliConfig:
    MetricThreshold: 2.5  # seconds
    TotalRequestsMetric:
      MetricStat:
        Metric:
          Namespace: AWS/ApplicationSignalsClient
          MetricName: Latency
          Dimensions:
            - { Name: ServiceName, Value: checkout-api }
            - { Name: ClientURL, Value: https://checkout.example.com }
        Period: 60
        Stat: p95
```

## Full NEVER list

1. NEVER embed long-lived AWS access keys in JavaScript. The SDK
   MUST authenticate via a Cognito identity pool guest role or a
   web-identity role. Embedded keys leak to every site visitor.
2. NEVER set `cookieDomain` to a public suffix (`.com`, `.app`,
   `.io`). The cookie leaks across unrelated sites and corrupts
   session counts.
3. NEVER omit a domain from `AllowedOrigins`. RUM silently drops
   events from origins not on the list; the dashboard shows zero
   sessions and there is no error in the console.
4. NEVER set the server-side X-Ray sampling rule to 0% when X-Ray
   correlation is enabled. Client traces land, server traces do
   not, and the correlation is lost. Use the default 5% rule or
   higher.
5. NEVER recreate the app monitor with a new name. The name is
   embedded in every metric dimension, every alarm, and the IAM
   resource ARN. Renaming breaks every downstream alarm and
   dashboard. Update in-place or migrate deliberately.
6. NEVER use hyphens or special characters in custom event
   `type`. RUM rejects non-alphanumeric event types silently.
   Use snake_case.
7. NEVER scope the guest role's `rum:PutRumEvents` policy with a
   wildcard resource. A malicious script could write events to
   any app monitor in the account, polluting dashboards and
   alarming.
8. NEVER assume the CDN script tag auto-upgrades safely. Pin the
   SDK version in the `src` attribute. Auto-upgrades can break
   event schemas.
9. NEVER assume multi-Region correlation. RUM does not merge
   across Regions. Plan per-Region app monitors and per-Region
   dashboards.
10. NEVER attempt to evade ad blockers. uBlock Origin and
    similar block the RUM CDN script. RUM cannot bypass this;
    expect 5-15% session under-count. Document the limitation.

## Edge-case handling (extended)

### Event data oversized

Event `data` exceeding 64 KB after serialization is rejected.
Split the event into multiple smaller events, or move bulk data
to a backend log (CloudWatch Logs via PutLogEvents).

### Cookie blocked by browser

Some browsers (Safari ITP, Firefox ETP) block third-party
cookies. The RUM cookie is first-party when `cookieDomain`
matches the page host. If the SDK runs inside a cross-origin
iframe (e.g., a third-party checkout), the cookie is treated as
third-party and may be blocked. Fall back to `allowCookies:
false` and accept that session stitching is per-iframe-load.

### INP (Interaction to Next Paint)

RUM captures INP as the successor to FID. The dashboard surfaces
both during the transition period. INP is a better
responsiveness signal — it captures the worst interaction in a
visit, not just the first. Build dashboards on INP, not FID.

### Session timeout

Default session timeout is 30 minutes of inactivity. A user who
walks away and returns after 31 minutes starts a new session.
Tunable via `sessionLengthSeconds` in the SDK config (max
43200 seconds = 12 hours).

### Page view recording in SPAs

The SDK records a page view on initial load only. SPA route
changes do NOT trigger a page view unless you call
`awsRum.recordPageView(path)` explicitly in the router hook.
See the deployment CLI reference for per-framework patterns.

## Step 5 — X-Ray trace correlation (header propagation + sampling) (moved from SKILL.md)

When `enableXRay: true` (or `EnableXRay: true` on the app monitor),
the RUM SDK generates a client-side X-Ray trace ID at session
start, attaches it to every `PutRumEvents` batch, and emits a
client-side segment via `PutTraceSegments`.

For server-side correlation, the **server must propagate the same
trace ID** by reading the `X-Amzn-Trace-Id` request header:

```http
X-Amzn-Trace-Id: Root=1-<8hex>-<24hex>;Parent=<16hex>;Sampled=1
```

The server's X-Ray SDK reads the header and joins the trace. The
result: the X-Ray service map shows the client-side segment
(browser) connecting to the server segment (app), and the RUM
dashboard shows the linked server-side traces.

Without server-side header propagation, RUM still captures
client-side traces but they do NOT link to the server — the
X-Ray trace stops at the browser.

**Sampling rule on the server** — the server-side X-Ray sampling
rule must sample the trace ID. A 0% sampling rule on the server
blanks the correlation. Use the default 5% rule, or a higher rate
for low-traffic endpoints.

## Step 6 — Record custom events (CDN + npm patterns) (moved from SKILL.md)

Custom events extend RUM beyond auto-captured errors, performance,
and HTTP. Use them for funnel tracking, feature adoption, business
events:

```typescript
// CDN pattern
cwr('recordEvent', {
  type: 'checkout_complete',
  data: {
    cartValue: 142.50,
    itemCount: 3,
    paymentMethod: 'card'
  }
});

// npm pattern
awsRum?.recordEvent({
  type: 'checkout_complete',
  data: { cartValue: 142.50, itemCount: 3, paymentMethod: 'card' }
});
```

Event `type` is a free-form string but **must** be alphanumeric +
underscore (RUM rejects special characters in event types). Event
`data` is an arbitrary JSON object (max 64 KB after serialization).

## Step 7 — RUM custom metrics (put-metrics-destination) (moved from SKILL.md)

Custom events become CloudWatch custom metrics in the `AWS/RUM`
namespace automatically when you define a metric on the app
monitor:

```bash
aws rum put-metrics-destination \
  --app-monitor-name checkout-web-prod \
  --metric-definition-namespace AWS/RUM \
  --metric-definition-name CartValueTotal \
  --metric-definition-value-key '$.event.data.cartValue' \
  --region us-east-1
```

The metric appears in CloudWatch as
`AWS/RUM > ApplicationName=checkout-web-prod, RumEventName=checkout_complete`
with the value extracted from `event.data.cartValue` for every
event of type `checkout_complete`. Use this to build alarms and
dashboards on RUM-derived business metrics.

**Metric extraction limits:**
- One value per event (the `valueKey` JSON path).
- Up to 100 metric definitions per app monitor.
- Dimensions are fixed: `ApplicationName` and `RumEventName`.
