# Baseline (no-skill) response: prompt-caching-opportunity

This file captures what a generic assistant produces WITHOUT the
bedrock-model-cost-optimizer skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, cache hit rate analysis,
write-premium math, dollar savings estimate, CONFIRM gate).

---

Your legal document analyser is sending a 2,800-token system prompt on
every invocation with Claude Sonnet. That's a lot of repeated input
tokens. With 60,000 invocations per month, you're paying for those
2,800 tokens 60,000 times.

Bedrock has a prompt caching feature that can cache repeated prompt
prefixes. You should enable it for your system prompt. This would
reduce the cost of those input tokens significantly.

To enable it, add a cache_control parameter to your system prompt in
the API call:

```python
"system": [
    {
        "type": "text",
        "text": "<your legal instructions>",
        "cache_control": {"type": "ephemeral"}
    }
]
```

This should cut your input token costs quite a bit since the cache
lasts for 5 minutes and you're getting about 2 requests per second.
