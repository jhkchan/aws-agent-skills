# Advanced Patterns — cloudtrail-missing-events-troubleshooter

## Mindset

A "CloudTrail is missing events" incident is almost always a
configuration mismatch between what the operator expects the trail
to capture and what the event selectors actually select. The trail
is fine; the *selector scope* is wrong, the *bucket policy* is
blocking delivery, or the *org trail* is shadowing a member trail.
Senior CloudTrail engineers do not start by reading individual log
files — they start with `describe-trails`, `get-trail-status`,
`get-event-selectors`, and `get-bucket-policy`. Only once the trail
configuration is proven correct do they pivot to `lookup-events`
to verify specific events are landing.

Four behaviours separate a senior CloudTrail engineer from a
generalist: (1) management events are default-on but data events
(S3 GetObject, Lambda InvokeFunction, DynamoDB GetItem) are
**opt-in** — a trail with default event selectors captures ZERO
data-plane API calls; data events require an explicit event
selector and are billed at a higher rate; (2) organization trails
**shadow** member trails — when an org trail is created, CloudTrail
creates a read-only shadow trail in every member account, and any
pre-existing member trail STOPS DELIVERING as soon as the shadow
appears (events route to the org bucket); (3) the S3 bucket policy
is the **silent failure mode** — `IsLogging: true` does NOT mean
events are delivering, because CloudTrail retries silently on
bucket-policy rejection, so always cross-reference
`LatestDeliveryTime` against the wall clock; (4) CloudTrail Lake
event data stores have **independent selectors** from S3 trails —
configuring one does not configure the other.

## Step 0: Non-obvious behaviours that change diagnosis

- **`IsLogging: true` does not mean events are delivering.** The
  managed service does not fail the trail on bucket-policy rejection
  — it retries silently. Cross-reference `LatestDeliveryTime` against
  the wall clock. A trail with `IsLogging: true` and
  `LatestDeliveryTime: 6 hours ago` is failing.
- **Organization trails create shadow trails in every member
  account.** The shadow trail appears in `describe-trails` with
  `IsOrganizationTrail: true`; the member cannot modify it. Any
  pre-existing member trail STOPS DELIVERING as soon as the shadow
  appears — events route to the org bucket.
- **Management events are default-on; data events are opt-in.** S3
  GetObject, Lambda InvokeFunction, DynamoDB GetItem require an
  event selector with `DataEvents` explicitly configured.
- **Event selectors have `ReadWriteType: All` by default**, but the
  field can be `ReadOnly` or `WriteOnly`. A trail with `ReadOnly`
  will not capture `CreateBucket`, `PutObject`, `RunInstances`.
- **`IncludeGlobalServiceEvents` controls IAM, STS, and
  CloudFront.** Global services deliver events from us-east-1 only.
  `IncludeGlobalServiceEvents: false` excludes them even on a
  multi-region trail.
- **KMS key disabled blocks log encryption silently.** If the trail
  has `KmsKeyId: <arn>` and `KeyState: Disabled` or
  `PendingDeletion`, CloudTrail cannot encrypt log files and stops
  delivering. `IsLogging` reports `true`; `LatestDeliveryTime` is
  stale.
- **CloudTrail Lake EDS has independent selectors from S3 trails.**
  An operator who "sees events in S3 but not in Lake" has the Lake
  EDS configured with a narrower selector. They are two independent
  ingestion paths.
- **Not all AWS services log in all regions.** Some regional
  services do not emit CloudTrail events in every region where they
  operate. Cross-reference the AWS docs for the service-region
  combination.
- **S3 log file prefix errors are subtle.** The trail's `S3KeyPrefix`
  field controls the prefix. An operator listing
  `s3://bucket/cloudtrail/` when `S3KeyPrefix` is `logs/` will see
  "no logs" even though delivery is healthy.
- **CloudTrail log file validation digests deliver separately.**
  `LatestDigestDeliveryTime` is independent of
  `LatestDeliveryTime`. Stale digest delivery with healthy log
  delivery is a separate issue (usually bucket policy missing
  `s3:PutObject` for the digest prefix).

## IaC pitfall — trail never started after IaC creation (Step 2)

IaC pitfall: CloudFormation `AWS::CloudTrail::Trail` does NOT
automatically start logging on creation. The IaC template must
include the `IsLogging: true` property or invoke `start-logging`
as a custom resource. Terraform's `aws_cloudtrail` resource starts
logging by default but can be stopped by setting
`enable_logging = false`.

## Single-region trail and global service events (Step 6)

If `IsMultiRegionTrail: false`, the trail captures only its home
region. A single-region trail in us-east-1 still captures global
service events (IAM, STS, CloudFront) if
`IncludeGlobalServiceEvents: true`. Convert to multi-region via
`update-trail --name <trail> --is-multi-region-trail`.

## ReadWriteType conversion (Step 7)

If `ReadWriteType: ReadOnly`, write events are excluded. Convert to
`All` via `put-event-selectors`. If `WriteOnly`, read events are
excluded — operators debugging "where did this ListBuckets call come
from" will not find it.

## CloudWatch Logs delivery role and log group checks (Step 8)

`LatestCloudWatchLogsDeliveryTime` is independent of
`LatestDeliveryTime`. If CW Logs delivery lags beyond 15 minutes
while S3 delivery is healthy: verify `CloudWatchLogsRoleArn` on the
trail trusts `cloudtrail.amazonaws.com` and has
`logs:CreateLogStream`, `logs:PutLogEvents`; verify the log group
exists and was not deleted.

## Service-region logging coverage (Step 10)

Not all AWS services emit CloudTrail events in every region. New
services often log in us-east-1 first; some services log only at
the regional endpoint; China regions and GovCloud have separate
event sources. Cross-reference the AWS CloudTrail documentation for
the service-region combination.
