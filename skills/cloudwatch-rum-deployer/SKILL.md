---
name: cloudwatch-rum-deployer
description: >-
  Provisions CloudWatch RUM (Real User Monitoring) app monitors
  with production-grade defaults — domain allow-list, sample
  rate, cookie domain, telemetries (errors, performance, HTTP),
  X-Ray trace correlation, custom events, custom metrics, and
  the CloudWatch RUM JavaScript SDK integrated via CDN or npm.
  Wires Application Signals client-side correlation and emits a
  READY_TO_DEPLOY checklist verifying every prerequisite. Use
  when creating a RUM app monitor, injecting the RUM SDK (CDN
  script tag or npm import), wiring cookie domain, recording
  custom events / custom metrics, enabling X-Ray trace
  integration, or correlating client-side RUM sessions with
  server-side Application Signals. Triggers: cloudwatch rum,
  real user monitoring, rum app monitor, rum javascript sdk,
  rum web client, rum cdn, rum npm, cookie domain, custom
  events rum, rum custom metrics, x-ray rum correlation,
  application signals client correlation, web vitals
  cloudwatch, client-side observability.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live deployment: AWS CLI v2 with
  rum, cloudwatch, xray, iam, application-signals, and ssm access.
  Works with Terraform aws_cloudwatch_rum_app_monitor, CloudFormation
  AWS::RUM::AppMonitor, and the CloudWatch RUM JavaScript SDK
  (@/aws-cdk/aws-rum or aws-rum-web on npm).
keywords:
  - aws
  - cloudwatch
  - rum
  - real-user-monitoring
  - client-side-observability
  - cloudops
  - deploy
  - provisioning
  - javascript-sdk
  - web-vitals
  - cookie-domain
  - custom-events
  - custom-metrics
  - xray-correlation
  - application-signals
tags:
  - aws
  - cloudwatch
  - rum
  - observability
  - deploy
  - javascript-sdk
  - web-vitals
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: Management
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags:
    - aws
    - cloudwatch
    - rum
    - observability
    - deploy
    - javascript-sdk
    - web-vitals
  dependencies:
    - aws-orchestrator
  keywords:
    - cloudwatch rum
    - real user monitoring
    - rum app monitor
    - rum javascript sdk
    - rum web client
    - cookie domain rum
    - rum custom events
    - rum custom metrics
    - x-ray rum correlation
    - application signals client correlation
    - web vitals cloudwatch
    - client-side observability
    - session sampling
  when_to_use: >-
    Invoke when the user wants to create a CloudWatch RUM app monitor
    (domain, sample rate, cookie domain, telemetries), inject the
    CloudWatch RUM JavaScript SDK via CDN or npm, wire cookie
    domain, record custom events or custom metrics, enable X-Ray
    tracing integration for client-to-server trace correlation, or
    correlate client-side RUM sessions with server-side Application
    Signals service map. Do NOT invoke for plain CloudWatch dashboards
    or alarms (use cloudwatch-dashboard-deployer / cloudwatch-alarm-operator),
    for X-Ray-only tracing without RUM (use xray-tracing-deployer), or
    for Application Signals enablement on server workloads
    (use cloudwatch-application-signals-deployer).
---

# CloudWatch RUM Deployer

An AWS CloudOps agent skill that provisions CloudWatch RUM (Real
User Monitoring) app monitors with the correct production defaults
— domain allow-list, sample rate, cookie domain, telemetry
selection (errors, performance, HTTP), X-Ray trace correlation,
custom events, custom metrics, and Application Signals client-side
correlation. Emits a READY_TO_DEPLOY checklist verifying every
prerequisite.

## Quick navigation

| Need | Section |
|---|---|
| What MUST be in the response | "STRICT output contract" |
| Why the provisioning order matters | "Reasoning framework" |
| What to verify before enabling | "Prerequisites" |
| The ordered provisioning steps | "Deployment procedure" |
| Common silent-failure pitfalls | "NEVER" |
| SDK integration, cookie domain, custom events | "Deployment procedure" Steps 3-7 |
| X-Ray and Application Signals correlation | "Deployment procedure" Steps 5-9 |
| Web client matrix (CDN / npm / React / Vue) | "Web client matrix" |
| 2024-2026 feature changes | "Recent AWS features" |
| Deep CLI sequences | `references/deployment-cli-commands.md` |
| Custom events, metrics, X-Ray correlation | `references/custom-events-and-correlation-guide.md` |

## STRICT output contract

When this skill is invoked with a CloudWatch RUM enablement request
(domain, application name, sample rate, integration type, or a
partial existing configuration), the agent MUST respond with the
READY_TO_DEPLOY checklist using the literal all-caps labels
`RUM_APP:`, `VERDICT:`, `CHECKLIST:`, `JS_SNIPPET:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response.

### Required output structure

1. `RUM_APP: <application-name>` — the web app being monitored
   (matches the `--name` / `applicationId` on the app monitor).
2. `VERDICT: READY_TO_DEPLOY` OR `VERDICT: PREREQUISITES_MISSING`.
3. `CHECKLIST:` followed by indented rows. Every row uses a status
   marker (`[✓]`, `[✗]`, `[OPTIONAL]`, `[INPUT NEEDED]`) and shows
   `current: <value>  recommended: <value>` so the operator can see
   the app monitor config at a glance: domain, sampling rate,
   telemetries (errors / performance / http), cookie domain, guest
   role ARN, X-Ray toggle, Application Signals correlation.
4. `JS_SNIPPET:` followed by a fenced code block containing the
   copy-pasteable CDN `<script>` tag (or npm import) with every
   placeholder resolved to real values from CHECKLIST. This is what
   the operator inserts into the page template.
5. `VERIFICATION_COMMANDS:` followed by indented `aws ...` commands.

### FORBIDDEN output patterns

1. **NEVER start with prose preamble** ("Let me analyze…", "Looking
   at your setup…"). The first non-empty line MUST be `RUM_APP:`. No
   greetings, no headings, no disclaimers before it.

2. **NEVER use markdown variants of the labels.** Write `VERDICT:`,
   not `**VERDICT:**`, `### Verdict`, `Verdict =`, or `` `VERDICT` ``.
   The labels are parser-anchored; bold or heading variants break
   downstream automation.

3. **NEVER swap verdict tokens.** Exactly `READY_TO_DEPLOY` or
   `PREREQUISITES_MISSING`. Not "ready", "missing", "BLOCKED", "OK",
   "PARTIAL", or any invented token.

4. **NEVER omit `JS_SNIPPET:` or emit it with placeholder values.**
   The snippet MUST show real values for `applicationId`,
   `guestRoleArn`, `identityPoolId`, `cookieDomain`, and
   `sessionSampleRate` resolved from CHECKLIST. A snippet with
   `<your-app-monitor-name>` is a FORBIDDEN placeholder leak.

5. **NEVER omit `VERIFICATION_COMMANDS:`** — include even when
   PREREQUISITES_MISSING; the operator needs commands to verify gaps.

6. **NEVER append extra sections after `VERIFICATION_COMMANDS:`.**
   The checklist block IS the entire response. Put deeper explanation
   in `references/`.

7. **NEVER invent status markers.** Use only `[✓]`, `[✗]`,
   `[OPTIONAL]`, `[INPUT NEEDED]`. Do not emit `[?]`, `[!]`, `[WARN]`,
   or emoji.

8. **NEVER set `cookieDomain` to a public suffix** (`.com`, `.app`,
   `.io`, `.dev`) in JS_SNIPPET or CHECKLIST — emit `[✗]` and cite
   the leak risk if the operator requested one.

### Perfect example — READY_TO_DEPLOY with XSS sanitization + X-Ray tracing

Every field below has real values. Copy this shape exactly and swap
in the operator's values. The CHECKLIST rows surface the app monitor
config (domain, sampling rate, telemetries, cookie domain, guest
role, X-Ray, Application Signals) as `current:` vs `recommended:`
pairs. The JS_SNIPPET is the copy-pasteable CDN script tag with XSS
sanitization (SRI `integrity` attribute + `crossorigin="anonymous"`)
and `enableXRay:true` for client-to-server trace correlation.

```text
RUM_APP: checkout-web
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓]      App monitor name — checkout-web-prod (arn:aws:rum:us-east-1:111122223333:appmonitor/checkout-web-prod)
  [✓]      Domain (AllowedOrigins) — https://checkout.example.com  (scheme+host+port; wildcard NOT supported)
  [✓]      Sampling rate — current: 1.0   recommended: 1.0 (raise traffic <100k sessions/day; drop to 0.1 above 1M)
  [✓]      Cookie domain — current: .example.com   recommended: .example.com (NOT .com — TLD leak)
  [✓]      Telemetries — current: errors, performance, http   recommended: errors, performance, http (declare ALL at init)
  [✓]      Guest role — arn:aws:iam::111122223333:role/checkout-web-rum-guest (rum:PutRumEvents scoped to app monitor ARN)
  [✓]      Identity pool — us-east-1:abcd1234-efgh-5678 (Cognito unauth pool backing the guest role)
  [✓]      X-Ray tracing — current: enableXRay=true   recommended: true (server sampling rule FixedRate 0.05 verified > 0)
  [✓]      Application Signals correlation — AWS/ApplicationSignalsClient namespace (auto-populated when server enabled)
  [✓]      XSS sanitization — CDN script loaded with SRI integrity="sha384-<hash>" + crossorigin="anonymous"; no inline eval
  [✓]      Custom metrics — AWS/RUM, dimensions ApplicationName=checkout-web-prod + RumEventName (up to 100 definitions)
  [✓]      CloudWatch metrics emitted — AWS/RUM: Errors, JsErrorCount, SessionCount, WebVitalsLCP, WebVitalsINP, Http4xx, Http5xx
  [OPTIONAL] Session sampling override — 0.05 for traffic > 1M daily sessions
  [OPTIONAL] Sub-resource timing — PerformanceNavigationTiming details enabled
JS_SNIPPET:
  <!-- Insert before </head> on every page template. integrity attr =
       Subresource Integrity (SRI); prevents CDN-tampered XSS. crossorigin
       required for SRI enforcement. Pin the SDK version; never auto-upgrade. -->
  <script>
    (function(n,i,v,r,s,c,x,z,h){var p=function(){var a=
    Array.prototype.slice.call(arguments);return new (Function.
    prototype.bind.apply(cwr,(a).concat(p.args)))},q=p.args=
    Array.prototype.slice.call(arguments);(cwr=a=cwr||function(){
    (cwr.q=cwr.q||[]).push(arguments)}).l=+new Date;cwr('init',
    {clientConfig:{applicationId:'checkout-web-prod',
    region:'us-east-1',version:'1.0.0',
    guestRoleArn:'arn:aws:iam::111122223333:role/checkout-web-rum-guest',
    identityPoolId:'us-east-1:abcd1234-efgh-5678'},
    telemetries:['errors','performance','http'],
    sessionSampleRate:1.0,
    sessionEventUrl:'https://dataplane.rum.us-east-1.amazonaws.com',
    cookieDomain:'.example.com',
    enableXRay:true,
    allowCookies:true,
    disableXsrfCookie:false});cwr('load')})()
  </script>
  <script async src="https://client.rum.us-east-1.amazonaws.com/1.18.0/aws-rum-web.min.js"
          integrity="sha384-<compute-sha384-of-the-file-and-insert-here>"
          crossorigin="anonymous"></script>
VERIFICATION_COMMANDS:
  aws rum list-app-monitors --region us-east-1
  aws rum get-app-monitor --name checkout-web-prod --region us-east-1
  aws cloudwatch list-metrics --namespace AWS/RUM --dimensions Name=ApplicationName,Value=checkout-web-prod --region us-east-1
  aws cloudwatch list-metrics --namespace AWS/ApplicationSignalsClient --region us-east-1
  aws xray get-sampling-rules --region us-east-1
  aws iam list-attached-role-policies --role-name checkout-web-rum-guest
  aws logs describe-log-streams --log-group-name /aws/rum/checkout-web-prod --limit 1 --order-by LastEventTime --descending --region us-east-1
```

### Perfect example — PREREQUISITES_MISSING

```text
RUM_APP: checkout-web
VERDICT: PREREQUISITES_MISSING
CHECKLIST:
  [✓]      App monitor name — checkout-web-prod (created in us-east-1)
  [✓]      Domain (AllowedOrigins) — https://checkout.example.com
  [✓]      Sampling rate — current: 1.0   recommended: 1.0
  [✗]      Cookie domain — current: .com   recommended: .example.com (REJECT TLD; cookie leaks across all .com sites)
  [✓]      Telemetries — current: errors, performance, http   recommended: errors, performance, http
  [✗]      Guest role — MISSING: no IAM role with rum:PutRumEvents found (run `aws iam list-roles --query 'Roles[?contains(RoleName,`rum`)]'`)
  [INPUT NEEDED] Identity pool — operator must provide Cognito unauth pool ID, or skill must create one
  [✗]      X-Ray tracing — current: enableXRay=true   BLOCKED: server sampling rule FixedRate=0.0; raise to >=0.01 (aws xray update-sampling-rule)
  [✗]      Application Signals correlation — BLOCKED on X-Ray sampling rule above
  [✗]      XSS sanitization — JS_SNIPPET withheld: SRI hash missing until SDK version pinned
  [✗]      Custom metrics — BLOCKED: no put-metrics-destination configured
  [✗]      CloudWatch metrics emitted — none yet (deployment not live)
JS_SNIPPET: (withheld — resolve the 4 BLOCKED rows above, then re-invoke)
VERIFICATION_COMMANDS:
  aws iam list-roles --query 'Roles[?contains(RoleName,`rum`)]' --output text
  aws xray get-sampling-rules --region us-east-1
  aws cognito-identity list-identity-pools --max-results 10 --region us-east-1
  aws rum get-app-monitor --name checkout-web-prod --region us-east-1
```

## Reasoning framework (why the provisioning order matters)

Enabling RUM has **dependency and ordering constraints** that make
the procedure non-trivial. Skipping or misordering causes silent
gaps — the dashboard stays empty, sessions drop, or X-Ray traces
never link to client-side events:

1. **App monitor FIRST** — `rum create-app-monitor` provisions the
   telemetry sink and emits the application identity used by every
   downstream SDK config and metric dimension. The monitor name is
   embedded in the IAM resource ARN; recreating it breaks every
   embedded snippet.
2. **Domain allow-list** — RUM rejects `PutRumEvents` whose
   `pageDomain` is not in the app monitor's `AppMonitorConfiguration.
   AllowedOrigins`. A misconfigured allow-list silently drops all
   telemetry; the dashboard shows zero sessions.
3. **IAM guest role is mandatory** — the SDK authenticates via an
   anonymous guest role (or authenticated Cognito identity) holding
   `rum:PutRumEvents`. Without it, the browser console fills with
   `AccessDenied` and no events land.
4. **Cookie domain must match the deployment** — the cookie domain
   drives session stitching across subdomains. An overly broad
   cookie domain (`.com`) leaks sessions across unrelated sites; a
   missing cookie domain breaks cross-subdomain session continuity.
5. **Telemetries declared at init** — errors, performance, http
   telemetries are gated by the `cwr('init', ...)` config. Adding
   telemetry later requires a code change; declare all three at
   init unless there is a deliberate reason to omit one.
6. **X-Ray tracing requires sampling** — RUM correlates to X-Ray
   by sending the client-side trace ID with `PutRumEvents`. The
   server-side segment must be sampled by an X-Ray sampling rule
   that includes the same trace ID. A 0% sampling rule on the
   server blanks the correlation.
7. **Application Signals correlation is auto-derived** — when both
   Application Signals (server) and RUM (client) are enabled for
   the same service, CloudWatch auto-populates the
   `AWS/ApplicationSignalsClient` namespace. RUM does NOT merge
   across Regions; plan per-Region app monitors.

## Prerequisites (verify before deployment)

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| **AWS account opt-in for CloudWatch RUM** | RUM is Region-scoped and must be available. | `aws rum list-app-monitors` (no error = available) |
| **Domain ownership** | The app monitor `AllowedOrigins` must enumerate every origin (scheme + host + port) the web app is served from. | Confirm with frontend team / DNS records |
| **Anonymous guest IAM role (or Cognito identity pool)** | The SDK must call `rum:PutRumEvents` from the browser; guest role holds the permission. | `aws iam list-attached-role-policies --role-name <guest-role>` |
| **CORS configured** | RUM API requires CORS from the allowed origins. `AllowedOrigins` on the app monitor drives CORS validation. | Implicit via app monitor config |
| **X-Ray tracing enabled** (optional) | Required for client-to-server trace correlation. | `aws xray get-encryption-config` |
| **X-Ray sampling rule** (optional) | Default sampling rule must be > 0% for trace correlation. | `aws xray get-sampling-rules` (Default FixedRate > 0) |
| **Application Signals enabled on the server** (optional) | Required for client/server service-map correlation. | `aws application-signals list-services` |
| **IAM permissions for caller** | Caller needs `rum:CreateAppMonitor`, `rum:GetAppMonitor`, `iam:PassRole`, `cloudwatch:ListMetrics`. | `aws sts get-caller-identity` |

## Deployment procedure (apply in order)

### Step 1: Create the app monitor

The app monitor provisions the telemetry sink. Provide a globally
unique name (within the account-Region), the domain allow-list, and
the sample rate:

```bash
aws rum create-app-monitor \
  --name checkout-web-prod \
  --app-monitor-configuration '{
    "AllowList": ["checkout.example.com"],
    "SessionSampleRate": 1.0,
    "Telemetries": ["errors", "performance", "http"],
    "EnableXRay": true
  }' \
  --cw-log-group-name /aws/rum/checkout-web-prod \
  --domain checkout.example.com \
  --region us-east-1
```

The app monitor name (`checkout-web-prod`) appears in the ARN and
every metric dimension. The `AllowList` enforces which origins
(scheme + host + port) can send `PutRumEvents`. **Every origin
must be listed explicitly** — RUM does not support wildcard
subdomains in the allow-list.

`SessionSampleRate` is a 0.0-1.0 fraction of sessions retained.
Use `1.0` for low-traffic sites, `0.1` (10%) for sites above
~1M daily sessions.

`Telemetries` declares which telemetry types the SDK captures:
- `errors` — uncaught JS exceptions, unhandled promise rejections.
- `performance` — Web Vitals (LCP, FID, CLS, INP, TTFB), navigation
  and resource timing.
- `http` — fetch and XHR request/response timing and status.

`EnableXRay: true` instructs the SDK to attach a client-side trace
ID to each event batch and emit a `PutTraceSegments` call for the
client-side segment.

### Step 2: Create the anonymous guest IAM role

The SDK needs credentials with `rum:PutRumEvents` on the app
monitor. For browser-based apps, use an anonymous guest role
(Cognito identity pool) — never embed long-lived AWS keys in JS.

```bash
# Trust policy for Cognito identity pool
cat > /tmp/guest-trust.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Federated": "cognito-identity.amazonaws.com" },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "cognito-identity.amazonaws.com:aud": "us-east-1:abcd1234-efgh-5678"
      },
      "ForAnyValue:StringLike": {
        "cognito-identity.amazonaws.com:amr": "unauth"
      }
    }
  }]
}
EOF

aws iam create-role \
  --role-name checkout-web-rum-guest \
  --assume-role-policy-document file:///tmp/guest-trust.json

cat > /tmp/guest-permission.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "rum:PutRumEvents",
    "Resource": "arn:aws:rum:us-east-1:111122223333:appmonitor/checkout-web-prod"
  }]
}
EOF

aws iam put-role-policy \
  --role-name checkout-web-rum-guest \
  --policy-name CheckoutWebRUMPutEvents \
  --policy-document file:///tmp/guest-permission.json
```

Resource-lock the policy to **this** app monitor ARN. A wildcard
(`rum:PutRumEvents: *`) lets any malicious script send events to
any app monitor in the account.

### Step 3: Inject the RUM JavaScript SDK (CDN pattern)

The CDN pattern loads the SDK via a script tag and configures it
with the app monitor identity, guest role, and cookie domain:

```html
<script>
  (function(n,i,v,r,s,c,x,z,h){var p=function(){var a=
  Array.prototype.slice.call(arguments);return new (Function.
  prototype.bind.apply(cwr,(a).concat(p.args)))},q=p.args=
  Array.prototype.slice.call(arguments);(cwr=a=cwr||function(){
  (cwr.q=cwr.q||[]).push(arguments)}).l=+new Date;cwr('init',
  {clientConfig:{applicationId:'checkout-web-prod',
  region:'us-east-1',version:'1.0.0',
  guestRoleArn:'arn:aws:iam::111122223333:role/checkout-web-rum-guest',
  identityPoolId:'us-east-1:abcd1234-efgh-5678'},
  telemetries:['errors','performance','http'],
  sessionSampleRate:1.0,
  sessionEventUrl:'https://dataplane.rum.us-east-1.amazonaws.com',
  cookieDomain:'.example.com',
  enableXRay:true});cwr('load')})()
</script>
<script async src="https://client.rum.us-east-1.amazonaws.com/1.18.0/aws-rum-web.min.js"
        integrity="sha384-<hash>"
        crossorigin="anonymous"></script>
```

Key config attributes: `applicationId` (must EXACTLY match the app
monitor name), `guestRoleArn` + `identityPoolId` (guest role from
Step 2), `telemetries` (must match the app monitor's `Telemetries`
field), `sessionSampleRate`, and `cookieDomain` (see Step 4).

### Step 3b: Inject the RUM SDK (npm pattern)

For SPA frameworks (React, Vue, Angular, Next.js), install
`aws-rum-web` via npm and construct the client:

```typescript
import { AwsRum, AwsRumConfig } from 'aws-rum-web';

const config: AwsRumConfig = {
  sessionSampleRate: 1.0,
  guestRoleArn: 'arn:aws:iam::111122223333:role/checkout-web-rum-guest',
  identityPoolId: 'us-east-1:abcd1234-efgh-5678',
  endpoint: 'https://dataplane.rum.us-east-1.amazonaws.com',
  telemetries: ['errors', 'performance', 'http'],
  allowCookies: true,
  cookieDomain: '.example.com',
  enableXRay: true
};

export const awsRum = new AwsRum(
  'checkout-web-prod', '1.0.0', 'us-east-1', config
);
```

The npm pattern is required for tree-shaking, build-time bundling,
or typed event records. The CDN pattern is fine for static
marketing sites and POC deploys.

### Step 4: Configure the cookie domain

RUM stores a session cookie (`cwr_s`) used to stitch page views
into a single session across reloads and navigation. The
`cookieDomain` controls which subdomains see the cookie:

```typescript
cookieDomain: '.example.com'  // checkout.example.com, app.example.com, www.example.com all share
cookieDomain: 'checkout.example.com'  // only this exact subdomain
```

**NEVER** set `cookieDomain: '.com'` or any TLD — the cookie leaks
to every `.com` site the user visits, breaking the session
definition and risking leakage into other AWS customers' RUM
dashboards if they share the browser.

Omit `cookieDomain` to default to the current host only. This is
correct for single-subdomain apps; multi-subdomain apps must set
the domain explicitly.

### Step 5: Configure X-Ray trace correlation

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

### Step 6: Record custom events

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

### Step 7: Configure RUM custom metrics

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

### Step 8: Wire Application Signals client-side correlation

When Application Signals is enabled on the server workload AND the
RUM app monitor's domain matches the server-side service's
`AWS_SERVICE_NAME`-derived endpoint, CloudWatch auto-joins the
client and server:

- The `AWS/ApplicationSignalsClient` namespace populates with
  `ClientURL` + `ServiceName` dimensions.
- The service map shows a client node (browser) connected to the
  server service node.

To verify correlation:

```bash
aws cloudwatch list-metrics --namespace AWS/ApplicationSignalsClient \
  --dimensions Name=ServiceName,Value=payments-api --region us-east-1
```

If the namespace stays empty, the cause is almost always:
1. Application Signals not enabled on the server workload (use the
   `cloudwatch-application-signals-deployer` skill).
2. Server-side sampling rate too low (raise X-Ray Default rule).
3. RUM app monitor domain mismatch with the server endpoint.

### Step 9: Verify telemetry is flowing

Within 1-5 minutes of the first user visiting the page, telemetry
should appear:

```bash
aws cloudwatch list-metrics --namespace AWS/RUM \
  --dimensions Name=ApplicationName,Value=checkout-web-prod

aws logs describe-log-streams \
  --log-group-name /aws/rum/checkout-web-prod \
  --limit 1 --order-by LastEventTime --descending

aws xray get-trace-summaries \
  --start-time $(date -u +%s --date='10 min ago') \
  --end-time $(date -u +%s) \
  --filter-expression 'service.id = "checkout-web-prod"'
```

If metrics do not appear within 15 minutes, the cause is almost
always:
- Domain not in `AllowedOrigins` (silent drop).
- Guest role lacks `rum:PutRumEvents` on the app monitor ARN.
- Browser ad blocker suppressing the RUM CDN script.

### Step 10: Tag, alarm, and visualize

Tag the app monitor for cost allocation; alarm on session drops
and error spikes:

```bash
aws rum tag-resource \
  --resource-arn arn:aws:rum:us-east-1:111122223333:appmonitor/checkout-web-prod \
  --tags team=payments,env=prod

aws cloudwatch put-metric-alarm \
  --alarm-name checkout-web-rum-error-spike \
  --namespace AWS/RUM \
  --metric-name Errors \
  --dimensions Name=ApplicationName,Value=checkout-web-prod \
  --period 300 --evaluation-periods 2 \
  --threshold 50 --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:111122223333:oncall
```

Open the CloudWatch console → RUM → Application list to confirm
the application shows session count, page load times, and Web
Vitals (LCP, FID, CLS, INP) populated.

## Web client matrix

| Web client | Integration | Notes |
|---|---|---|
| Static HTML | CDN script tag | Easiest; fine for marketing sites |
| React SPA | npm import + `AwsRum` constructor | Wrap in error boundary; record page views on route change |
| Vue SPA | npm import | Record in `router.afterEach` |
| Angular SPA | npm import | Register as an Angular provider |
| Next.js (SSR) | npm import, guard against SSR | Use `if (typeof window !== 'undefined')` |
| SvelteKit | npm import | Conditionally init in `onMount` |
| Mobile webview | CDN or npm | Configure cookie domain to match the wrapping site |

## Edge-case handling

- **Sessions not appearing in dashboard:** the domain in
  `AllowedOrigins` is missing scheme or port. RUM matches scheme +
  host + port exactly; `https://checkout.example.com` differs from
  `checkout.example.com`. Always include `https://`.
- **Browser console `AccessDenied` on `PutRumEvents`:** the guest
  role lacks the permission, or the resource ARN in the policy
  does not match the app monitor ARN. Check `iam get-role-policy`.
- **X-Ray traces not correlating:** server-side sampling rule is
  0%, or the server's X-Ray SDK is not propagating the
  `X-Amzn-Trace-Id` header. Inspect server-side X-Ray SDK config.
- **Custom events rejected:** event `type` contains a hyphen or
  special character. Use snake_case (`checkout_complete`, not
  `checkout-complete`).
- **Cookie domain rejected:** the cookie domain does not match the
  page URL host. The browser ignores the cookie and session
  stitching breaks. Verify the domain with `document.cookie` in
  DevTools.
- **Ad blockers suppressing telemetry:** uBlock Origin and
  similar block the RUM CDN script. RUM cannot bypass this;
  expect 5-15% session under-count in adblock-heavy audiences.
  Document the limitation; do not attempt to evade adblockers.
- **Application Signals correlation empty:** the server workload
  is not enabled for Application Signals, or the RUM domain does
  not match the server's `AWS_SERVICE_NAME`-derived endpoint.
- **Multi-Region apps:** RUM does not merge across Regions. Plan
  per-Region app monitors and per-Region dashboards.

## Recent AWS features (2024-2026)

- **RUM Application Signals correlation (2025):** the
  `AWS/ApplicationSignalsClient` namespace auto-populates when both
  Application Signals (server) and RUM (client) cover the same
  service endpoint. Surfaced as a client node in the service map.

- **RUM custom metrics (2024-2025):** `put-metrics-destination` on
  the app monitor emits CloudWatch custom metrics from custom
  event data. Up to 100 metric definitions per app monitor.

- **Web Vitals INP (Interaction to Next Paint) GA (2024-2025):**
  RUM captures INP as the successor to FID. The dashboard surfaces
  both during the transition period.

- **Extended SDK versioning (2024-2025):** the SDK is versioned
  independently of the service. Pin the version in the CDN script
  tag (`aws-rum-web@1.18.0`) — auto-upgrades can break event
  schemas.

- **RUM with Application Signals SLOs (2025):** Application
  Signals SLOs can reference client-side metrics (Latency,
  Availability) sourced from RUM via the
  `AWS/ApplicationSignalsClient` namespace. Client-side SLOs are
  now first-class.

- **Cookie domain strict validation (2024-2025):** cookie domains
  must match the page URL host exactly or be a parent domain.
  Invalid cookie domains are silently dropped (no error in the
  SDK; sessions just don't persist across navigation).

- **Session event batching (2024-2025):** the SDK batches events
  up to 3 MB before calling `PutRumEvents`. Tunable via
  `batchLimitMB`. Lower for low-bandwidth mobile; raise for high-
  bandwidth desktop.

- **CORS strict origin matching (2024-2025):** the allow-list
  matches scheme + host + port exactly. Wildcards are not
  supported; explicit subdomain entries are required.

## NEVER (top 5 — full list in references)

- NEVER embed long-lived AWS access keys in JavaScript. The SDK
  MUST authenticate via a Cognito identity pool guest role or a
  web-identity role. Embedded keys leak to every site visitor.
- NEVER set `cookieDomain` to a public suffix (`.com`, `.app`,
  `.io`). The cookie leaks across unrelated sites and corrupts
  session counts. Use the specific subdomain or the parent
  organizational domain only.
- NEVER omit a domain from `AllowedOrigins`. RUM silently drops
  events from origins not on the list; the dashboard shows zero
  sessions and there is no error in the console.
- NEVER set the server-side X-Ray sampling rule to 0% when X-Ray
  correlation is enabled. Client traces land, server traces do
  not, and the correlation is lost. Use the default 5% rule or
  higher.
- NEVER recreate the app monitor with a new name. The name is
  embedded in every metric dimension, every alarm, and the IAM
  resource ARN. Renaming breaks every downstream alarm and
  dashboard. Update in-place or migrate deliberately.

## Expert heuristic — enabling RUM and choosing config

- **Sample rate vs. cost.** RUM charges per `PutRumEvents` call.
  At 100% sample rate and 1M daily sessions, expect ~$300/month
  per app monitor. Drop to 10% for high-traffic sites; raise to
  100% for low-traffic beta deploys.
- **Cookie domain defaults to the current host.** This is correct
  for single-subdomain apps; multi-subdomain apps must set the
  parent domain explicitly. When in doubt, omit and observe
  session continuity.
- **Telemetries: declare all three at init.** errors, performance,
  http. Adding telemetry later requires a code change. Removing
  one (e.g., `http` for privacy) is a deliberate choice.
- **Custom event types: snake_case only.** Hyphens and special
  characters are rejected silently. Establish a naming convention
  (`<domain>_<action>`, e.g., `checkout_complete`).
- **Guest role ARN resource lock.** Scope `rum:PutRumEvents` to
  the specific app monitor ARN. Wildcard policies let any
  malicious script write events to any app monitor in the
  account.
- **X-Ray correlation needs server-side header propagation.**
  Confirm the server reads `X-Amzn-Trace-Id` and joins the trace.
  Without propagation, RUM captures client-side traces only.
- **Ad blockers cannot be bypassed.** Expect 5-15% under-count in
  adblock-heavy audiences. Document the limitation; do not
  attempt to evade.

## Pre-flight safety checks (run before any enablement CLI)

- **Confirm RUM is available in the Region:** `aws rum
  list-app-monitors --region <r>` (no error = available).
- **Confirm the guest role:** `aws iam list-attached-role-policies
  --role-name <guest-role>` (must include a policy with
  `rum:PutRumEvents` on the planned app monitor ARN).
- **Confirm X-Ray sampling default exists (if X-Ray enabled):**
  `aws xray get-sampling-rules` (must list a `Default` rule with
  `FixedRate > 0`).
- **Confirm Application Signals is enabled on the server (if
  client correlation desired):** `aws application-signals
  list-services` (server workload appears).
- **Confirm the domain allow-list:** every origin (scheme + host
  + port) the web app is served from must be in `AllowedOrigins`.
- **Confirm the cookie domain** matches the deployment's parent
  domain or the exact host.

## Output format — MANDATORY literal labels

When invoked with a CloudWatch RUM enablement request, your
ENTIRE response MUST be the checklist block defined in
"STRICT output contract" earlier in this document. The labels are
**case-sensitive all-caps keywords** — write them EXACTLY as
shown. Do NOT write a preamble. Start with `RUM_APP:` and
stop after the `VERIFICATION_COMMANDS:` block. The five mandatory
labels in order are: `RUM_APP:`, `VERDICT:`, `CHECKLIST:`,
`JS_SNIPPET:`, `VERIFICATION_COMMANDS:`. The full worked example
shape (READY_TO_DEPLOY and PREREQUISITES_MISSING) lives in the
"STRICT output contract" / "Perfect example" subsection above —
copy that shape exactly and resolve every placeholder to a real
value before emitting.

**Status marker semantics:**
- `[✓]` — applied and verified.
- `[✗]` — NOT applied or misconfigured. Cite the gap.
- `[OPTIONAL]` — recommended but not required for the workload
  type.
- `[INPUT NEEDED]` — prerequisite value missing; operator must
  provide.

**PREREQUISITES_MISSING verdict:** if any REQUIRED prerequisite
is missing (domain not in `AllowedOrigins`, guest role ARN, X-Ray
sampling rule when correlation enabled), the verdict is
`PREREQUISITES_MISSING` with each gap listed in CHECKLIST as `[✗]`
and `JS_SNIPPET:` withheld until every BLOCKED row is resolved.

## Domain

AWS CloudOps / Client-Side Observability Provisioning.

## AWS documentation

- **CloudWatch RUM User Guide** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-RUM.html
- **Creating a RUM app monitor** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-RUM-create-appmon.html
- **RUM JavaScript SDK** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-RUM-sdk.html
- **RUM custom metrics** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-RUM-metrics.html
- **RUM X-Ray integration** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-RUM-Xray.html
- **RUM Application Signals correlation** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Application-Signals.html
- **aws-rum-web npm package** — https://www.npmjs.com/package/aws-rum-web
- **AWS CLI rum reference** — https://docs.aws.amazon.com/cli/latest/reference/rum/
- **AWS::RUM::AppMonitor CloudFormation** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-rum-appmonitor.html

## References

- `references/deployment-cli-commands.md` — full copy-pasteable
  CLI command sequence for all 10 enablement steps, including
  Terraform equivalents, CloudFormation snippets, and per-framework
  (React, Vue, Angular, Next.js) integration code.

- `references/custom-events-and-correlation-guide.md` — deep
  reference on custom event schemas, custom metric extraction,
  X-Ray header propagation, Application Signals client correlation
  internals, full NEVER list, and edge-case handling.
