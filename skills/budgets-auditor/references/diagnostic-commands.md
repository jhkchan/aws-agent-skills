# budgets-auditor — diagnostic commands (moved from SKILL.md)

Progressive-disclosure reference. Content below was moved verbatim from SKILL.md; the agent loads it only when needed.

## Live-account sweep note (pagination)

**Live-account sweep note (pagination):** `aws budgets describe-budgets` is
paginated via `--next-token` and returns at most 100 budgets per page on a
payer. For each budget, page `aws budgets describe-notifications-for-budget`
(up to 100/page) and, for each notification, `aws budgets
describe-subscribers-for-notification`. Always drain `NextToken` to completion
— the long tail of stale, decorative, or breached budgets hides beyond page
one. Budgets are **account-scoped, not regional**; the Budgets API endpoint is
`us-east-1` regardless of where workloads run, so always query
`--region us-east-1`.

## Live-account pre-flight checks

1. Confirm the caller identity has `budgets:DescribeBudget*` and
   `sns:GetTopicAttributes`. A read-only auditor role without SNS read
   permission will silently skip Step 3 (the SNS policy check) — the most
   common misclassification source. Surface this BEFORE the operator trusts an
   OK verdict.
2. For consolidated-billing (Organizations) accounts, run
   `aws organizations list-accounts` and audit the **payer** budget inventory.
   A payer budget with no `LinkedAccount` filter covers ALL member accounts; a
   member account with no own budget and no payer visibility is a blind spot.
3. Snapshot `aws budgets describe-budget-performance-history --account-id <id>`
   when available — it shows whether a budget has historically breached,
   calibrating whether a CONFIG_GAP is theoretical or recurring.
