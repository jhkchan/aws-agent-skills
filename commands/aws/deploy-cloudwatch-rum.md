---
description: Provision CloudWatch RUM (Real User Monitoring) app monitors with domain allow-list, sample rate, cookie domain, telemetries (errors, performance, HTTP), X-Ray trace correlation, custom events, custom metrics, and the CloudWatch RUM JavaScript SDK integrated via CDN or npm. Wires Application Signals client-side correlation and emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "cloudwatch rum"
  - "real user monitoring"
  - "rum app monitor"
  - "enable rum"
  - "rum javascript sdk"
  - "rum web client"
  - "rum cdn"
  - "rum npm"
  - "aws-rum-web"
  - "cookie domain rum"
  - "custom events rum"
  - "rum custom metrics"
  - "x-ray rum correlation"
  - "application signals client correlation"
  - "rum application signals"
  - "web vitals cloudwatch"
  - "client-side observability"
  - "rum session sampling"
  - "rum put-metrics-destination"
  - "cognito guest role rum"
routes_to: cloudwatch-rum-deployer
---

# /aws:deploy-cloudwatch-rum

Activate the `cloudwatch-rum-deployer` skill and provision
CloudWatch RUM with production-grade configuration.

## What it does

The skill walks a 10-step enablement procedure and emits a
READY_TO_DEPLOY checklist:

1. Create the app monitor (name, domain, sample rate, telemetries)
2. Create the anonymous guest IAM role (Cognito identity pool)
3. Inject the RUM JavaScript SDK (CDN script tag or npm import)
4. Configure the cookie domain (cross-subdomain session stitching)
5. Configure X-Ray trace correlation (header propagation)
6. Record custom events (snake_case types, 64 KB payload cap)
7. Configure RUM custom metrics (put-metrics-destination)
8. Wire Application Signals client-side correlation
9. Verify telemetry is flowing (AWS/RUM namespace populated)
10. Tag, alarm, and visualize

## When to use

- You want to enable CloudWatch RUM on a static site, SPA, or
  SSR app with the CDN or npm SDK pattern.
- You are wiring cookie domain, session sampling, or telemetry
  selection (errors, performance, http).
- You want to record custom events and expose them as CloudWatch
  custom metrics in the AWS/RUM namespace.
- You are enabling X-Ray trace correlation between client-side
  RUM sessions and server-side X-Ray segments.
- You want Application Signals client/server service-map
  correlation via the AWS/ApplicationSignalsClient namespace.
- You want to check for enablement blockers (domain not in
  AllowedOrigins, missing guest role, 0% X-Ray sampling, server
  workload not discovered by Application Signals).

## How to invoke

### Slash command

```
/aws:deploy-cloudwatch-rum
```

Then provide: application name, domain (scheme + host + port),
sample rate, telemetries, cookie domain, guest role ARN +
identity pool ID, X-Ray tracing flag, custom event / metric
details, and Application Signals correlation preference.

### Natural language

Any of these routes to the same skill:

- "enable cloudwatch rum on checkout-web-prod"
- "create a rum app monitor for the marketing site"
- "wire x-ray correlation for rum"
- "record a checkout_complete custom event in rum"
- "expose a rum custom metric CartValueTotal"
- "correlate rum sessions with application signals"

### CLI routing

```bash
node cli/bin/cli.js route "deploy cloudwatch rum"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps
pipeline. The output checklist feeds into verification pipelines
and downstream auditor skills (e.g., a CloudWatch alarm auditor
for RUM error spikes, and the
`cloudwatch-application-signals-deployer` skill which completes
the server side of the service-map correlation).

## Example

```
You: /aws:deploy-cloudwatch-rum

     Enable CloudWatch RUM on checkout-web-prod in us-east-1.
     Domain https://checkout.example.com. Cookie domain
     .example.com. 100% session sampling, errors / performance /
     http telemetries, X-Ray enabled. Identity pool
     us-east-1:abcd1234-efgh-5678, guest role
     arn:aws:iam::111122223333:role/checkout-web-rum-guest.
     CDN integration for the static site, npm for the React
     migration. Record a checkout_complete event and a
     CartValueTotal custom metric. Account: 111122223333.

Skill:
  APPLICATION: checkout-web
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓]      Domain — https://checkout.example.com (validated against AllowedOrigins)
    [✓]      App monitor — arn:aws:rum:us-east-1:111122223333:appmonitor/checkout-web-prod
    [✓]      Sample rate — 1.0
    [✓]      Cookie domain — .example.com
    [✓]      Telemetries — errors, performance, http
    [✓]      IAM auth — guest role checkout-web-rum-guest with rum:PutRumEvents
    [✓]      SDK integration — CDN script tag (static) + npm (React migration)
    [✓]      Custom events — checkout_complete (snake_case)
    [✓]      Custom metrics — AWS/RUM CartValueTotal via $.event.data.cartValue
    [✓]      X-Ray tracing — enabled; server-side sampling rule FixedRate=0.05
    [✓]      Application Signals correlation — AWS/ApplicationSignalsClient namespace wired
  VERIFICATION_COMMANDS:
    aws rum list-app-monitors --region us-east-1
    aws rum get-app-monitor --name checkout-web-prod --region us-east-1
    aws cloudwatch list-metrics --namespace AWS/RUM --dimensions Name=ApplicationName,Value=checkout-web-prod
    aws cloudwatch list-metrics --namespace AWS/ApplicationSignalsClient --region us-east-1
    aws xray get-sampling-rules --region us-east-1
    aws iam list-attached-role-policies --role-name checkout-web-rum-guest
```

## References

- Skill definition: `skills/cloudwatch-rum-deployer/SKILL.md`
- Deployment CLI commands: `skills/cloudwatch-rum-deployer/references/deployment-cli-commands.md`
- Custom events and correlation guide: `skills/cloudwatch-rum-deployer/references/custom-events-and-correlation-guide.md`
- Eval suite: `skills/cloudwatch-rum-deployer/evals/evals.json`
