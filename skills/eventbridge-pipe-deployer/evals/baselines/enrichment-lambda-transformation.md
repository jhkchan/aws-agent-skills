# Baseline (no-skill) response: enrichment-lambda-transformation

This file captures what a generic assistant produces WITHOUT the
eventbridge-pipe-deployer skill loaded — contrast proves the skill
adds structure around the enrichment stage, dual IAM grants
(enrichment + target), and batched-payload semantics.

---

Here's a plan for your pipe with the enrichment Lambda.

The pipe will:
- Read from DynamoDB Streams
- Filter to CONFIRMED orders
- Send each batch through the orders-enrich Lambda (joins customer data)
- Pass the transformed payload to the OrderWorkflow state machine

Steps:

1. Create the pipe with source, filter, enrichment, and target.
2. Start the pipe.

Commands:

```
aws pipes create-pipe --name prod-orders-enriched \
  --source <stream-arn> \
  --enrichment <enrich-lambda-arn> \
  --target <state-machine-arn>
aws pipes start-pipe --name prod-orders-enriched
```

Make sure your pipe role has permission to invoke both the
enrichment Lambda and the Step Functions state machine. Let me know
if you need help with the IAM policy.
