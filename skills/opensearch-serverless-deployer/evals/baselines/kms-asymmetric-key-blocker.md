# Baseline (no-skill) response: kms-asymmetric-key-blocker

This file captures what a generic assistant produces WITHOUT the
opensearch-serverless-deployer skill loaded — the contrast that proves
the skill catches the asymmetric KMS key blocker (SYMMETRIC_DEFAULT
requirement) that a generic assistant would miss.

---

Here's the deployment plan for your vector search collection:

1. Create the encryption policy referencing your KMS key.
2. Create a network policy for VPC access.
3. Create the collection with VECTORSEARCH type.

Commands:

```
aws opensearchserverless create-security-policy --name prod-encryption-semantic --type encryption --policy '{"Rules":[{"ResourceType":"collection","Resource":["collection/prod-semantic-search"]}],"KmsKeyArn":"arn:aws:kms:us-east-1:111111111111:key/def-456"}'
aws opensearchserverless create-collection --name prod-semantic-search --type VECTORSEARCH --standby-replicas ENABLED
```

Your KMS key def-456 should work fine for encryption. Just make sure
the key policy grants access to the OpenSearch Serverless service.

Once the collection is active, you can create your vector index and
start indexing documents.
