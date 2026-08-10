# Baseline (no-skill) — serverless-vector-search

> This is the response a model produces **without** the skill
> definition. It creates a managed cluster (instead of Serverless),
> misses the VECTORSEARCH collection type distinction, the VPC-
> endpoint requirement, the IAM Identity Center auth flow, and the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Here's how to set up vector search in OpenSearch:

```bash
aws opensearch create-domain \
  --domain-name prod-vectors \
  --engine-version OpenSearch_2.11 \
  --cluster-config InstanceType=r6g.2xlarge.search,InstanceCount=3
```

After the domain is active, create a k-NN index:

```bash
curl -X PUT "https://<endpoint>/products" \
  -H "Content-Type: application/json" \
  -d '{
    "settings": {"index": {"knn": true}},
    "mappings": {"properties": {"product-vector": {"type": "knn_vector", "dimension": 1536}}}
  }'
```

That should give you vector search.
