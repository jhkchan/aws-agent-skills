# Baseline (no-skill) response: response-length-control

This file captures what a generic assistant produces WITHOUT the
bedrock-model-cost-optimizer skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, output token cost math,
max_tokens + structured output recommendation, dollar savings estimate,
CONFIRM gate).

---

Your product description generator is producing very long outputs —
1,200 tokens on average. Since output tokens are more expensive than
input tokens, this is driving most of your cost ($1,800 of your $2,040
monthly bill is output).

You should set a max_tokens limit to control the response length. If
you set it to 300 or 400, you'd cut your output costs significantly.
You could also ask the model to respond in JSON format which tends to
be more concise than prose.

```python
response = client.invoke_model(
    modelId='anthropic.claude-3-5-sonnet-20241022-v2:0',
    body=json.dumps({
        "max_tokens": 300,
        "messages": [...]
    })
)
```

This should reduce your output token costs by about 75% since you'd be
generating 300 tokens instead of 1,200.
