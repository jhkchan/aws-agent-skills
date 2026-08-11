# Baseline (no-skill) — cross-account-domain-share

> This is the response a model produces **without** the skill definition.
> It mentions sharing but misses the both-must-allow contract (owner
> domain policy AND consumer IAM), the `--domain-owner` flag requirement
> for cross-account `codeartifact login`, and the RAM resource share
> pattern recommended for Organizations setups.

---

To share the domain with the consumer account:

```bash
aws ram create-resource-share \
  --name codeartifact-shared-domain \
  --principals arn:aws:iam::123456789012:root \
  --resource-arns arn:aws:codeartifact:us-east-1:123456789012:domain/shared
```

Then the consumer can log in:

```bash
aws codeartifact login --tool npm --domain shared --repository shared-npm
```
