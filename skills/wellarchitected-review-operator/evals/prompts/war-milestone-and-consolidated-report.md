# Eval prompt: war-milestone-and-consolidated-report

Create a milestone after the quarterly review is complete and
generate a PDF consolidated report. Walk the pre-flight checks
and emit the standard VERDICT block.

## Scenario

An operator has finished a quarterly review of workload
"checkout-service" (id `workload-abc123`) in `us-east-1`.

## Known facts

- **Workload id:** `workload-abc123`.
- **Review state:** all six base pillars plus Prosperity have
  every question answered (verified via `list-answers` for
  each pillar).
- **Milestone name:** `2026-Q3-baseline`.
- **Report format:** PDF.
- **Caller permissions:** `wellarchitected:CreateMilestone` and
  `wellarchitected:GetConsolidatedReport`.

## Symptom

The operator needs the `create-milestone` CLI to snapshot the
review at "2026-Q3-baseline", followed by the
`get-consolidated-report --format PDF` CLI for the executive
report. Confirm both succeed and emit `COMPLETED`.
