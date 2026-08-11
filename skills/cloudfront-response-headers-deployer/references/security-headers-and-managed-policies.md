# Security headers reference and managed policy matrix

Loaded on demand when the skill needs the security header semantics,
managed policy contents, or browser-compatibility matrix.

## Security header semantics

### Content-Security-Policy (CSP)

| Directive | Recommended | Why |
|---|---|---|
| `default-src` | `'self'` or `'none'` | Fallback for all resource types |
| `script-src` | `'self'` (add specific origins as needed) | Mitigates XSS |
| `object-src` | `'none'` | Blocks Flash/Java/plugins |
| `style-src` | `'self'` | Limits CSS sources |
| `img-src` | `'self' data:` | Allows data: URIs for inline images |
| `connect-src` | `'self'` | Limits XHR/WebSocket endpoints |
| `font-src` | `'self'` | Limits font sources |
| `frame-ancestors` | `'none'` | Clickjacking defense (modern browsers) |
| `base-uri` | `'self'` | Prevents `<base>` tag injection |
| `form-action` | `'self'` | Limits form submission targets |
| `upgrade-insecure-requests` | (present) | Auto-upgrade HTTP to HTTPS |

**Common CSP mistakes:**
- `'unsafe-inline'` in `script-src` — defeats XSS protection.
- `'unsafe-eval'` in `script-src` — needed by some frameworks (Angular,
  React dev mode) but defeats eval-based XSS protection.
- Wildcard origins (`https://*.example.com`) — overly broad.
- Missing `frame-ancestors` — only sets `X-Frame-Options`, which modern
  browsers ignore.

### Strict-Transport-Security (HSTS)

| Setting | Production | Testing | Why |
|---|---|---|---|
| `max-age` | 63072000 (2 years) | 300 (5 min) | HTTPS-only duration |
| `includeSubDomains` | true (verify all subdomains HTTPS) | false | Extends to all subdomains |
| `preload` | true (after registration at hstspreload.org) | false | Browser preload list |

**HSTS is irreversible** — once a browser sees the header, it enforces
HTTPS for the `max-age` duration. There is no "undo" header.

### X-Frame-Options

| Value | Browser behavior |
|---|---|
| `DENY` | Page cannot be framed at all |
| `SAMEORIGIN` | Page can be framed only by same-origin |
| `ALLOW-FROM uri` | DEPRECATED — ignored by modern browsers |

Modern browsers honor CSP `frame-ancestors` over `X-Frame-Options`.
Keep both for defense-in-depth (legacy browser support).

### X-Content-Type-Options

Always `nosniff`. Prevents MIME-type sniffing (browser guessing content
type from content rather than header). No other valid value.

### Referrer-Policy

| Value | Behavior |
|---|---|
| `no-referrer` | No referrer sent (breaks analytics) |
| `no-referrer-when-downgrade` | Default; sends referrer on HTTPS→HTTPS only |
| `same-origin` | Referrer sent only to same origin |
| `strict-origin` | Sends origin (scheme+host) only, no path |
| `strict-origin-when-cross-origin` | Recommended; full referrer same-origin, origin-only cross-origin |
| `origin-when-cross-origin` | Full referrer same-origin, origin-only cross-origin |
| `unsafe-url` | Always sends full referrer (NOT recommended) |

**For analytics-dependent sites:** use `strict-origin-when-cross-origin`.
Avoid `no-referrer` unless privacy trumps analytics.

### Permissions-Policy (formerly Feature-Policy)

| API | Recommended | Why |
|---|---|---|
| `camera` | `()` | Disable camera access |
| `microphone` | `()` | Disable microphone |
| `geolocation` | `()` | Disable location |
| `payment` | `()` | Disable Payment Request API |
| `usb` | `()` | Disable WebUSB |
| `magnetometer` | `()` | Disable sensor |
| `gyroscope` | `()` | Disable sensor |

Syntax: `camera=(), microphone=(), geolocation=()` (empty parens =
disabled). Use `camera=self` to allow same-origin only.

## Managed policy contents

### SecurityHeadersPolicy (ID: `0857826db9cffff310d5ad62955c9c26`)

```yaml
SecurityHeadersConfig:
  StrictTransportSecurity:
    AccessControlMaxAgeSec: 63072000
    IncludeSubdomains: true
    Preload: false  # note: managed policy does NOT preload
    Override: true
  XFrameOptions:
    FrameOption: DENY
    Override: true
  XContentTypeOptions:
    Override: true
  ReferrerPolicy:
    ReferrerPolicy: "strict-origin-when-cross-origin"
    Override: true
```

**Limitations:**
- No `Content-Security-Policy` — must be added via custom policy.
- No `Permissions-Policy` — must be added via custom policy.
- `Preload: false` — operator must opt in via custom policy for preload.

### SimpleCORS (ID: `608323ce734e4449839d234493be9c7c`)

```yaml
CorsConfig:
  AccessControlAllowOrigins:
    Items: ["*"]
    Quantity: 1
  AccessControlAllowMethods:
    Items: [GET, HEAD]
    Quantity: 2
  AccessControlAllowCredentials: false
  OriginOverride: true
```

**Limitations:**
- No preflight (`OPTIONS`) handling.
- No `Access-Control-Allow-Headers` config.
- `AllowCredentials: false` — cannot be used for cookie-bearing requests.

### CORS-with-preflight-and-SecurityHeadersPolicy
(ID: `5cc3b908-e619-4b99-88e5-2ca770afe08f`)

```yaml
CorsConfig:
  AccessControlAllowOrigins:
    Items: ["*"]
  AccessControlAllowMethods:
    Items: [GET, HEAD, OPTIONS, PUT, POST, PATCH, DELETE]
  AccessControlAllowHeaders:
    Items: ["*"]
  AccessControlAllowCredentials: false
  AccessControlMaxAgeSec: 86400
  OriginOverride: true
SecurityHeadersConfig:
  # Same as SecurityHeadersPolicy above
```

### CORSAndHTTPSecurityHeadersPolicy
(ID: `e0bbb029-0798-45b7-9b86-9e6a1c2670e4`)

```yaml
CorsConfig:
  AccessControlAllowOrigins:
    Items: ["*"]
  AccessControlAllowMethods:
    Items: [GET, HEAD]
  AccessControlAllowCredentials: false
  OriginOverride: true
SecurityHeadersConfig:
  # Same as SecurityHeadersPolicy above
```

## Decision matrix — managed vs custom

| Requirement | Recommended policy |
|---|---|
| Security headers only, no CSP, no Permissions-Policy | Managed `SecurityHeadersPolicy` |
| Simple CORS (read-only, `*` origin) | Managed `SimpleCORS` |
| CORS with preflight + security headers | Managed `CORS-with-preflight-and-SecurityHeadersPolicy` |
| CORS without preflight + security headers | Managed `CORSAndHTTPSecurityHeadersPolicy` |
| Custom CSP | Custom policy |
| Specific CORS origins (credentials) | Custom policy |
| Custom headers (Cache-Control override) | Custom policy |
| Removal headers (X-Powered-By) | Custom policy |
| Permissions-Policy | Custom policy |

## Browser compatibility

| Header | Chrome | Firefox | Safari | Edge |
|---|---|---|---|---|
| CSP | 25+ | 23+ | 7+ | 12+ |
| HSTS | 4+ | 4+ | 7+ | 12+ |
| X-Frame-Options | All | All | All | All |
| X-Content-Type-Options | All | All | All | All |
| Referrer-Policy | 56+ | 50+ | 11.1+ | 79+ |
| Permissions-Policy | 88+ | 74+ (behind flag) | 15.4+ | 88+ |
