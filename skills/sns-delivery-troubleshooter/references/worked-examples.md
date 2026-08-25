# Worked Examples — SNS Delivery Troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

### Worked example — filter policy silent drop

```text
TARGET: arn:aws:sns:us-east-1:111111111111:order-events
  (subscription: arn:aws:sns:us-east-1:111111111111:order-events:abc)
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: Subscription filter policy {"event": ["order.created"]} drops
  messages with attribute event=order.updated. Filter policies silently
  drop non-matching messages — no error, no DLQ entry (Step 7).
LAYER: FILTER_POLICY_MISMATCH
EVIDENCE:
  - Symptom: consumer reports ~40% of expected messages never arrive.
    No errors in SNS delivery metrics.
  - Probe: aws sns get-subscription-attributes returns FilterPolicy:
    {"event": ["order.created"]}.
  - Probe: NumberOfNotificationsDelivered for this subscription is
    ~60% of Published — the drop ratio matches the order.created vs
    order.updated split. Test publish with event=order.updated does
    NOT increment Delivered; event=order.created does.
  - Passing: ConfirmationStatus is Confirmed; Lambda resource policy
    grants sns.amazonaws.com lambda:InvokeFunction.
REMEDIATION:
  1. Update the filter policy to include order.updated:
     aws sns set-subscription-attributes \
       --subscription-arn <sub-arn> \
       --attribute-name FilterPolicy \
       --attribute-value '{"event": ["order.created", "order.updated"]}' \
       --profile <p>
  2. Verify by publishing event=order.updated and confirming
     NumberOfNotificationsDelivered increments.
CONFIRM: Before updating the filter policy, emit and await:
  "CONFIRM: About to add order.updated to the filter policy on
   subscription <sub-arn>. Proceed? (yes/no)"
```
