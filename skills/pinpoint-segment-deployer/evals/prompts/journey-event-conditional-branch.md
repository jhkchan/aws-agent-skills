# Eval: journey-event-conditional-branch

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — ENTRY → SEND → WAIT → CONDITIONAL_SPLIT (event purchase, 7-day wait) with YES branch SEND and NO branch MULTIVARIATE_SPLIT (50/50), all paths reach END

## Prompt

Build a Pinpoint journey on project app-abc123 named
"onboarding-7d". ENTRY → Send welcome-email → WAIT 3d →
CONDITIONAL_SPLIT on event "purchase" (wait 7 days): YES branch
→ Send thanks-email → END; NO branch → MULTIVARIATE_SPLIT
(50/50: discount-email → END, nudge-email → END). Email channel
verified. Segment active-mobile-7d.
