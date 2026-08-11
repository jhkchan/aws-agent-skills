# Eval prompt: email-campaign-full-security

Design a deployment plan for a production Pinpoint email campaign with an
A/B test. Emit the standard VERDICT block (CAMPAIGN, VERDICT, PRE_CHECKS,
STEPS, POST_VERIFY, CHANNEL, SEGMENT, SCHEDULE, QUIET_TIME,
FREQUENCY_CAP, AB_TEST).

Requirements:

- Project: app-abc123 (prod-engagement)
- Channel: email (SES identity example.com, verified SUCCESS in us-east-1,
  FromAddress: noreply@example.com)
- Segment: seg-premium (demographic — DeviceType=ios, tier=premium,
  lifecycle=active; resolves to 45230 endpoints)
- Templates: subject-a (email), subject-b (email), both with Liquid
  personalization using {{UserAttributes.FirstName}}
- Schedule: IMMEDIATE
- Quiet time: 22:00-08:00 America/New_York
- Frequency cap: 5/day (project-wide)
- A/B test: 10% holdout (control), 45% treatment-a (subject-a template),
  45% treatment-b (subject-b template)
- Event stream: arn:aws:kinesis:us-east-1:111111111111:stream/pinpoint-events
  (role arn:aws:iam::111111111111:role/PinpointStream with kinesis:PutRecord)

Existing-account context: the email channel is already enabled and the
SES identity example.com has been verified for 30 days. The segment
seg-premium was created last week. The operator holds
pinpoint:CreateCampaign and CreateEmailTemplate permissions.
