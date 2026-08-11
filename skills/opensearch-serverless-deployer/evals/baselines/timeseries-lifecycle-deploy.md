# Baseline (no-skill) response: timeseries-lifecycle-deploy

This file captures what a generic assistant produces WITHOUT the
opensearch-serverless-deployer skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, lifecycle policy
ordering, standby replica cost visibility, OCU floor enforcement, and
data access policy requirement).

---

To create an OpenSearch Serverless collection for logs:

1. Go to the OpenSearch Serverless console.
2. Create a new collection. Select TIMESERIES type.
3. For encryption, you can use the default AWS-owned key or your own
   KMS key.
4. Set the network to public since your application will access it
   directly.
5. Enable standby replicas for production.

Commands:

```
aws opensearchserverless create-collection --name prod-logs --type TIMESERIES
```

You might want to set up a lifecycle policy to manage log retention,
but that's optional. The collection will auto-scale based on your
workload.

For data access, you should be able to use the collection once it's
created. If you need to grant access to other roles, you can add an
access policy later.

The collection should be ready in about 15-30 minutes.
