# Eval: coffee-order-dialog-codehook

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — full bot with custom slot types, explicit slot priorities, both DIALOG_CODE_HOOK and FULFILLMENT_CODE_HOOK wired, conversation logs, KMS encryption, version and alias

## Prompt

Create a Lex V2 bot named OrderCoffeeBot in us-east-1 (account
123456789012). Locale en-US, NLU confidence threshold 0.40. Intents:
OrderCoffee, Greeting, Fallback. OrderCoffee has slots CoffeeSize
(required, priority 1, custom slot type CoffeeSizeType), CoffeeDrink
(required, priority 2, custom slot type CoffeeDrinkType), and
CoffeeTemp (optional, priority 3, AMAZON.AlphaNumeric). Wire both
DIALOG_CODE_HOOK and FULFILLMENT_CODE_HOOK to Lambda function
OrderCoffeeFulfillment. Enable conversation logs (text only) to
CloudWatch Logs group /aws/lex/OrderCoffeeBot. KMS CMK abc-def-123
for encryption. Build the locale, create bot version 1, and alias
prod pointing at version 1.
