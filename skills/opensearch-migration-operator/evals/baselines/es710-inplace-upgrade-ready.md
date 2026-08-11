# Baseline (no-skill) response: es710-inplace-upgrade-ready

This file captures what a generic assistant produces WITHOUT the
opensearch-migration-operator skill loaded.

---

You can upgrade your Elasticsearch 7.10 domain to OpenSearch 2.11 using
the AWS CLI. Run this command:

```bash
aws opensearch update-domain-config \
  --domain-name prod-search-cluster \
  --engine-version OpenSearch_2.11 \
  --region us-east-1
```

This will perform a blue/green deployment where AWS provisions new nodes
with OpenSearch, migrates your data, and switches traffic. The endpoint
should remain the same.

Make sure to take a snapshot before upgrading as a backup. You can check
the upgrade progress with:

```bash
aws opensearch describe-domain --domain-name prod-search-cluster
```

Your plugins (analysis-icu, analysis-phonetic, ingest-attachment) should
all work in OpenSearch since they're built-in. Just update your client
library to the OpenSearch client when you're ready.
