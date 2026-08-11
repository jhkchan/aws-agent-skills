# Baseline (no-skill) — full-thing-cert-policy-binding

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the triple binding
> requirement (cert→thing AND policy→cert), the policy attaches to
> the certificate (not the thing), and the READY_TO_DEPLOY checklist
> format. Generated for with-skill-vs-baseline comparison.

---

Create the thing:

```bash
aws iot create-thing --thing-name sensor-001
```

Create a certificate:

```bash
aws iot create-keys-and-certificate --set-as-active
```

Create a policy and attach it:

```bash
aws iot create-policy --policy-name sensor-publish-policy --policy-document '...'
aws iot attach-policy --policy-name sensor-publish-policy --target arn:aws:iot:...:thing/sensor-001
```
