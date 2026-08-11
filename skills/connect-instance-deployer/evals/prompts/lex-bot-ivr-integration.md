# Eval: lex-bot-ivr-integration

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — InvokeAmazonLex block on inbound-main-flow, Lex V2 bot CustomerService alias Prod (published), intent RouteCall, slot department, branch on department to sales-queue or support-queue

## Prompt

Add a Lex IVR block to the inbound-main-flow on instance
inst-abc123. Use Lex V2 bot CustomerService, alias Prod
(arn:aws:lex:us-east-1:123456789012:bot-alias/CustomerService:Prod).
Intent RouteCall, slot "department". Branch on department
value to sales-queue or support-queue.
