# Baseline (no-skill) response: vectorsearch-full-security

This file captures what a generic assistant produces WITHOUT the
opensearch-serverless-deployer skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, enumerated PRE_CHECKS,
specific STEPS with exact CLIs, expert knowledge of encryption-first
ordering, KMS symmetric key requirement, data access policy vs resource
policy distinction, standby replica cost doubling, and OCU floor).

---

Here's how to set up an OpenSearch Serverless collection for vector
search:

1. Create a collection in the AWS Console. Choose VECTORSEARCH as the
   type.
2. Set up a KMS key for encryption if you need customer-managed keys.
3. Configure the network — you can make it public or VPC-only.
4. Create an access policy so your application can read and write.
5. Set up standby replicas if you need high availability.
6. Configure your vector index with the right dimension.

Commands:

```
aws opensearchserverless create-collection --name prod-vectors --type VECTORSEARCH
aws opensearchserverless create-access-policy --name access --type data
```

The collection will take some time to create. Once it's active, you
can start indexing vectors.

For the KMS key, you can use any KMS key in your account. For the VPC
endpoint, make sure your subnets are in the right VPC. The data access
policy lets you control who can access the collection.

Let me know if you need help with the vector index mapping.
