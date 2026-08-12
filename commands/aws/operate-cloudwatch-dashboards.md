---
description: Operate Amazon CloudWatch dashboard workflows — create/update dashboards via JSON model (PutDashboard API), add metric math expressions, anomaly detection bands, alarm widgets, cross-account dashboards via OAM, custom Lambda widgets, dashboard sharing, Metrics Insights queries, and version-controlled dashboard IaC — with deterministic pre-checks, CONFIRM gate, and post-verification.
nl_triggers:
  - "create CloudWatch dashboard"
  - "update dashboard JSON"
  - "PutDashboard API"
  - "metric math expression"
  - "anomaly detection band"
  - "add alarm to dashboard"
  - "cross-account dashboard"
  - "OAM shared observability"
  - "dashboard sharing"
  - "dashboard variables"
  - "custom widget Lambda"
  - "dashboard template"
  - "RDS monitoring dashboard"
  - "EC2 monitoring dashboard"
  - "Lambda monitoring dashboard"
  - "ECS monitoring dashboard"
  - "Metrics Insights query"
  - "version-controlled dashboard"
  - "dashboard IaC"
  - "CloudWatch dashboard management"
routes_to: cloudwatch-dashboards-operator
---

# /aws:operate-cloudwatch-dashboards

Activate the `cloudwatch-dashboards-operator` skill and plan/execute a
CloudWatch dashboard operation with deterministic pre-checks, CONFIRM
gate, and post-verification.

## What it does

Reads a dashboard specification (service type, metrics, layout) plus
the intended operation and applies the priority-ordered pre-check
sequence:

1. Pre-flight dashboard metadata gate — check for existing dashboard
   name conflict, namespace data availability, dimension value match.
2. Pre-check gate — verify dashboard JSON validity, Lambda custom-widget
   permissions, OAM sink/source configuration, anomaly detection
   training data.
3. Emit OPERATION_COMPLETED for straightforward operations (create,
   update via IaC, add metric math). Emit REVIEW_REQUIRED for operations
   needing human attention (cross-account OAM scope, dashboard sharing,
   custom Lambda widget code execution).
4. Execute behind CONFIRM gate — capture pre-state for diff, execute
   PutDashboard, verify body applied.
5. Post-verification — GetDashboard confirms body, widgets render with
   data, alarm widgets show state, cross-account @Account returns data.

Emits a deterministic VERDICT per operation:

```text
OPERATION: <create-dashboard | update-dashboard | add-metric-math | add-anomaly-detection | share-dashboard | enable-cross-account | add-custom-widget | delete-dashboard>
VERDICT: OPERATION_COMPLETED | REVIEW_REQUIRED
TARGET: <dashboard-name> (widgets: <count>)
PRE_CHECKS:
  - [PASS] <check description>
  - [REVIEW] <check description> — <item requiring human attention>
STEPS:
  1. <CLI command with dashboard JSON>
  2. <verification command>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
NOTES: <monitoring, caveats>
```

## When to invoke

Paste a dashboard specification plus the intended operation, or just
describe the scenario and ask any of:

- "create an RDS monitoring dashboard"
- "add an anomaly detection band to the Lambda dashboard"
- "set up cross-account dashboard visibility"
- "add a custom Lambda widget"
- "create a top-10 EC2 dashboard with Metrics Insights"
- "version-control our dashboards in Git"
- "share this dashboard with the security team"
- "update the dashboard with metric math for error rate"

A bare dashboard name + any dashboard verb ("create dashboard",
"update the dashboard") also routes here via the orchestrator.

## Inputs

- Dashboard specification: name, service type, metric names, widget
  layout preference, optional anomaly detection and Metrics Insights
  queries.
- For updates: current dashboard body via GetDashboard.
- For cross-account: OAM sink ID and source account IDs.
- For custom widgets: Lambda function ARN and resource-based policy.
- For sharing: target account IDs or OU IDs.

## Outputs

- One VERDICT block per operation.
- PRE_CHECKS list with `[PASS]` / `[REVIEW]` per check.
- For OPERATION_COMPLETED: POST_VERIFY list with `[PASS]` per check,
  the dashboard body for Git storage, monitoring recommendations.
- For REVIEW_REQUIRED: the specific items requiring human review
  (cross-account scope, sharing exposure, Lambda code execution,
  anomaly detection tuning) and the steps once approved.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 4 Operate specialist for CloudWatch dashboard operations).
- `/aws:audit-cloudwatch-alarms` for the audit-side counterpart —
  auditing alarm posture across many dashboards without changing state.
- `/aws:deploy-cloudwatch-cross-account-observability` for the deploy-
  side counterpart — provisioning OAM sinks and links for cross-account
  observability.
