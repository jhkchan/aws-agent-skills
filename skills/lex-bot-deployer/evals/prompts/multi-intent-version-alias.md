# Eval: multi-intent-version-alias

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — multi-intent bot with ReturnIntent fulfillment, two bot versions, prod and staging aliases for blue-green deployment

## Prompt

Create a Lex V2 bot named MultiIntentBot in us-east-1 (account
123456789012). Locale en-US. Intents: BookFlight, CancelFlight,
CheckStatus, Greeting, Fallback. Each intent has required slots
with explicit priorities. Wire DIALOG_CODE_HOOK only (no fulfillment —
client handles action via ReturnIntent). Build the locale, create
bot version 1 and version 2, create alias prod pointing at version 1
and alias staging pointing at version 2 for blue-green deployment.
