# Baseline (no-skill) — pull-through-cache-docker-hub

> This is the response a model produces **without** the skill
> definition. It creates the cache rule but uses the wrong upstream
> URL format (docker.io instead of registry-1.docker.io), misses
> that the first pull triggers the cache fetch (slower) while
> subsequent pulls use the cached copy, and the READY_TO_DEPLOY
> checklist format. Generated for with-skill-vs-baseline comparison.

---

Create a pull-through cache rule:

```bash
aws ecr create-pull-through-cache-rule \
  --ecr-repository-prefix docker-hub/ \
  --upstream-registry-url docker.io
```

Then pull images using the prefix.
