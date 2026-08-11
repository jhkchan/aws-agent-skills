# Vector Search and Semantic Search Reference

Supplementary reference for the OpenSearch Serverless Deployer skill.
Use when configuring VECTORSEARCH collections, k-NN indexes, semantic
search with embeddings, or flow frameworks.

## VECTORSEARCH collection type

The `VECTORSEARCH` collection type is optimized for high-dimensional vector
similarity search. It supports:

- **k-NN (k-nearest neighbors)** search using HNSW or IVF algorithms.
- **Engines:** `faiss` (recommended) and `nmslib` (legacy).
- **Space types:** `cosinesimil`, `l2`, `innerproduct` (faiss only).
- **Hybrid search:** combine k-NN vector scores with lexical (BM25) scores.

### When to use VECTORSEARCH vs SEARCH

| Use case | Collection type |
|---|---|
| Semantic search / RAG / Q&A | VECTORSEARCH |
| Image similarity / visual search | VECTORSEARCH |
| Recommendation systems | VECTORSEARCH |
| Full-text search with no vectors | SEARCH |
| Hybrid (text + vector) | VECTORSEARCH with hybrid query |

## k-NN index configuration

### Index mapping (faiss HNSW)

```json
{
  "mappings": {
    "properties": {
      "embedding": {
        "type": "knn_vector",
        "dimension": 1536,
        "method": {
          "name": "hnsw",
          "space_type": "cosinesimil",
          "engine": "faiss",
          "parameters": {
            "ef_construction": 128,
            "m": 24
          }
        }
      },
      "content": {"type": "text"},
      "metadata": {"type": "object", "enabled": false}
    }
  }
}
```

### Parameters

| Parameter | Description | Recommended |
|---|---|---|
| `dimension` | Vector dimensionality (match embeddings model) | 1536 (Bedrock Titan v2), 768 (Cohere) |
| `ef_construction` | Index build-time quality (higher = more accurate, slower build) | 128-512 |
| `m` | Number of bi-directional links per node | 16-48 |
| `ef_search` | Search-time quality (higher = more accurate, slower) | 50-200 (set at query time) |

### Space types

| Space type | Similarity measure | Use case |
|---|---|---|
| `cosinesimil` | Cosine similarity | Text embeddings (normalized) |
| `l2` | Euclidean distance | Image embeddings |
| `innerproduct` | Dot product | Max inner product search (faiss only) |

### Engine comparison

| Dimension | faiss | nmslib |
|---|---|---|
| Recommendation | Recommended for new collections | Legacy |
| HNSW | Yes | Yes |
| IVF | Yes | No |
| `innerproduct` space | Yes | No |
| Performance | Optimized, actively maintained | Comparable for HNSW |

Use `faiss` for all new VECTORSEARCH collections. Use `nmslib` only if
migrating from managed OpenSearch with an existing nmslib index.

## Semantic search with embeddings

### Architecture

```
User Query
   |
   v
[Application] --text--> [Bedrock Titan Embeddings] --vector--> [OpenSearch k-NN]
                                                                    |
                                                                    v
                                                          [Top-k results]
```

At ingest time, the application calls the embeddings model to convert text
to vectors, then indexes them in OpenSearch. At query time, the same model
converts the query text to a vector for k-NN search.

### ML Commons connector (Bedrock)

Register an ML connector to Bedrock Titan Embeddings:

```json
{
  "name": "bedrock-titan-embeddings",
  "description": "Connector for Amazon Bedrock Titan Text Embeddings v2",
  "version": "1",
  "protocol": "aws_sigv4",
  "parameters": {
    "region": "us-east-1",
    "service_name": "bedrock"
  },
  "credential": {
    "access_key": "",
    "secret_key": "",
    "session_token": ""
  },
  "actions": [
    {
      "action_type": "predict",
      "method": "POST",
      "url": "https://bedrock-runtime.us-east-1.amazonaws.com/model/amazon.titan-embed-text-v2:0/invoke",
      "request_body": "{\"inputText\": \"${parameters.input}\"}",
      "pre_process_function": "...",
      "post_process_function": "..."
    }
  ]
}
```

The connector role MUST have `bedrock:InvokeModel` on the model ARN.

### Neural search pipeline

After registering the connector, create a search pipeline that calls the
model at query time:

```json
{
  "description": "Neural search pipeline",
  "request_processors": [
    {
      "neural_query": {
        "tag": "neural-query",
        "description": "Convert query text to vector",
        "model_id": "<model-id-from-connector>",
        "vector_field": "embedding",
        "text_field": "content",
        "k": 10
      }
    }
  ]
}
```

### Bedrock Titan Embeddings models

| Model | Dimension | Max input tokens | Notes |
|---|---|---|---|
| `amazon.titan-embed-text-v2:0` | 1536 (default), 512, 256, 1024 | 8192 | Recommended; supports dimension truncation |
| `amazon.titan-embed-text-v1` | 1536 | 8192 | Legacy v1 |

Always match the `dimension` in the OpenSearch index mapping to the
embeddings model's output dimension.

## Flow frameworks

Flow frameworks (2024-2025) automate ML model provisioning through JSON
templates. They define a directed acyclic graph (DAG) of steps for:

1. **Connector creation:** register a Bedrock/SageMaker connector.
2. **Model registration:** register the model with ML Commons.
3. **Model deployment:** deploy the model to the ML task nodes.
4. **Pipeline creation:** create ingest/search pipelines that use the model.

### Template structure

```json
{
  "name": "semantic-search-setup",
  "description": "Provision Bedrock embeddings connector for semantic search",
  "workflows": {
    "provision": {
      "nodes": [
        {"id": "create-connector", "type": "create_connector", "inputs": {...}},
        {"id": "register-model", "type": "register_model", "inputs": {"model_group_id": "${create-connector.model_group_id}"}},
        {"id": "deploy-model", "type": "deploy_model", "inputs": {"model_id": "${register-model.model_id}}"}
      ],
      "edges": [
        {"source": "create-connector", "dest": "register-model"},
        {"source": "register-model", "dest": "deploy-model"}
      ]
    }
  }
}
```

### Submitting a flow framework

```bash
curl -X POST "https://<collection-endpoint>/_plugins/_flow_frameworks/workflow" \
  -H "Content-Type: application/json" \
  -d @flow-template.json
```

Flow frameworks are useful for repeatable ML pipeline setup across
environments (dev, staging, prod). The template can be version-controlled
and re-applied.

## Hybrid search (vector + lexical)

Hybrid search combines k-NN vector scores with BM25 lexical scores for
improved relevance. Requires a normalization processor in the search
pipeline:

```json
{
  "request_processors": [
    {"neural_query": {"model_id": "<id>", "vector_field": "embedding", "text_field": "content", "k": 50}}
  ],
  "response_processors": [
    {
      "normalization-processor": {
        "normalization": {"technique": "min_max"},
        "combination": {"technique": "arithmetic_mean", "parameters": {"weights": [0.5, 0.5]}}
      }
    }
  ]
}
```

Weights control the balance between vector and lexical relevance. A 0.7/0.3
split favors semantic relevance; 0.3/0.7 favors exact keyword matches.

## Lifecycle for VECTORSEARCH

VECTORSEARCH collections do not require a lifecycle policy, but for
collections with unbounded vector growth, a size-based lifecycle is
recommended:

```json
{
  "Rules": [{
    "ResourceType": "index",
    "Resource": {"index": "prod-vectors-*"},
    "MaxSize": "500gb"
  }]
}
```

When an index exceeds `MaxSize`, the oldest documents are deleted (FIFO)
to stay within the limit. This prevents storage cost growth and search
latency degradation.
