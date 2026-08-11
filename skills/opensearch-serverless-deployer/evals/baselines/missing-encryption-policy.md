# Baseline (no-skill) response: missing-encryption-policy

This file captures what a generic assistant produces WITHOUT the
opensearch-serverless-deployer skill loaded — the contrast that proves
the skill catches the missing encryption policy (which must exist BEFORE
collection creation to bind the KMS key) that a generic assistant would
overlook.

---

To create your OpenSearch Serverless SEARCH collection:

1. Create the collection in the console or via CLI.
2. Set up the KMS key for encryption.
3. Configure network access.

Commands:

```
aws opensearchserverless create-collection --name prod-search --type SEARCH
```

After the collection is created, you can create an encryption policy
that references your KMS key abc-123. You can also create a network
policy for public access and a data access policy for your IAM roles.

The collection should be ready in about 15-30 minutes. Once it's
active, you can start indexing your product catalog data.
