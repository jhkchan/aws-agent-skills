# Eval: segment-based-multivariate-holdout

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — segment-based entry, multivariate split 50/50, holdout 10% for control group, scheduled start/end

## Prompt

Create a Pinpoint journey named WeeklyPromoABTest in project
app-xyz789 (us-east-1, account 123456789012). Entry: segment-based
on segment seg-active-users-456. Activities: Holdout 10%,
MultivariateSplit (50% → SendVariantA email, 50% → SendVariantB
email). Email channel configured with templates promo-variant-a
and promo-variant-b. Schedule start 2026-08-20T09:00:00Z, end
2026-08-27T09:00:00Z, timezone America/New_York.
