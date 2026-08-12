# Baseline (no-skill) — cross-account-repository-policy

> This is the response a model produces **without** the skill
> definition. It creates the domain and repository but misses the
> repository policy requirement for cross-account access (the
> consumer account needs codeartifact:ReadFromRepository granted
> explicitly), the consumer login needing the domain owner account
> ID, and the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Create the domain and repository:

```bash
aws codeartifact create-domain --domain shared-artifacts
aws codeartifact create-repository --domain shared-artifacts --repository data-science-pkgs
```

The consumer account can just log in:

```bash
aws codeartifact login --tool pip --domain shared-artifacts --repository data-science-pkgs
```
