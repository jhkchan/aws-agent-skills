# Baseline (no-skill) — lex-bot-ivr-integration

> This is the response a model produces **without** the skill
> definition. It references Lex V1 (deprecated; should be Lex V2 via
> InvokeAmazonLex block), uses a DRAFT alias (Connect invokes
> published aliases only), and does not verify the bot locale matches
> the instance language. Does not emit the READY_TO_DEPLOY checklist
> format. Generated for with-skill-vs-baseline comparison.

---

Add a Lex block to the flow:

```bash
aws connect update-contact-flow-content \
  --instance-id inst-abc123 \
  --contact-flow-id inbound-main-flow \
  --content '{"LexBot":{"Name":"CustomerService","Alias":"$LATEST"}}'
```

The Lex bot will elicit the department slot.
