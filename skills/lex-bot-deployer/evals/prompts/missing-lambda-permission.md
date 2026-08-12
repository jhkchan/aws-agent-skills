# Eval: missing-lambda-permission

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — Lambda function lacks resource-based permission granting lexv2.amazonaws.com invoke access; code hook will silently fail at runtime

## Prompt

Create a Lex V2 bot named BrokenHookBot in us-east-1 (account
123456789012). Locale en-US. Intent: TestIntent with slot TestSlot
(required, priority 1, AMAZON.AlphaNumeric). Wire DIALOG_CODE_HOOK
to Lambda function OrderCoffeeFulfillment. The Lambda does NOT have
a resource-based permission granting lexv2.amazonaws.com invoke
access. Build, version 1, alias prod.
