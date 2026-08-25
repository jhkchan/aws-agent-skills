# Worked Examples — Kinesis Data Firehose Troubleshooter

Secondary worked examples (full DIAGNOSIS blocks) moved verbatim from SKILL.md for progressive disclosure. Load on demand.

## Worked example - NEED_MORE_INFO, DeliveryLag (intermittent) (moved from SKILL.md)

```text
DIAGNOSIS: prod-firehose-lag
DELIVERY_STREAM: prod-events-delivery
DESTINATION: s3
SYMPTOM: DeliveryLag
ROOT_CAUSE: Pending diagnosis - DataFreshnessSec spikes at
            irregular intervals. Buffering hints are 64 MB /
            900 sec which is reasonable for the traffic level.
            Need per-stage timing in the Lambda transform to
            identify whether the lag is Lambda-bound or
            destination-bound.
EVIDENCE:
  - get-metric-statistics DeliveryToS3.DataFreshnessSec: spikes to 600-900 sec every ~30 min
  - BufferingHints: SizeInMBs=64, IntervalInSeconds=900
  - DeliveryToS3.Success: 100% (no drops)
  - Lambda Errors metric: 0
LAYER_CHECK:
  - Source: PASS - IncomingBytes steady
  - Transform: PASS (no errors) - but duration distribution unknown
  - Convert: N/A
  - Deliver: PASS - Success 100%
  - Observability: PASS
FIX: (pending root cause)
VERIFICATION: (pending fix)
VERDICT: NEED_MORE_INFO
NEXT_STEP: Enable Lambda Insights and capture per-invocation
  duration distribution:
    aws logs filter-log-events --log-group-name /aws/lambda/<fn> --filter-pattern "REPORT"
  Concurrently, query for KMS throttling:
    aws cloudwatch get-metric-statistics --namespace AWS/KMS --metric-name ThrottledRequests --dimensions Name=KeyId,Value=<key-id> --start-time $(date -u -v-3H +%Y-%m-%dT%H:%M:%S) --end-time $(date -u +%Y-%m-%dT%H:%M:%S) --period 300 --statistics Sum --output table
  If duration spikes correlate with the DataFreshness spikes, the
  Lambda is the bottleneck. If KMS ThrottledRequests spikes, the
  limit is the bottleneck.
ESCALATION_PATH: If timing does not correlate with any single
  metric, escalate to AWS Support with the delivery-stream-name
  and the DataFreshness spike timestamps.
```

## Worked example - ESCALATE, OpenSearchFails (cluster red) (moved from SKILL.md)

```text
DIAGNOSIS: prod-firehose-opensearch
DELIVERY_STREAM: prod-events-to-opensearch
DESTINATION: opensearch
SYMPTOM: OpenSearchFails
ROOT_CAUSE: OpenSearch domain prod-events-search is in RED
            cluster health. Shard allocation is failing because
            two data nodes are out of disk (free storage below
            the watermark). Firehose cannot deliver until the
            cluster returns to GREEN or YELLOW.
EVIDENCE:
  - describe-domain-health: ClusterHealth=Red
  - OpenSearch ClusterStatus shows 2/5 nodes with free_storage_below_watermark
  - DeliveryToOpenSearch.Success: 0% for the last 45 minutes
  - Firehose log: circuit breaker engaged after 5 minutes of sustained 429
LAYER_CHECK:
  - Source: PASS - IncomingBytes steady
  - Transform: N/A
  - Convert: N/A
  - Deliver: FAIL - OpenSearch cluster red, Firehose circuit breaker engaged
  - Observability: PASS
FIX: Cannot remediate from Firehose side alone - the OpenSearch
  cluster needs disk cleanup, node expansion, or index lifecycle
  action. The Firehose circuit breaker will recover automatically
  once OpenSearch returns to sustained success, but the cluster
  state change requires OpenSearch admin action.
VERIFICATION: After OpenSearch returns to GREEN:
  aws opensearch describe-domain-health --domain-name prod-events-search --query 'DomainStatus.ClusterHealth' --output text --profile opensearch-admin
  Expect: Green. Then Firehose circuit breaker will reset within the configured window.
VERDICT: ESCALATE
NEXT_STEP: Provide the OpenSearch admin with this remediation:
  1. Identify oversized indices: GET _cat/indices?v&s=store.size:desc
  2. Delete or snapshot old indices via the Index State Management policy
  3. Add EBS storage or instance count to free disk above the watermark
ESCALATION_PATH: OpenSearch domain administrator must restore
  prod-events-search to GREEN. Firehose will resume automatically
  once the circuit breaker window clears.
```

