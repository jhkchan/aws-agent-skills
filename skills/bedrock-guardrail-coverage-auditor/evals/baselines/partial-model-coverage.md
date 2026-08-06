# Baseline (no-skill) response: partial-model-coverage

This file captures what a generic assistant produces WITHOUT the
bedrock-guardrail-coverage-auditor skill loaded.

---

Your guardrail looks well-configured with READY status, good content filters,
and proper grounding thresholds. However, it seems like not all of your
resources are using it. The content-writer-agent, chat-app, and
summarizer-app don't have the guardrail attached.

You should add the guardrail configuration to those resources. For agents,
you can update them with the guardrail identifier. For your applications,
make sure to pass the guardrail ID when calling the Bedrock API.

It's important that all resources use the guardrail, otherwise some of your
traffic won't be protected.
