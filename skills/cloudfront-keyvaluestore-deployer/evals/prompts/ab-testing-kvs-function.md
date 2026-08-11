# Eval: ab-testing-kvs-function

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — KVS for A/B testing, cloudfront-js-2.0 function, KVS-function linkage, viewer-request event, eventual consistency acknowledged

## Prompt

Create a CloudFront KeyValueStore named ab-testing-kvs for A/B
testing. I need a CloudFront Function named ab-test-router that
reads the KVS to route traffic between variant-a and variant-b
based on a percentage stored in the KVS. The distribution is
E1234567890ABC. I want to change the split without redeploying
the function. Account ID: 123456789012. Tags:
Environment=production, UseCase=ab-testing.
