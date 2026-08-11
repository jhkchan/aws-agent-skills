# Eval prompt: rum-blocked-domain-missing-from-allowlist

Diagnose why RUM events from a beta subdomain are silently
dropped. Walk the pre-flight checks and emit the standard VERDICT
block (APPLICATION, VERDICT, CHECKLIST,
VERIFICATION_COMMANDS, REMEDIATION).

## Scenario

An operator wants to deploy RUM on a new subdomain
`https://checkout-beta.example.com`. The app monitor
`checkout-web-prod` in `us-east-1` has
`AllowedOrigins=["https://checkout.example.com"]` — the beta
subdomain is NOT listed.

## Known facts

- **Target domain:** `https://checkout-beta.example.com`.
- **App monitor `AllowedOrigins`:** only
  `https://checkout.example.com`.
- **Guest role:** `arn:aws:iam::111122223333:role/checkout-web-rum-guest`
  holds `rum:PutRumEvents` on the app monitor ARN.
- **Identity pool:** `us-east-1:abcd1234-efgh-5678`.
- **Cookie domain:** `.example.com`.
- **SDK integration:** CDN script tag.

## Symptom

The operator expects telemetry from the beta subdomain to flow
into the existing app monitor. Walk the pre-flight check for
`AllowedOrigins` and surface the gap.
