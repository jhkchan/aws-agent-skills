# Eval prompt: org-trail-shadowing

Diagnose the CloudTrail missing-events incident for the following
org/member trail topology. Walk the symptom-driven diagnostic tree
and emit the standard diagnostic block (TARGET, VERDICT, ROOT_CAUSE,
LAYER, EVIDENCE, REMEDIATION).

Symptom: an organization trail exists from the management account.
A member account also created its own trail. Events appear to be
duplicated and some are missing from the member's S3 bucket. The
operator needs to determine which trail is active and where events
are landing.

```text
Management account: 111111111111
Member account: 222222222222
OrgID: o-abc123def4

In the member account (222222222222):
describe-trails output:
  [
    { "Name": "prod-org-trail",
      "S3BucketName": "org-cloudtrail-logs",
      "IsOrganizationTrail": true,
      "IsMultiRegionTrail": true },
    { "Name": "member-trail",
      "S3BucketName": "member-cloudtrail-logs",
      "IsOrganizationTrail": false }
  ]

get-trail-status --name member-trail (in member):
  isLogging: true
  latestDeliveryTime: null
  (null — the trail has not delivered since the org trail was
  created.)

In the management account:
get-trail-status --name prod-org-trail:
  isLogging: true
  latestDeliveryTime: 2026-08-11T19:30:14Z
```

The org trail shadows the member trail. Events route to the org
bucket, not the member bucket. The input provided does NOT include
confirmation of whether the org trail's bucket policy covers the
org ID, or whether the member trail was explicitly re-started after
the org trail was created. Without this confirmation the diagnosis
cannot positively confirm the root cause.
