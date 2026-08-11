# Example usage: sns-delivery-troubleshooter

A walkthrough showing the skill diagnosing an SNS delivery failure
caused by a PendingConfirmation subscription, demonstrating the
ConfirmationStatus heuristic, the symptom-to-layer triage, the
evidence-backed ROOT_CAUSE_IDENTIFIED verdict, and the subscription-
lifecycle fix.

## Input (user prompt)

> Our partner webhook https://api.partner.com/webhook receives zero
> messages since we created the SNS subscription 2 hours ago. The
> Lambda subscription on the same topic works fine. We've checked the
> partner's firewall and AWS IP ranges — nothing is blocked.

```text
TopicArn: arn:aws:sns:us-east-1:111111111111:orders-events
Protocol: https
Endpoint: https://api.partner.com/webhook
SubscriptionArn: arn:aws:sns:us-east-1:111111111111:orders-events:abc-def
ConfirmationStatus: PendingConfirmation

CloudWatch metrics (last 2 hours):
  - NumberOfNotificationsPublished: 12000 (steady)
  - NumberOfNotificationsDelivered: 0 (for this Endpoint)
  - NumberOfNotificationsFailed: 0 (for this Endpoint)

Other subscriptions on the same topic:
  - Lambda subscription (fn-orders-processor): Confirmed, receiving
    normally (NumberOfNotificationsDelivered matches Published).
```

## Skill output

```text
TARGET: arn:aws:sns:us-east-1:111111111111:orders-events
  (subscription: https://api.partner.com/webhook)
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: Subscription ConfirmationStatus is PendingConfirmation. The
  HTTP endpoint never confirmed the SubscriptionConfirmation token.
  SNS does not deliver messages to unconfirmed HTTP/HTTPS
  subscriptions (Step 2).
LAYER: HTTP_SUBSCRIPTION_CONFIRMATION
EVIDENCE:
  - Symptom: partner reports zero messages received since the
    subscription was created 2 hours ago.
  - Probe: aws sns get-subscription-attributes returns
    ConfirmationStatus: PendingConfirmation.
  - Probe: aws cloudwatch get-metric-statistics on AWS/SNS
    NumberOfNotificationsDelivered for this TopicName + Endpoint
    returns Values: [0, 0, 0, ...].
  - Passing: the topic itself is publishing
    (NumberOfNotificationsPublished is non-zero); the Lambda
    subscription on the same topic is receiving (so the topic is not
    the issue).
REMEDIATION:
  1. Retrieve the SubscriptionConfirmation token from the endpoint's
     access logs (SNS sent a POST with a token when the subscription
     was created), OR re-trigger confirmation by re-subscribing:
     aws sns subscribe --topic-arn <topic> --protocol https \
       --notification-endpoint https://api.partner.com/webhook \
       --return-subscription-arn --profile <p>
  2. The endpoint must call ConfirmSubscription with the token:
     aws sns confirm-subscription --topic-arn <topic> \
       --token <token> --authenticate-on-unsubscribe true \
       --profile <p>
  3. Verify ConfirmationStatus transitions to Confirmed and
     NumberOfNotificationsDelivered increments.
CONFIRM: Before re-subscribing, emit and await:
  "CONFIRM: About to re-subscribe https://api.partner.com/webhook to
   orders-events. Proceed? (yes/no)"
```

## What the skill caught that a generic assistant misses

1. **Checked ConfirmationStatus before assuming network/firewall
   issues.** A generic assistant tells the operator to check firewall
   rules and AWS IP ranges. The skill reads `ConfirmationStatus` and
   identifies that the subscription was never confirmed — the
   endpoint is fine; the subscription lifecycle is the issue.

2. **Used the Lambda subscription as a positive control.** The
   skill's evidence notes that the Lambda subscription on the same
   topic is receiving normally. That rules out the topic itself as
   the failure surface — the topic publishes, the Lambda delivers;
   the HTTP subscription is the only one failing.

3. **Explained the asymmetry between HTTP and Lambda/SQS
   subscriptions.** Lambda and SQS subscriptions auto-confirm; HTTP/
   HTTPS require manual token confirmation. The operator (who created
   the subscription via IaC) did not realise the HTTP endpoint needed
   to call `ConfirmSubscription`.

4. **Recommended the subscription-lifecycle fix, not a network
   investigation.** The remediation is `subscribe` + `confirm-
   subscription`, not a deep-dive into firewall rules or AWS IP
   ranges.

## Slash-command invocation

```
/aws:troubleshoot-sns-delivery
```

Or via the orchestrator:

```
/aws:pipeline
You: "diagnose why SNS orders-events is not delivering to the partner webhook"
```

The orchestrator emits
`[Phase: Troubleshoot | Skills routed: sns-delivery-troubleshooter]`
and hands off to this skill for the diagnostic block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the subscription transitions to Confirmed
and delivery begins:

```bash
# Verify the subscription is now Confirmed
aws sns get-subscription-attributes \
  --subscription-arn arn:aws:sns:us-east-1:111111111111:orders-events:abc-def \
  --query 'Attributes.ConfirmationStatus' --profile default

# Confirm delivery metrics increment
aws cloudwatch get-metric-statistics --namespace AWS/SNS \
  --metric-name NumberOfNotificationsDelivered \
  --dimensions Name=TopicName,Value=orders-events \
  Name=Endpoint,Value=https://api.partner.com/webhook \
  --start-time $(date -d '-30 minutes' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Sum --profile default --output json
```

Then monitor for 1-2 hours to confirm sustained delivery.
