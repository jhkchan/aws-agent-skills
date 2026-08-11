# Eval prompt: severity-none-all-categories-missing

Design a deployment plan for an Amazon Bedrock Guardrail. Emit the
standard VERDICT block (GUARDRAIL_SPEC, VERDICT, CHECKLIST,
VERIFICATION_COMMANDS).

Requirements:

- Guardrail name: minimal-guardrail
- Region: us-east-1
- Content filters: sexual=NONE, violence=NONE, hate=NONE,
  insults=NONE (operator says "we'll set severity later")
- Denied topics: none
- Word filters: managed PROFANITY only
- PII filters: BLOCK for SSN only
- Applied to model: anthropic.claude-3-5-sonnet-20241022-v2:0

Additional context: the operator created a guardrail to "get
something in place" but left all content filter severities at NONE.
The guardrail exists in the console and appears configured, but NONE
means each filter is explicitly disabled. The model invocation is
running in production with this guardrail applied.
