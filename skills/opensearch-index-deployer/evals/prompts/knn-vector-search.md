# Eval: knn-vector-search

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — k-NN vector search index with 768 dimensions, HNSW method, cosinesimil space type, nmslib engine, ef_construction 512, m 48

## Prompt

Create a k-NN vector search index on domain search-vectordomain
-xyz789.us-east-1.es.amazonaws.com. 768-dimensional embeddings
from a sentence transformer model. Use HNSW method with cosine
similarity and nmslib engine. ef_construction 512, m 48. 3
primary shards, 1 replica. Index name vector-search-v1. Tags:
Environment=production, UseCase=semantic-search.
