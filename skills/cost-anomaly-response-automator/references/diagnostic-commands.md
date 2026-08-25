# Diagnostic commands - Cost Anomaly Response Automator

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Live-account pre-flight (run before generation, live accounts only)

**Live-account pre-flight (skip for offline authoring):**
1. `aws ce get-anomaly-monitors` (CAD enabled).
2. `aws cur describe-report-definitions` (CUR exists).
3. SNS topic exists or is in the template.
4. Lambda role has `ce:GetAnomalies` (read) + scoped action perms.
5. `aws budgets describe-budgets --account-id <payer>` (Budgets enabled).
