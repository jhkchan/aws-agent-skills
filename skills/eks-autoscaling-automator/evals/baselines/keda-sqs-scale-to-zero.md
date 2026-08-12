# Baseline (no-skill) response: keda-sqs-scale-to-zero

This file captures what a generic assistant produces WITHOUT the
eks-autoscaling-automator skill loaded.

---

For scaling your SQS consumer based on queue depth, KEDA is a great
choice. It can scale your deployment up when there are messages in
the queue and scale it down to zero when the queue is empty.

Install KEDA:

```
helm install keda kedacore/keda --namespace keda-system --create-namespace
```

Then create a ScaledObject that watches your SQS queue:

```
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: sqs-scaler
spec:
  scaleTargetRef:
    name: sqs-batch-processor
  minReplicaCount: 0
  maxReplicaCount: 30
  triggers:
    - type: aws-sqs-queue
      metadata:
        queueURL: https://sqs.us-east-1.amazonaws.com/111111111111/batch-jobs
        queueLength: "10"
        awsRegion: us-east-1
```

Make sure KEDA has permission to read the SQS queue. You'll need to
set up an IAM role and associate it with the KEDA service account.
