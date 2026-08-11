# Baseline (no-skill) — missing-parent-domain

> This is the response a model produces **without** the skill definition.
> It proceeds with the create-repository command without flagging that
> the parent domain `payments-team` does not exist — the command would
> fail with `ResourceNotFoundException` at runtime.

---

To create your CodeArtifact pip repository:

```bash
aws codeartifact create-repository \
  --domain payments-team \
  --repository payments-pip

aws codeartifact associate-external-connection \
  --domain payments-team \
  --repository payments-pip \
  --external-connection public:pypi
```

Grant your payments-ci and payments-release roles access to the
repository and you're good to go.
