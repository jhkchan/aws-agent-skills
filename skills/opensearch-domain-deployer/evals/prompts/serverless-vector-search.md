# Eval: serverless-vector-search

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — OpenSearch Serverless VECTORSEARCH collection; VPC-only; customer CMK; IAM Identity Center auth

## Prompt

Provision an OpenSearch Serverless vector search collection named
"prod-vectors" in us-east-1 for RAG / generative AI similarity search.
Vector dimensions: 1536 (OpenAI ada-002). About 10M vectors. VPC-only
access via VPC endpoint vpce-0aaa. Customer CMK alias/vector-kms. IAM
Identity Center for auth. Tags: Environment=production,
Workload=vector-search. Account ID: 123456789012.
