# Eval prompt: org-trail-member-shadow-stopped

Diagnose the following CloudTrail gap. Walk the ORG_TRAIL_GAP
diagnostic tree and emit the standard VERDICT block (INCIDENT, VERDICT,
ROOT_CAUSE, EVIDENCE, ROOT_CAUSE_CATALOG, REMEDIATION).

## Scenario

An AWS Organizations trail (`corp-org-trail`) logs management account
events and 9 of 10 member accounts. Member account `222222222222` has
no events in the org trail's S3 bucket for the past day. The
management account is `111111111111`.

## Known facts

- In the management account (`111111111111`):
  - `aws cloudtrail describe-trails --query
    'trailList[?IsOrganizationTrail]'` returns:
    - `Name: corp-org-trail`
    - `IsOrganizationTrail: true`
    - `IsMultiRegionTrail: true`
    - `IsLogging: true`
    - `S3BucketName: org-trail-logs`
  - `aws cloudtrail get-trail-status --name corp-org-trail` returns
    `IsLogging: true`, `LatestDeliveryTime` recent.
- `aws organizations list-accounts --query
  'Accounts[?Id==`222222222222`]'` returns:
  - `Id: 222222222222`
  - `Status: ACTIVE`
  - `Name: member-2`
- `aws organizations list-delegated-administrators
  --service-principal cloudtrail.amazonaws.com` returns an empty list
  (no delegated admin configured; the trail is owned by the
  management account).
- Using member-account credentials for `222222222222`:
  - `aws cloudtrail describe-trails --show-shadow-trails --query
    'trailList[*].{name:Name,shadow:IsShadowTrail,logging:IsLogging,
    isOrg:IsOrganizationTrail}'` returns:
    ```
    [{name: corp-org-trail, shadow: true, logging: false,
      isOrg: true}]
    ```
  - The shadow trail is `IsLogging: false` in this member.
- CloudTrail event history in the member account shows a
  `StopLogging` event at yesterday 14:00 UTC from an automation
  role `AutomationRole`.

## Symptom

Org trail is healthy in the management account, but member account
`222222222222` events are missing. The shadow trail is stopped in
the member account.
