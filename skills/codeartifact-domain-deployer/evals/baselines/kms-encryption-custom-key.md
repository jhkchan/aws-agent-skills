# Baseline (no-skill) — kms-encryption-custom-key

> This is the response a model produces **without** the skill
> definition. It creates the domain with the KMS key but misses the
> encryption immutability warning (the key CANNOT be changed after
> domain creation), the KMS key policy requirement for CodeArtifact
> service access, and the READY_TO_DEPLOY checklist format. Generated
> for with-skill-vs-baseline comparison.

---

Create the domain with the KMS key:

```bash
aws codeartifact create-domain \
  --domain secure-domain \
  --encryption-key arn:aws:kms:us-east-1:123456789012:key/abcd1234-ef56-7890-abcd-ef1234567890
```

Create the repository:

```bash
aws codeartifact create-repository \
  --domain secure-domain \
  --repository dotnet-packages
```

Done.
