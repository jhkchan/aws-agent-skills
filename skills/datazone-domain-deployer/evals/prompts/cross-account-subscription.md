# Eval: cross-account-subscription

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — cross-account subscription with data in account 222222222222, DataZone domain in 111111111111, consumer project in 333333333333

## Prompt

Create a DataZone domain called shared-analytics in us-east-1,
account 111111111111. Project data-marketplace in account
111111111111. S3 data source shared-data-lake in account
222222222222. Consumer project bi-reporting in account
333333333333 needs to subscribe to assets from data-marketplace.
The subscription workflow should use request-approve with the
project owner as approver. IAM roles: DataZoneS3AccessRole in
222222222222, DataZoneConsumerRole in 333333333333. Tags:
Environment=production.
