# Managed Rules, Logging, and Bot Defense Guide — WAFv2 Web ACL Deployer

Deep reference on managed rule group internals, WCU costs, versioning,
scope-down statements, logging destination resource policies,
CAPTCHA / Challenge token lifecycle, and aggregate key selection.

## AWS-managed rule group internals

### AWSManagedRulesCommonRuleSet

The core rule set — 10 rules across 5 groups. Covers:

- **SizeRestrictions** — blocks bodies/headers/URI exceeding WAF limits.
- **GenericLFI** — Local File Inclusion (`../../`, `/etc/passwd`).
- **GenericRFI** — Remote File Inclusion (`http://`, `ftp://` in query).
- **GenericSQLi** — SQL injection patterns (`OR 1=1`, `UNION SELECT`).
- **GenericXSS** — Cross-site scripting (`<script>`, `javascript:`).
- **CrossSiteScripting** — deeper XSS inspection on body/header/URI.

**WCU cost:** ~700 WCUs.
**Rule group version:** pin to a specific version for production stability.

### AWSManagedRulesSQLiRuleSet

SQL injection signatures — deeper SQLi coverage beyond the Core
Rule Set. Inspects query args, body, URI, headers.

**WCU cost:** ~200 WCUs.
**Priority:** typically 20 (after Common).

### AWSManagedRulesLinuxRuleSet / WindowsRuleSet

OS-specific command injection:
- **Linux:** `/etc/passwd`, `/bin/sh`, `wget`, `curl`, bash escapes.
- **Windows:** PowerShell (`powershell.exe`, `Invoke-`), `cmd.exe`, registry.

**WCU cost:** ~200 each.

### AWSManagedRulesAmazonIpReputationList

AWS threat intelligence — IPs associated with bots, malware command
and control, and scanners. Updated automatically.

**WCU cost:** ~25 WCUs.

### AWSManagedRulesAnonymousIpList

Tor exit nodes, anonymous proxies, VPNs, and hosting/datacenter
ranges. Useful for blocking automated tools.

**WCU cost:** ~25 WCUs.

## Subscription rule group internals

### AWSManagedRulesBotControlRuleSet

Categorizes requests into bot categories. Requires Marketplace
subscription. Per-request billing.

**Categories:**
- `CategorySearchEngine` — Googlebot, Bingbot (allow these for SEO).
- `CategoryMonitoring` — uptime monitors (Pingdom, UptimeRobot).
- `CategoryScraping` — scrapers and content extractors.
- `CategorySpam` — known spam IPs.
- `CategoryAutomated` — scripted clients (curl, Python requests).
- `CategoryCommon` — generic bots.

**WCU cost:** ~50 WCUs.
**Overrides:** per-category allow/block/count. Common pattern: allow
`CategorySearchEngine`, block `CategorySpam`, count everything else.

```json
{
  "ManagedRuleGroupStatement": {
    "VendorName": "AWS",
    "Name": "AWSManagedRulesBotControlRuleSet",
    "ManagedRuleGroupConfigs": [{
      "AWSManagedRulesBotControlRuleSet": {
        "InspectionLevel": "COMMON"
      }
    }],
    "RuleActionOverrides": [
      {
        "Name": "CategorySearchEngine",
        "ActionToUse": { "Allow": {} }
      },
      {
        "Name": "CategorySpam",
        "ActionToUse": { "Block": {} }
      }
    ]
  }
}
```

### AWSManagedRulesATPRuleSet

Account Takeover Prevention. Inspects login endpoints for credential
stuffing, brute force, and anomalous patterns. Integrates with AWS
threat-intel (HaveIBeenPwned-style compromised credential lists).

**Required configuration:**
- `LoginPath` — exact URI path (e.g., `/api/v1/login`).
- `PayloadType` — `JSON` or `FORM_ENCODED`.
- `UsernameField.Identifier` — JSON key or form field name for username.
- `PasswordField.Identifier` — JSON key or form field name for password.

**WCU cost:** ~50 WCUs.
**Enforcement modes:**
- `Count` (recommended for first 1-2 weeks) — measure without blocking.
- `Block` — block credential stuffing requests.

**ATP also supports:**
- `RegisterURIPath` — registration/signup endpoint for ACFP.
- `EnableRegexInPath` — use regex for path matching.

### AWSManagedRulesACFPRuleSet

Account Creation Fraud Prevention. Detects abusive signups, disposable
email addresses, and bot-driven registration.

**Required configuration:**
- `RegistrationPath` — signup endpoint.
- `PayloadType` — `JSON` or `FORM_ENCODED`.
- `EmailField.Identifier`, `UsernameField.Identifier`,
  `PasswordField.Identifier`.

## Versioning and AGENTIC mode

Managed rule groups are versioned. By default, WAF uses `Latest` —
which can introduce new rules that change traffic behavior.

**Versioning strategies:**
- **Pinned version:** `Version: "2.1.0"` — stable, does not change.
  Update manually after testing.
- **AGENTIC:** `Versioning: { Type: "AGENTIC" }` — auto-updates to
  the latest version. Faster to adopt new protections but riskier.
- **Latest (default):** same as AGENTIC for most rule groups.

For production, pin to a specific version. Update quarterly after
testing in a staging Web ACL.

## Scope-down statements

A scope-down statement limits which requests a managed rule group
or rate-based rule evaluates. Use `ScopeDownStatement` to narrow
inspection:

```json
{
  "ManagedRuleGroupStatement": {
    "VendorName": "AWS",
    "Name": "AWSManagedRulesATPRuleSet",
    "ScopeDownStatement": {
      "ByteMatchStatement": {
        "SearchString": "/api/v1/login",
        "FieldToMatch": { "UriPath": {} },
        "PositionalConstraint": "STARTS_WITH"
      }
    },
    "ManagedRuleGroupConfigs": [...]
  }
}
```

Without scope-down, managed rule groups inspect all requests —
consuming WCUs and potentially false-positiving on non-target paths.

## Logging destination resource policies

### Kinesis Firehose

The Firehose delivery stream MUST be named with the prefix
`aws-waf-logs-`. WAF validates this at `PutLoggingConfiguration`
time. The delivery stream's IAM role must allow Firehose to write
to the S3 bucket.

### CloudWatch Logs

The log group's resource policy MUST allow
`delivery.logs.amazonaws.com`:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "delivery.logs.amazonaws.com" },
    "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
    "Resource": "arn:aws:logs:<region>:<account>:log-group:<group-name>:*"
  }]
}
```

Apply via `aws logs put-resource-policy`.

### S3 (via Firehose)

WAF does NOT write directly to S3. The flow is:
WAF → Firehose → S3. The S3 bucket policy must allow Firehose
(`firehose.amazonaws.com`) to `s3:PutObject`. The Firehose
delivery stream's IAM role handles the write.

## Log fields

WAF logs are JSON objects. Key fields:

| Field | What it contains |
|---|---|
| `timestamp` | Epoch time of the request |
| `action` | `ALLOW`, `BLOCK`, `COUNT`, `CAPTCHA`, `CHALLENGE` |
| `terminatingRuleId` | Rule that made the final decision |
| `terminatingRuleType` | `RATE_BASED`, `REGULAR`, `MANAGED_RULE_GROUP` |
| `httpRequest` | Client IP, country, URI, method, headers |
| `requestHeadersInserted` | Custom headers added by WAF |
| `labels` | WAF labels applied (for label-based matching) |
| `ruleGroupList` | Managed rule groups evaluated |
| `nonTerminatingMatchingRules` | Rules that matched with Count |
| `rateBasedRuleList` | Rate-based rules that triggered |
| `responseCodeSent` | HTTP status returned to client |

**Excluding fields:** use `RedactedFields` to remove sensitive fields
(Authorization header, cookies) from logs:

```json
{
  "RedactedFields": [
    { "SingleHeader": { "Name": "Authorization" } },
    { "SingleHeader": { "Name": "Cookie" } }
  ]
}
```

## CAPTCHA and Challenge token lifecycle

When a CAPTCHA or Challenge rule matches:

1. **Token check:** WAF checks for a valid token in the request
   (cookie `aws-waf-token` or header `x-aws-waf-token`).
2. **Valid token:** request is allowed (token proves the client
   passed a challenge in the last ~300 seconds).
3. **Invalid/missing token:**
   - **CAPTCHA:** WAF returns HTTP 405 with a JavaScript interstitial.
     The browser renders the CAPTCHA, solves it (~5-15 seconds), and
     retries the request with a valid token.
   - **Challenge:** WAF returns HTTP 202 with a silent JavaScript
     challenge. The browser solves it in ~5 seconds (no user
     interaction) and retries.
4. **Token issuance:** on successful solve, WAF sets the
   `aws-waf-token` cookie (domain-scoped). Subsequent requests in
   the token's validity window are allowed.

**Token domains:** tokens can be shared across Web ACLs in the same
account/Region by specifying allowed domains. This reduces friction
for users navigating across properties.

**Application integration SDK:**
- **JavaScript (browser):** load the `aws-waf` SDK via the integration
  snippet, call `AwsWafIntegration.fetch()` instead of `fetch()`. The
  SDK attaches the token cookie to all requests.
- **Mobile (iOS/Android):** native SDKs for CAPTCHA solving.
- **API clients:** for non-browser clients, use the Challenge API to
  obtain tokens programmatically.

## Aggregate key selection for rate-based rules

| Scenario | Recommended key | Why |
|---|---|---|
| Direct client → ALB | `IP` | Source IP is the client's real IP |
| Client → CloudFront → origin | `FORWARDED_IP` (`X-Forwarded-For`, `FIRST`) | CloudFront terminates TCP; source IP is the edge node |
| Client → ALB → target | `FORWARDED_IP` or `IP` | ALB preserves source IP by default; use `IP` if not behind another proxy |
| Per-endpoint rate limit | `URI` | Rate-limit each path independently |
| Per-method rate limit | `HTTP_METHOD` | Limit POST/PUT separately from GET |
| Per-API-key rate limit | `QUERY_STRING` or `HEADER` | Aggregate by API key value |
| Behind WAF in front of API Gateway | `FORWARDED_IP` | API Gateway sees the WAF IP; use forwarded header |

**FORWARDED_IP pitfalls:**
- `X-Forwarded-For` is comma-separated: `client, proxy1, proxy2`.
- `Position: FIRST` takes the leftmost IP (original client).
- `Position: LAST` takes the rightmost (closest proxy).
- `FallbackBehavior: MATCH` — if the header is absent, all
  headerless requests share a single bucket (rate-limit triggers if
  combined traffic exceeds the limit). Use when most clients send
  the header.
- `FallbackBehavior: NO_MATCH` — if the header is absent, the rule
  does not count those requests. Use when headerless traffic is
  expected and should not be rate-limited.

**Spoofing risk:** `X-Forwarded-For` is client-controllable unless
the proxy (ALB, CloudFront) overwrites it. Configure the proxy to
set `X-Forwarded-For` from the real source IP, not append the
client-provided value. Without this, attackers can spoof unique IPs
to evade rate limiting.
