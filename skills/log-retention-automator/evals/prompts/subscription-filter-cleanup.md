# Eval prompt: subscription-filter-cleanup

Design a retention change for a log group with active subscription
and metric filters. Emit the standard RETENTION block (POLICY,
TRIGGER, ARCHIVAL, VERDICT, TEMPLATE).

Design reference: subscription-filter-cleanup
Account: 111111111111
Region: us-east-1

Log group: /aws/lambda/legacy-processor
Current retention: Never Expire (800 GB stored).
Has: 1 subscription filter (to OpenSearch), 2 metric filters
(powering CloudWatch alarms for Error and Duration).
Desired: set retention to 7 days, keep metric filters alive.
Compliance: export 30-day window to S3 before shortening.

Emit the standard RETENTION block. Address the subscription filter
cleanup sequence, metric filter preservation, and the S3 export
requirement before retention shortening.
