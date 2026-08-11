# Eval: alias-reindex-zero-downtime

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — zero-downtime reindex from products-v1 to products-v2, add SKU keyword field, change metadata from object to nested, alias swap

## Prompt

Create a zero-downtime reindex plan on domain search-prod-abc
.us-east-1.es.amazonaws.com. Current index products-v1 needs a
mapping change: add a new SKU keyword field and change metadata
from object to nested. Create products-v2 with updated mappings.
Use alias products for read traffic. 5 primary shards, 1 replica.
Strict dynamic mapping. Tags: Environment=production.
