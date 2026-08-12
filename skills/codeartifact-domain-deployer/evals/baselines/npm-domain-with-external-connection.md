# Baseline (no-skill) — npm-domain-with-external-connection

> This is the response a model produces **without** the skill
> definition. It creates the domain and repository but misses the
> upstream cascade order (internal before public — supply-chain
> security), the 12-hour authorization token expiry (CI refresh
> requirement), the domain-as-IAM-boundary model, and the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Create the domain and repository:

```bash
aws codeartifact create-domain --domain my-domain
aws codeartifact create-repository --domain my-domain --repository my-team-packages
```

Add npmjs as upstream:

```bash
aws codeartifact update-repository \
  --domain my-domain \
  --repository my-team-packages \
  --upstreams external-connection=npmjs
```

Then run `aws codeartifact login` to get the auth token.
