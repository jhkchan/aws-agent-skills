# Baseline (no-skill) — kms-collection-face-index

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the KMS-at-creation
> requirement (KMS cannot be added after collection creation), the
> ExternalImageId best practice for traceability, the 80%+ similarity
> threshold production heuristic, and the READY_TO_DEPLOY checklist
> format. Generated for with-skill-vs-baseline comparison.

---

Create the collection:

```bash
aws rekognition create-collection --collection-id employee-faces
```

Then index faces:

```bash
aws rekognition index-faces \
  --collection-id employee-faces \
  --image '{"S3Object":{"Bucket":"my-face-bucket","Name":"employee-001.jpg"}}'
```

Search with default threshold.
