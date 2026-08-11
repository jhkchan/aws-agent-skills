# Eval prompt: rum-cdn-static-site-enable

Create a CloudWatch RUM app monitor and inject the CDN SDK. Walk
the pre-flight checks and emit the standard VERDICT block
(APPLICATION, VERDICT, CHECKLIST, VERIFICATION_COMMANDS).

## Scenario

An operator wants to enable CloudWatch RUM on
"checkout-web-prod" in `us-east-1`. The web app is served from
`https://checkout.example.com` (static HTML).

## Known facts

- **Domain:** `checkout.example.com` (served over HTTPS).
- **Identity pool:** `us-east-1:abcd1234-efgh-5678` (unauth path
  enabled).
- **Guest role:** `checkout-web-rum-guest` holds
  `rum:PutRumEvents` on
  `arn:aws:rum:us-east-1:111122223333:appmonitor/checkout-web-prod`.
- **Sample rate:** 1.0 (100% of sessions).
- **Telemetries:** errors, performance, http.
- **Cookie domain:** `.example.com` (cross-subdomain stitching).
- **Integration:** CDN script tag.
- **Application version:** `1.0.0`.

## Symptom

The operator needs the exact `create-app-monitor` CLI sequence
and the CDN script tag snippet with the `cwr('init', ...)`
configuration.
