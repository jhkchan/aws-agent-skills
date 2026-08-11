# Baseline (no-skill) response: snapshot-setup-blocked-no-s3-bucket

This file captures what a generic assistant produces WITHOUT the
opensearch-migration-operator skill loaded.

---

To set up a snapshot repository for your Elasticsearch domain, you'll
need to create an S3 bucket first. Here's how:

```bash
aws s3 mb s3://migration-snapshots-bucket
```

Then register it as a snapshot repository:

```
PUT _snapshot/s3-repo
{
  "type": "s3",
  "settings": {
    "bucket": "migration-snapshots-bucket"
  }
}
```

You'll also need to make sure your IAM role has the right S3 permissions.
It looks like it's missing s3:PutObject. Add that permission to the role
policy and you should be good to go.
