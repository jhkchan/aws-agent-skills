# Baseline (no-skill) — cross-account-resource-policy

> This is the response a model produces **without** the skill
> definition. It creates the stream but misses the stream ARN resource
> policy (put-resource-policy) for cross-account access, the
> requirement that the consuming account ALSO needs an identity-based
> IAM policy, and the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Create the stream:

```bash
aws kinesis create-stream --stream-name shared-events --shard-count 1
```

For cross-account access, you can use IAM roles or share it some other
way.
