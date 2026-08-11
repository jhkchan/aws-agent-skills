# Baseline (no-skill) — swift-repo-with-region-check

> This is the response a model produces **without** the skill definition.
> It blindly associates the `public:swift` external connection without
> checking Region availability — the association would fail at runtime
> with a ResourceNotFoundException or similar.

---

Create your Swift repository:

```bash
aws codeartifact create-repository \
  --domain mobile-shared \
  --repository mobile-shared-swift

aws codeartifact associate-external-connection \
  --domain mobile-shared \
  --repository mobile-shared-swift \
  --external-connection public:swift
```

Give mobile-ci access and you're ready to publish Swift packages.
