# Error Handling — CloudTrail Alert Automation

Load-on-demand error tables and remedies for the CloudTrail Alert Automator skill.

## Common EventBridge pattern errors (Step 1)

Common pattern errors:

| Error | Cause | Fix |
|---|---|---|
| Rule never fires | `detail-type` or `source` mismatch | Verify via CloudTrail event JSON |
| Fires on wrong events | Overly broad `eventName` (e.g., `Create*`) | List events explicitly |
| Misses regional events | Rule in one region only | Deploy to all active regions |
| Fires on read-only events | No `readOnly` filter | Add `"readOnly": [false]` |

## Slack webhook rate-limit mitigation (Step 5)

**Rate-limit mitigation:** SNS → SQS → Lambda consumer. SQS buffers
bursts; Lambda processes at 1 msg/second per webhook URL.
