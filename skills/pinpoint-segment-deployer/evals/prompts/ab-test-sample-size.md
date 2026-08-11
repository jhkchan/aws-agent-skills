# Eval: ab-test-sample-size

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — A/B test sample-size gate (18,000 / 3 treatments = 6,000 per treatment ≥ 5,000 threshold for 2-3% MDE); holdout 20% + treatments 40/20/20 sum to 100

## Prompt

Build an A/B test email campaign on project app-abc123. Segment
active-mobile-7d resolves to 18,000 endpoints. Three treatments
(subject-a, subject-b, subject-c) plus a 20% holdout. Treatment
percentages: 40/20/20 (holdout 20). Target MDE is 2%. Verify
sample-size adequacy before emitting create-campaign.
