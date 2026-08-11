# Baseline (no-skill) — standard-ledger-verification

> This is the response a model produces **without** the skill
> definition. It creates the ledger but misses the importance of
> STANDARD permissions mode enforcement, does not explain the hash chain
> verification workflow (digest + proof), does not note that indexes
> must be created before queries, and omits the READY_TO_DEPLOY
> checklist format. Generated for with-skill-vs-baseline comparison.

---

Create the ledger:

```bash
aws qldb create-ledger \
  --name audit-ledger \
  --permissions-mode STANDARD \
  --deletion-protection \
  --region us-east-1
```

Then create tables and indexes using the QLDB shell. The ledger
is immutable and cryptographically verified.
