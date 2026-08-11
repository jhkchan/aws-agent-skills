# Eval prompt: visual-monitoring-mismatch-post-deploy

Diagnose the following CloudWatch Synthetics canary failure. Walk the
diagnostic decision tree and emit the standard VERDICT block (CANARY,
VERDICT, ROOT_CAUSE, FAILURE_TYPE, EVIDENCE, ROOT_CAUSE_CATALOG,
REMEDIATION).

## Scenario

A CloudWatch Synthetics canary `checkout-ui-canary` in `us-east-1`
transitioned to FAILED state at `2026-08-09T14:02Z`. The application
team received a CloudWatch alarm notification.

## Known facts

- Canary type: GUI Selenium WebDriver
- `describe-canary` shows:
  - `Type: gui`
  - `RuntimeVersion: synthetics-nodejs-5.0`
  - `RunConfig.TimeoutInSeconds: 60`
  - `VisualTesting.Tolerance: 1`
  - `Schedule.Expression: rate(5 minutes)`
- Run report (from `get-canary-runs`):
  - State: FAILED
  - Error: `VisualMonitoringBaselineMismatch` on step 3 (payment-page)
  - Delta: 12.4% pixel difference vs 1% tolerance
  - Duration: 18 seconds (normal)
  - Steps 1-2 PASSED, step 3 FAILED on visual comparison
- CloudWatch `SuccessPercent`: 100% before 14:02Z, 0% after
- CloudWatch `Duration`: 18s average (unchanged)
- The `checkout-ui` service deployed a redesign at
  `2026-08-09T14:00Z` (confirmed via CodePipeline deployment record)
- The step 3 screenshot shows: "Pay Now" button moved from
  right-aligned to center, and a new trust badge appears below the total
- The canary functionally completed all steps (clicks, navigation) —
  only the visual comparison failed

## Symptom

`VisualMonitoringBaselineMismatch` on step 3, with a 12.4% pixel delta.
The canary started failing immediately after a confirmed UI deployment.
The canary functionally succeeded — only the visual comparison flagged
the delta.
