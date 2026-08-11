# Baseline (no-skill) response: sbom-export-completed

This file captures what a generic assistant produces WITHOUT the
inspector2-coverage-operator skill loaded.

---

To export an SBOM from Inspector:

```bash
aws inspector2 start-sbom-export \
  --report-format CYCLONEDX_1_5 \
  --s3-destination bucketName=inspector-sbom-prod,keyPrefix=sbom/us-east-1/ \
  --region us-east-1
```

The export goes to the configured S3 bucket.
