# Eval prompt: timeout-stale-selector-dom-change

Diagnose the following CloudWatch Synthetics canary failure. Walk the
diagnostic decision tree and emit the standard VERDICT block (CANARY,
VERDICT, ROOT_CAUSE, FAILURE_TYPE, EVIDENCE, ROOT_CAUSE_CATALOG,
REMEDIATION).

## Scenario

A CloudWatch Synthetics canary `login-flow-canary` in `us-west-2` is
consistently hitting FAILED state. The on-call engineer was paged by
the CloudWatch alarm at 2026-08-08T22:05Z.

## Known facts

- Canary type: GUI Selenium WebDriver
- `describe-canary` shows:
  - `Type: gui`
  - `RuntimeVersion: synthetics-nodejs-4.0`
  - `RunConfig.TimeoutInSeconds: 60`
  - `Schedule.Expression: rate(5 minutes)`
- Run report (from `get-canary-runs`):
  - State: FAILED
  - No runtime exception thrown
  - Duration: consistently 59-60 seconds (the timeout limit)
  - Last logged step: "Waiting for dashboard element #welcome-banner"
  - No subsequent steps logged after this point
- Step results:
  - Step 1 (login): PASSED
  - Step 2 (dashboard): never completed — timed out
- CloudWatch `SuccessPercent`: 100% before 22:05Z, 0% after
- CloudWatch `Duration`: consistently 59-60s (at the timeout limit)
- The target application deployed at 2026-08-08T22:00Z:
  - The dashboard was redesigned
  - The `#welcome-banner` element was removed
  - It was replaced with `.dashboard-greeting`
  - The page loads normally (verified independently)
- The target URL is accessible and responds with 200 OK
- The login step succeeds — the timeout occurs AFTER login, waiting for
  the dashboard element

## Symptom

Canary timeout at the `TimeoutInSeconds` limit (60s). The last logged
step is waiting for a DOM element (`#welcome-banner`) that was removed
in a deployment. No runtime exception — the canary hangs waiting for
the element and hits the timeout.
