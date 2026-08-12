# Eval: event-based-cart-recovery

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — event-based entry, conditional split evaluating purchase_completed event, wait activities, quiet time (holds not cancels), journey limits

## Prompt

Create a Pinpoint journey named AbandonedCartRecovery in project
app-xyz789 (us-east-1, account 123456789012). Entry: event-based on
cart_abandoned event. Activities: SendReminderEmail, Wait1Hour,
ConditionalSplit (check if purchase_completed event recorded —
YES→ExitConverted, NO→SendReminderSMS), Wait24Hours. Email channel
configured. SMS channel configured. Quiet time 22:00-08:00 UTC
Mon-Fri. Journey limits: dailyCap 50000, maxEndpointSend 3.
Schedule start 2026-08-15T09:00:00Z.
