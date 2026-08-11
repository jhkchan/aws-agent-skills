# Eval: dynamic-segment-recompute

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — dynamic segment (Behavior DAY_7 ACTIVE + Demographic Channel GCM/APNS), scheduled email campaign 7 days out, dynamic-recompute behavior flagged (segment size will differ at send time)

## Prompt

Create a Pinpoint dynamic segment on project app-abc123 named
"active-mobile-7d". Use Behavior: Recency DAY_7 ACTIVE. Use
Demographic: Channel INCLUSIVE [GCM, APNS]. Create a scheduled
campaign firing 7 days from now targeting this segment via email
template welcome-email. The email channel is already verified
(SES identity arn example.com). Project ID app-abc123.
