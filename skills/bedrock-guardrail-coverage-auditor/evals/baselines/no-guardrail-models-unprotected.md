# Baseline (no-skill) response: no-guardrail-models-unprotected

This file captures what a generic assistant produces WITHOUT the
bedrock-guardrail-coverage-auditor skill loaded.

---

It looks like you don't have any guardrails set up in your Bedrock account.
This means your models, agents, and knowledge bases are running without any
content filtering or safety controls.

You should create a guardrail using the AWS Console or CLI. Go to the
Bedrock console, navigate to Guardrails, and create one with appropriate
content filters for your use case. Make sure to enable it and attach it to
your agents and applications.

Without guardrails, harmful content could be generated or processed without
any checks, which is a risk for production deployments.
