# Baseline (no-skill) — missing-kms-key

> This is the response a model produces **without** the skill
> definition. It attempts to create the collection without KMS (since
> no key is provided), missing the critical fact that KMS encryption
> CANNOT be added after collection creation. Generated for
> with-skill-vs-baseline comparison.

---

Create the collection:

```bash
aws rekognition create-collection --collection-id secure-faces
```

Then index faces:

```bash
aws rekognition index-faces --collection-id secure-faces \
  --image '{"S3Object":{"Bucket":"...","Name":"..."}}'
```

You can add KMS encryption later.
