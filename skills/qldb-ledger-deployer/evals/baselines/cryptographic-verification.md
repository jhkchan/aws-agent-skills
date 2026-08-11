# Baseline (no-skill) — cryptographic-verification

> This is the response a model produces **without** the skill
> definition. It creates the ledger and mentions verification exists but
> does not document the digest + proof workflow in detail, does not
> explain the SHA-256 hash chain mechanics, does not note that digests
> should be stored externally for audit, and omits the READY_TO_DEPLOY
> checklist format. Generated for with-skill-vs-baseline comparison.

---

Create the ledger:

```bash
aws qldb create-ledger \
  --name compliance-ledger \
  --permissions-mode STANDARD \
  --deletion-protection \
  --region us-east-1
```

QLDB provides cryptographic verification. You can get a digest
and verify documents:

```bash
aws qldb get-digest --name compliance-ledger --region us-east-1
```

Then create your tables and start using it.
