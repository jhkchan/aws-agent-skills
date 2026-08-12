# Baseline (no-skill) response: lambda-reserved-concurrency-zero-review-required

This file captures what a generic assistant produces WITHOUT the
ec2-spot-interruption-operator skill loaded.

---

Your interruption pipeline has some issues. The SQS queue is backing up
and the Lambda function has reserved concurrency set to 0, which means
it cannot run. You should fix this:

```bash
aws lambda put-function-concurrency \
  --function-name prod-spot-graceful-shutdown \
  --reserved-concurrent-executions 10
```

Also, your ALB target group deregistration delay is set to 300 seconds,
which is too long for Spot interruptions. Consider reducing it.

Check the SQS queue for stuck messages and process the DLQ.
