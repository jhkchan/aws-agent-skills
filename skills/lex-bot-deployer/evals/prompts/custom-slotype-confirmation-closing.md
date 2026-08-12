# Eval: custom-slotype-confirmation-closing

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — custom slot type enumerations (PizzaSize, PizzaCrust), confirmation/closing/failure prompts, both code hooks wired

## Prompt

Create a Lex V2 bot named PizzaOrderBot in us-east-1 (account
123456789012). Locale en-US. Intent: OrderPizza with custom slot
types PizzaSize (values: small, medium, large) and PizzaCrust
(values: thin, thick, stuffed). Slots: PizzaSize (required, priority
1), PizzaCrust (required, priority 2), Quantity (optional, priority 3,
AMAZON.Number). Configure confirmation prompt "Should I order a
{Quantity} {PizzaSize} {PizzaCrust} pizza?", closing prompt "Your
pizza order is confirmed.", and failure prompt "Okay, I've cancelled
that." Wire DIALOG_CODE_HOOK and FULFILLMENT_CODE_HOOK to Lambda
PizzaOrderFulfillment. Build, version 1, alias prod.
