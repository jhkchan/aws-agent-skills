# Error Handling — SNS Delivery Troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Remediation guidance — per-layer fix commands

### HTTP_SUBSCRIPTION_CONFIRMATION

```bash
aws sns subscribe --topic-arn <topic> --protocol https \
  --notification-endpoint <endpoint> --return-subscription-arn --profile <p>
aws sns confirm-subscription --topic-arn <topic> --token <token> \
  --authenticate-on-unsubscribe true --profile <p>
```

### HTTP_4XX_5XX_RETRY

Address the endpoint-side issue (scale, refresh auth, raise rate
limit). Adjust the subscription delivery policy for more retries:

```bash
aws sns set-subscription-attributes --subscription-arn <sub-arn> \
  --attribute-name DeliveryPolicy \
  --attribute-value '{"healthyRetryPolicy":{"numRetries":5,"minDelayTarget":1,"maxDelayTarget":60}}' \
  --profile <p>
```

### HTTP_SIGNATURE_VERIFICATION

No SNS-side fix. Update the endpoint's validation code to fetch the
cert from `SigningCertURL` and verify per the AWS SNS message spec.

### LAMBDA_ASYNC_INVOCATION

```bash
aws lambda add-permission --function-name <fn> \
  --statement-id AllowSNSInvoke \
  --action lambda:InvokeFunction \
  --principal sns.amazonaws.com \
  --source-arn <topic-arn> --profile <p>
```

### LAMBDA_DLQ

```bash
aws lambda put-function-event-invoke-config --function-name <fn> \
  --destination-config '{"OnFailure":{"Destination":"<sns-or-sqs-arn>"}}' \
  --profile <p>
```
Route to `lambda-invocation-troubleshooter` if the handler is throwing.

### SQS_MESSAGE_SIZE / SQS_REDRIVE

```bash
# Remove envelope overhead
aws sns set-subscription-attributes --subscription-arn <sub-arn> \
  --attribute-name RawMessageDelivery --attribute-value true --profile <p>
```
For SQS_REDRIVE: inspect the source queue's RedrivePolicy; adjust
`maxReceiveCount` or fix the consumer so messages don't exhaust
retries.

### EMAIL_BOUNCE_COMPLAINT

Remove the bounced address from the subscription; implement SES
bounce/complaint handling via a separate SNS topic.

### PLATFORM_ENDPOINT_DISABLED

```bash
aws sns create-platform-endpoint --platform-application-arn <app-arn> \
  --token <device-token> --profile <p>
aws sns delete-endpoint --endpoint-arn <old-endpoint-arn> --profile <p>
```

### FILTER_POLICY_MISMATCH / MESSAGE_ATTRIBUTE_LOSS

```bash
aws sns set-subscription-attributes --subscription-arn <sub-arn> \
  --attribute-name FilterPolicy \
  --attribute-value '<corrected-json>' --profile <p>
```
Verify the corrected policy against the publisher's actual message
attributes. Use `prefix`, `anything-but`, `exists` for flexible
matching. For MESSAGE_ATTRIBUTE_LOSS: set `RawMessageDelivery: false`
to propagate attributes, OR parse from the body in the consumer.

### FIFO_ORDERING / CROSS_REGION_DELIVERY / DLQ_MISSING

- FIFO_ORDERING: use a `.fifo` queue; ensure publisher assigns
  `MessageGroupId` correctly.
- CROSS_REGION_DELIVERY: `aws lambda add-permission --function-name <fn>
  --principal sns.amazonaws.com --source-arn <topic-arn> ...`.
- DLQ_MISSING: configure SNS subscription DLQ via
  `set-subscription-attributes RedrivePolicy`, OR Lambda OnFailure
  destinations for Lambda subscriptions.
