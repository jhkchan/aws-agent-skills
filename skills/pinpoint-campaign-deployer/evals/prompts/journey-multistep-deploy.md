# Eval prompt: journey-multistep-deploy

Design a deployment plan for a Pinpoint multi-step onboarding journey.
Emit the standard VERDICT block.

Requirements:

- Project: app-abc123 (prod-engagement)
- Channel: email (SES identity example.com, verified SUCCESS in us-east-1)
- Journey name: onboarding-flow
- Entry: segment-based (seg-new-users, 12000 endpoints — users who signed
  up in the last 7 days)
- Activities (in order):
  1. ENTRY -> send-welcome
  2. SEND welcome email (template: welcome-email, Liquid
     {{UserAttributes.FirstName}})
  3. WAIT 24 hours (PT24H)
  4. CONDITIONAL_SPLIT on app_open event in the last 1 day
     - True (user opened app) -> END (engaged, no nudge needed)
     - False (user did not open app) -> send-nudge
  5. SEND nudge email (template: nudge-email)
  6. END
- Quiet time: 22:00-08:00 America/New_York
- State: DRAFT (review before enabling)

Existing-account context: the email channel is enabled. Templates
welcome-email and nudge-email already exist. The segment seg-new-users
resolves to 12000 endpoints. The operator holds pinpoint:CreateJourney
permission.
