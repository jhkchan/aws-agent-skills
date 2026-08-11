# Baseline (no-skill) — co-password-and-quorum

> This is the response a model produces **without** the skill
> definition. It creates CO users without flagging that the CO
> password is not recoverable, omits the quorum policy, and does
> not prescribe Secrets Manager + KMS encryption. Generated for
> with-skill-vs-baseline comparison.

---

Create the CO users:

```bash
cloudhsm-cli user create --username admin --role CO --password '...'
cloudhsm-cli user create --username officer2 --role CO --password '...'
```

That should cover it.
