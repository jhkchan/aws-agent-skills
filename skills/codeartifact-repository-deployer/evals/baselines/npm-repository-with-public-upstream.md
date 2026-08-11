# Baseline (no-skill) — npm-repository-with-public-upstream

> This is the response a model produces **without** the skill definition.
> It produces a basic create-repository command but misses the structured
> READY_TO_DEPLOY checklist, the upstream chain ordering (internal-first,
> external-last), the separated consume vs publish IAM policies, the
> `codeartifact login` CLI for CI, and the verification commands.

---

To create your CodeArtifact npm repository:

```bash
aws codeartifact create-repository \
  --domain shared \
  --repository shared-npm

aws codeartifact associate-external-connection \
  --domain shared \
  --repository shared-npm \
  --external-connection public:npmjs
```

Then set up upstream to shared-internal. Give your CI and release
roles access to the repository.
