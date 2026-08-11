# Baseline (no-skill) — maven-multiple-upstreams

> This is the response a model produces **without** the skill definition.
> It produces a create-repository command but misses the multi-hop upstream
> chain ordering (team-payments-internal -> shared-maven), the
> external-connection association on shared-maven (not on the team repo),
> and the `codeartifact login --tool mvn` CLI for CI.

---

Create your maven repository:

```bash
aws codeartifact create-repository \
  --domain shared \
  --repository team-payments-maven
```

Point upstream at shared-maven and then at maven-central. Attach the
external connection to team-payments-maven. Give payments-ci and
payments-release access.
