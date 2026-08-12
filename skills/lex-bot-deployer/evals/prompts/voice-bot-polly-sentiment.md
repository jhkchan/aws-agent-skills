# Eval: voice-bot-polly-sentiment

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — voice bot with Polly neural Joanna, sentiment analysis enabled, Twilio SMS channel integration with Secrets Manager credentials

## Prompt

Create a Lex V2 voice bot named CustomerSupportBot in us-east-1
(account 123456789012). Locale en-US, Polly neural voice_id Joanna.
Enable sentiment analysis. Intent: HandleComplaint with slots
IssueType (required, priority 1, AMAZON.AlphaNumeric) and Severity
(required, priority 2, AMAZON.Number). Wire DIALOG_CODE_HOOK and
FULFILLMENT_CODE_HOOK to Lambda ComplaintHandler. Build, version 1,
alias prod. Integrate Twilio SMS channel (credentials in Secrets
Manager twilio/customersupport).
