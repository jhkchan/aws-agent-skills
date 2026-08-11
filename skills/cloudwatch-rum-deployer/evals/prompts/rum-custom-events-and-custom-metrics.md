# Eval prompt: rum-custom-events-and-custom-metrics

Record a `checkout_complete` custom event and configure a RUM
custom metric `CartValueTotal` extracted from the event payload.
Walk the pre-flight checks and emit the standard VERDICT block
(APPLICATION, VERDICT, CHECKLIST, VERIFICATION_COMMANDS).

## Scenario

An operator wants to track checkout funnel completion in RUM on
app monitor `checkout-web-prod` (`us-east-1`). They want to
record a custom event and expose a CloudWatch custom metric on
the extracted value.

## Known facts

- **App monitor:** `checkout-web-prod` exists; SDK already loaded
  via npm (`aws-rum-web`).
- **Event type:** `checkout_complete` (snake_case).
- **Event payload:**
  `{cartValue: 142.50, itemCount: 3, paymentMethod: "card"}`.
- **Custom metric name:** `CartValueTotal`.
- **Metric namespace:** `AWS/RUM`.
- **Value extraction path:** `$.event.data.cartValue`.
- **Identity pool / guest role:** already wired; operator only
  needs the `recordEvent` call and the
  `put-metrics-destination` CLI.

## Symptom

The operator needs the `recordEvent` call (npm and CDN forms) and
the exact `put-metrics-destination` CLI command to extract
`CartValueTotal` into the `AWS/RUM` namespace.
