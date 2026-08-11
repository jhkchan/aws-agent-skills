# Baseline (no-skill) response: es68-blocked-version-plugin

This file captures what a generic assistant produces WITHOUT the
opensearch-migration-operator skill loaded.

---

To migrate from Elasticsearch 6.8 to OpenSearch 2.11, you'll need to
upgrade your domain. You can try:

```bash
aws opensearch update-domain-config \
  --domain-name legacy-search-cluster \
  --engine-version OpenSearch_2.11
```

You have x-pack-ml and x-pack-sql plugins installed. You may need to
remove those before the migration since they might not be compatible
with OpenSearch. OpenSearch has its own ML and SQL plugins.

You should also set up a snapshot repository before making any changes.
Create an S3 bucket and register it as a snapshot repository on your
cluster.
