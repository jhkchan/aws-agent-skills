# Eval prompt: rum-npm-spa-with-xray

Inject the `aws-rum-web` npm SDK in a React SPA with X-Ray trace
correlation and cookie domain configured. Walk the pre-flight
checks and emit the standard VERDICT block (APPLICATION, VERDICT,
CHECKLIST, VERIFICATION_COMMANDS).

## Scenario

An operator wants to integrate CloudWatch RUM into a React SPA
"checkout-web" in `us-east-1` via the `aws-rum-web` npm package.

## Known facts

- **App monitor:** `checkout-web-prod` already exists with
  `EnableXRay=true` and
  `AllowedOrigins=["https://app.example.com"]`.
- **Server workload:** `checkout-api` is enabled for Application
  Signals; X-Ray Default sampling rule `FixedRate=0.05`.
- **Identity pool:** `us-east-1:abcd1234-efgh-5678`.
- **Guest role:** `arn:aws:iam::111122223333:role/checkout-web-rum-guest`
  holds `rum:PutRumEvents` on the app monitor ARN.
- **Cookie domain:** `.example.com`.
- **X-Ray:** `enableXRay=true` in the SDK config (client-to-server
  trace correlation desired).
- **Application version:** `1.0.0`.

## Symptom

The operator needs the npm install command, the `AwsRum`
constructor pattern, and confirmation that client/server trace
correlation will work end-to-end.
