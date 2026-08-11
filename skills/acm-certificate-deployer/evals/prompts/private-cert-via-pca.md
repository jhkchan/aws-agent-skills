# Eval: private-cert-via-pca

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — private certificate via Private CA, internal mTLS use case, NOT browser-trusted

## Prompt

Request a private ACM certificate for internal.api.example.com
via our AWS Private CA
arn:aws:acm-pca:us-east-1:123456789012:certificate-authority/abc-123.
This is for internal mTLS between microservices. DNS validation.
Region us-east-1. Tags: Environment=internal, UseCase=mTLS.
Account ID: 123456789012.
