# Baseline (no-skill) response: unsupported-crr-requested-missing

This file captures what a generic assistant produces WITHOUT the
s3-directory-bucket-deployer skill loaded — the contrast that proves
the skill catches unsupported feature requests (CRR, versioning,
Object Lock) that a baseline would blindly attempt to configure.

---

Create the directory bucket:

```bash
aws s3api create-directory-bucket \
  --bucket production-data--use1-az1--x-s3 \
  --data-redundancy SingleAvailabilityZone
```

Then enable cross-region replication:

```bash
aws s3api put-bucket-replication \
  --bucket production-data--use1-az1--x-s3 \
  --replication-configuration file://crr-config.json
```

Enable versioning:

```bash
aws s3api put-bucket-versioning \
  --bucket production-data--use1-az1--x-s3 \
  --versioning-configuration Status=Enabled
```

Set up Object Lock as needed for compliance.
