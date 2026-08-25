# Worked Examples (load on demand) — CloudFront KeyValueStore Deployer

Use-case patterns moved verbatim from SKILL.md: the Step 5 feature-flag pattern and the Step 6 IP allowlist/blocklist pattern. The primary A/B testing worked example remains in SKILL.md.


---

## Step 5 — Feature flags via KVS (moved from SKILL.md)

Feature flags let you toggle functionality at the edge without
redeploying function code. The KVS stores the flag state; the function
reads it on every request.

**KVS data schema for feature flags:**

| Key | Value | Purpose |
|---|---|---|
| `flag-new-checkout` | `on` / `off` | New checkout flow toggle |
| `flag-beta-api` | `on` / `off` | Beta API endpoint toggle |
| `flag-maintenance-mode` | `on` / `off` | Maintenance page toggle |

**Function code for feature flag evaluation:**

```javascript
import cf from 'cloudfront';

const kvs = cf.openKvs();

function handler(event) {
    const request = event.request;

    // Maintenance mode — serve static page from edge
    if (kvs.get('flag-maintenance-mode') === 'on') {
        return {
            statusCode: 503,
            statusDescription: 'Service Unavailable',
            headers: { 'content-type': { value: 'text/html' } },
            body: '<html><body>Under maintenance.</body></html>'
        };
    }

    // Route to new checkout if flag is on
    if (kvs.get('flag-new-checkout') === 'on' &&
        request.uri.startsWith('/checkout')) {
        request.uri = request.uri.replace('/checkout', '/checkout-v2');
    }
    return request;
}
```

**Toggling a feature flag:**

```bash
ETAG=$(aws cloudfront-keyvaluestore describe-key-value-store \
  --kvs-arn "$KVS_ARN" --query 'ETag' --output text)

aws cloudfront-keyvaluestore put-key \
  --kvs-arn "$KVS_ARN" \
  --key "flag-new-checkout" \
  --value "on" \
  --if-match "$ETAG"
```

**Common mistake:** storing complex JSON in a KVS value and parsing it
in the function. KVS values are strings. While you CAN store JSON, the
3 KB per-value limit and 1 MB total limit make this impractical for
large configs. Use flat key-value pairs (`flag-x=on`).


---

## Step 6 — IP allowlists / blocklists via KVS (moved from SKILL.md)

KVS can store IP addresses or CIDR blocks for edge-side filtering. The
function checks the client IP against the KVS list and blocks or allows
the request.

**KVS data schema for IP lists:**

| Key | Value | Purpose |
|---|---|---|
| `blocklist-mode` | `on` / `off` | Master toggle |
| `ip-block-192.168.1.10` | `blocked` | Individual IP block |
| `cidr-block-10.0.0.0/8` | `blocked` | CIDR block |

**Function code for IP blocklist:**

```javascript
import cf from 'cloudfront';

const kvs = cf.openKvs();

function handler(event) {
    const request = event.request;
    if (kvs.get('blocklist-mode') !== 'on') return request;

    const clientIp = event.viewer.ip;
    if (kvs.get('ip-block-' + clientIp) === 'blocked') {
        return {
            statusCode: 403,
            statusDescription: 'Forbidden',
            headers: { 'content-type': { value: 'text/plain' } },
            body: 'Access denied.'
        };
    }
    return request;
}
```

**Important limitation:** CloudFront Functions have limited string
manipulation. CIDR range matching is complex in function code. For
CIDR-based blocking, prefer AWS WAF IP sets, which handle CIDR matching
natively and propagate instantly.

**KVS vs WAF for IP filtering:**

| Factor | KVS + Functions | AWS WAF IP Sets |
|---|---|---|
| Propagation speed | Seconds to minutes | Near-instant |
| CIDR support | Manual parsing in function | Native |
| Flexibility | Custom logic (time/path-based) | Declarative rules |
| Max entries | ~1000s (1 MB limit) | 10,000+ per IP set |
