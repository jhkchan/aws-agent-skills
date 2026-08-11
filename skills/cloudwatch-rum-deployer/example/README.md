# End-to-end usage scenario: cloudwatch-rum-deployer

A walkthrough showing the skill enabling CloudWatch RUM on a
static marketing site via the CDN pattern, then extending to a
React SPA with X-Ray trace correlation and a RUM custom metric.
This exercises Step 1 (app monitor creation), Step 2 (guest IAM
role), Step 3 (SDK injection), Step 5 (X-Ray wiring), and
Step 7 (custom metrics).

## Input (user prompt)

> Enable CloudWatch RUM on `checkout-web-prod` in `us-east-1`.
> The web app is served from `https://checkout.example.com`
> (static HTML, then React SPA migration). Cookie domain
> `.example.com`. Sample rate 100%, telemetries errors /
> performance / http, X-Ray enabled. Identity pool
> `us-east-1:abcd1234-efgh-5678` with guest role
> `arn:aws:iam::111122223333:role/checkout-web-rum-guest`. Also
> record a `checkout_complete` custom event with a CartValueTotal
> custom metric in the AWS/RUM namespace.

## Skill output

```text
APPLICATION: checkout-web
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓]      Domain — https://checkout.example.com (validated against AllowedOrigins)
  [✓]      App monitor — arn:aws:rum:us-east-1:111122223333:appmonitor/checkout-web-prod
  [✓]      Sample rate — 1.0
  [✓]      Cookie domain — .example.com
  [✓]      Telemetries — errors, performance, http
  [✓]      IAM auth — guest role checkout-web-rum-guest with rum:PutRumEvents on app monitor ARN
  [✓]      SDK integration — CDN script tag (static site) + npm (React migration)
  [✓]      Custom events — cwr('recordEvent', { type: 'checkout_complete', data: {...} })
  [✓]      Custom metrics — AWS/RUM CartValueTotal, value key $.event.data.cartValue
  [✓]      X-Ray tracing — enabled; server-side sampling rule FixedRate=0.05
  [✓]      Application Signals correlation — AWS/ApplicationSignalsClient namespace wired
  [OPTIONAL] Session sampling override — leave at 1.0 for beta; drop to 0.1 post-launch
VERIFICATION_COMMANDS:
  aws rum list-app-monitors --region us-east-1
  aws rum get-app-monitor --name checkout-web-prod --region us-east-1
  aws cloudwatch list-metrics --namespace AWS/RUM --dimensions Name=ApplicationName,Value=checkout-web-prod
  aws cloudwatch list-metrics --namespace AWS/ApplicationSignalsClient --region us-east-1
  aws xray get-sampling-rules --region us-east-1
  aws iam list-attached-role-policies --role-name checkout-web-rum-guest
```

## What the skill caught that a generic assistant misses

1. **Domain allow-list scheme + host + port.** A generic assistant
   omits the `https://` scheme; RUM rejects `PutRumEvents` whose
   `pageOrigin` is not on the list verbatim. The skill includes
   the scheme and warns about port.
2. **Guest role resource lock.** A generic assistant suggests
   `rum:PutRumEvents: *`. The skill scopes the policy to the
   specific app monitor ARN to prevent cross-app-monitor event
   injection from a malicious script.
3. **Cookie domain pitfall.** A generic assistant picks
   `.example.com` without explaining that `.com` is a public
   suffix and would leak sessions. The skill explains the
   constraint.
4. **X-Ray correlation needs server-side sampling.** A generic
   assistant enables `enableXRay` and assumes correlation works.
   The skill verifies the server-side X-Ray sampling rule and
   the `X-Amzn-Trace-Id` header propagation.
5. **Custom event type naming.** A generic assistant uses
   `checkout-complete` (hyphenated). RUM rejects non-alphanumeric
   event types; the skill enforces snake_case.
6. **Custom metric extraction path.** A generic assistant suggests
   `put-metric-data` from the browser. The skill uses
   `put-metrics-destination` on the app monitor so CloudWatch
   derives the metric server-side from the custom event stream.
7. **Application Signals correlation prerequisite.** A generic
   assistant assumes correlation works automatically. The skill
   verifies `list-services` returns the server workload and the
   X-Ray sampling rule before claiming correlation.

## Slash-command invocation

```
/aws:deploy-cloudwatch-rum
```

Or via the orchestrator:

```
/aws:pipeline
You: "enable cloudwatch rum on checkout-web-prod in us-east-1"
```

The orchestrator emits `[Phase: Deploy | Skills routed:
cloudwatch-rum-deployer]` and hands off to this skill for the
VERDICT.

## Related scenarios

The same skill handles:

- **Static site + CDN** — script tag with `cwr('init', ...)`.
- **React / Vue / Angular SPA + npm** — `AwsRum` constructor
  with typed config.
- **Next.js SSR** — guard `new AwsRum(...)` with
  `typeof window !== 'undefined'`.
- **Cookie domain for multi-subdomain** — `.example.com` for
  cross-subdomain session stitching.
- **X-Ray trace correlation** — `enableXRay: true` plus
  `X-Amzn-Trace-Id` server-side propagation.
- **Application Signals client correlation** — verify
  `AWS/ApplicationSignalsClient` namespace populates.
- **Custom events + custom metrics** — `recordEvent` plus
  `put-metrics-destination` on the app monitor.
- **Multi-Region apps** — per-Region app monitors; RUM does not
  merge across Regions.
