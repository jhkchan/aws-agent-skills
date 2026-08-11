# Baseline (no-skill) response: missing-required-fields

This file captures what a generic assistant produces WITHOUT the
opensearch-serverless-deployer skill loaded — the contrast that proves
the skill identifies missing required fields (collection type, encryption,
network) and emits a structured PREREQUISITES_MISSING verdict rather
than guessing.

---

Sure! To create an OpenSearch Serverless collection called prod-data:

1. Go to the OpenSearch Serverless console.
2. Click Create collection.
3. Enter the name prod-data.
4. Choose a type — SEARCH is good for general use.
5. Use the default encryption (AWS-owned key).
6. Set network to public for now.

Commands:

```
aws opensearchserverless create-collection --name prod-data --type SEARCH
```

You can always change the configuration later if needed. The
collection will auto-scale based on your workload.

Let me know what kind of data you want to store and I can help you set
up the index mapping.
