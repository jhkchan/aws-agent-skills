# Eval: wait-activities-journey-limits

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — segment-based entry, duration and absolute-time waits, totalParticipantCap, daily quiet time

## Prompt

Create a Pinpoint journey named ReengagementCampaign in project
app-xyz789 (us-east-1, account 123456789012). Entry: segment-based
on segment seg-inactive-30d-789. Activities: SendReengagementEmail,
Wait 3 days (duration), SendReengagementSMS, Wait until
2026-09-01T10:00:00Z (absolute), SendFinalPush. Email, SMS, and
push channels configured. Quiet time 20:00-07:00 America/Los_Angeles
every day. Journey limits: dailyCap 20000, maxEndpointSend 3,
totalParticipantCap 100000.
