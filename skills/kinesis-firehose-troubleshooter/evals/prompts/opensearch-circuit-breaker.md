# Eval prompt: opensearch-circuit-breaker

Diagnose the following Firehose to OpenSearch delivery failure. Emit
the standard DIAGNOSIS block.

Diagnosis reference: opensearch-circuit-breaker
Account: 111111111111
Region: us-east-1
Delivery-stream-name: prod-events-to-opensearch
Destination: opensearch
Domain: prod-events-search
Symptom: OpenSearchFails

Recent diagnostic output:
- DeliveryToOpenSearch.Success: 0% for the last 45 min
- Firehose log: circuit breaker engaged after 5 minutes of
  sustained 429 responses
- aws opensearch describe-domain-health:
  ClusterHealth=Red
- 2/5 data nodes show free_storage_below_watermark
- OpenSearch access policy includes the Firehose role with
  es:ESHttpPost (auth OK)
- IAM and KMS layers pass

Emit the standard DIAGNOSIS block.
