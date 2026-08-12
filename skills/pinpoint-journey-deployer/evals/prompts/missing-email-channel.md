# Eval: missing-email-channel

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — project app-broken456 does not have email channel configured (no SES verified identity); send email activities will fail

## Prompt

Create a Pinpoint journey named NewsletterJourney in project
app-broken456 (us-east-1, account 123456789012). Entry: segment-based
on segment seg-subscribers-999. Activities: SendNewsletterEmail,
Wait7Days, SendFollowUpEmail. The email channel is NOT configured on
project app-broken456 (no SES verified identity). Schedule start
2026-08-15T09:00:00Z.
