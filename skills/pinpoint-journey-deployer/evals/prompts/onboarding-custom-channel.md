# Eval: onboarding-custom-channel

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — event-based entry, multiple wait activities, custom Lambda channel for CRM webhook, push and email channels

## Prompt

Create a Pinpoint journey named UserOnboarding in project app-xyz789
(us-east-1, account 123456789012). Entry: event-based on user_signup
event. Activities: SendWelcomeEmail, Wait24Hours, SendTipsEmail,
Wait48Hours, Custom (Lambda function OnboardingWebhook for CRM
integration), Wait24Hours, SendCheckinPush. Email and push channels
configured. Lambda OnboardingWebhook deployed. No quiet time.
Journey limits: dailyCap 10000, maxEndpointSend 5.
