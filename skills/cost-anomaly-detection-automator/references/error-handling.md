# Error Handling (load on demand) — Cost Anomaly Detection Automator

API error tables and failure remedies moved verbatim from SKILL.md. Loaded on demand.

---

## Step 3 — create-anomaly-subscription errors and fixes (moved from SKILL.md)

Common errors and fixes:

| Error | Cause | Fix |
|---|---|---|
| `ValidationException` on monitor ARN | Monitor still PENDING | Wait for ACTIVE, then retry |
| `AccessDeniedException` | CE service role missing | Ensure caller has `ce:CreateAnomalySubscription` |
| `LimitExceededException` | Too many subscriptions per monitor | Consolidate via SNS fan-out |
| No alerts despite subscription | SNS topic policy blocks CE | Add `events.costanomaly.amazonaws.com` as trusted publisher |
