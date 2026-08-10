# Baseline (no-skill) response: input-transformer-lambda-deploy

This file captures what a generic assistant produces WITHOUT the
eventbridge-rule-deployer skill loaded — note the absence of the
InputTransformer wiring, the InputPathsMap / InputTemplate
distinction, and the pre-flight checks that the skill adds.

---

To trigger a Lambda on S3 object-created events, create an
EventBridge rule on the default bus matching `aws.s3` source with
`Object Created` detail-type, filtered on the bucket and prefix.
Then add the Lambda as a target.

```
aws events put-rule --name s3-upload --event-pattern '{"source":["aws.s3"],"detail-type":["Object Created"],"detail":{"bucket":{"name":["my-uploads-bucket"]},"object":{"key":[{"prefix":"uploads/"}]}}}'
aws events put-targets --rule s3-upload --targets '[{"Arn":"<lambda-arn>","Id":"process"}]'
```

The Lambda will receive the full event envelope. If you want a
simplified payload, you can configure an input transformer.
