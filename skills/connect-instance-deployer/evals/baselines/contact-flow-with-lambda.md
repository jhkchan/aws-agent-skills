# Baseline (no-skill) — contact-flow-with-lambda

> This is the response a model produces **without** the skill
> definition. It lists the contact flow CLI but misses the Lambda
> resource policy requirement (without it, the InvokeLambda block
> returns Lambda.AccessDenied at run time), does not handle Lambda
> exceptions (AccessDenied, Timeout), and does not emit the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Create the contact flow:

```bash
aws connect create-contact-flow \
  --instance-id inst-abc123 \
  --name "inbound-main-flow" \
  --type CONTACT_FLOW \
  --content '{"Version":"2024-07-30","Actions":[{"Identifier":"invoke","Type":"Action","Parameters":{"FunctionARN":"arn:aws:lambda:us-east-1:123456789012:function:lookup-customer"}}]}'
```

Lambda will be invoked when the flow runs.
