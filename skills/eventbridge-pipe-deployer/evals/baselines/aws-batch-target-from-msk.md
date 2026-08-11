# Baseline (no-skill) response: aws-batch-target-from-msk

This file captures what a generic assistant produces WITHOUT the
eventbridge-pipe-deployer skill loaded — contrast proves the skill
adds structure around MSK source parameters (consumer group, SCRAM
auth secret association), AWS Batch target with job definition, and
the dual iam:PassRole requirement on the Batch job role.

---

Here's a plan for your MSK to Batch pipe.

The pipe will:
- Read from your MSK cluster's orders-events topic
- Batch records into 60s windows
- Submit a Batch job for each batch

Steps:

1. Create the pipe with MSK source and Batch target.
2. Start the pipe.

Commands:

```
aws pipes create-pipe --name prod-batch-pipeline \
  --source <msk-cluster-arn> \
  --target <batch-queue-arn>
aws pipes start-pipe --name prod-batch-pipeline
```

Make sure your pipe role can read from MSK and submit Batch jobs.
You may need to configure Kafka authentication. Let me know if you
need help with the SCRAM setup.
