# Eval prompt: insufficient-context-need-canary-name

Diagnose the following CloudWatch Synthetics canary failure. Walk the
diagnostic decision tree and emit the standard VERDICT block.

## Scenario

A user reports: "Our CloudWatch canary is failing and the alarm is
going off. The application name is checkout-service. Can you help?"

## Known facts

- The user mentioned the application name "checkout-service"
- The user did NOT provide:
  - The canary name
  - The region
  - The canary type (GUI Selenium, HTTP, API, broken-link, multi-step)
  - The run report error string
  - The CloudWatch metric pattern (SuccessPercent, Duration)
  - The canary ARN or alarm name
  - Whether a deployment occurred recently

## Symptom

Vague report of a canary failure without any identifying information
or diagnostic detail. Cannot begin diagnosis without the canary name
and region.
