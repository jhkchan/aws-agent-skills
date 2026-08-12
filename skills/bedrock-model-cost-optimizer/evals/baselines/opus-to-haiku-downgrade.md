# Baseline (no-skill) response: opus-to-haiku-downgrade

This file captures what a generic assistant produces WITHOUT the
bedrock-model-cost-optimizer skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, Haiku cost-differential
citation, prompt caching math, dollar savings estimate, CONFIRM gate,
canary workflow).

---

Your customer support chatbot is using Claude Opus, which is the most
expensive model. For a FAQ Q&A use case where responses are only 180
tokens, you're massively overpaying. Claude Haiku would be much cheaper
and can easily handle simple questions.

The system prompt of 2,000 tokens is sent on every call, which adds up
with 200,000 invocations per month. You should look into prompt caching
to reduce that cost.

I'd recommend switching to Claude Haiku. You can do this by changing
the modelId in your API call:

```python
client.invoke_model(
    modelId='anthropic.claude-3-haiku-20240307-v1:0',
    ...
)
```

This should save you a significant amount of money each month.
