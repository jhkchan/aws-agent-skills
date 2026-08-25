# ECR Push/Pull Troubleshooter — worked examples (moved from SKILL.md

Loaded on demand — content moved verbatim from SKILL.md (progressive disclosure; nothing deleted).
## INSUFFICIENT_DATA re-prompt template (moved from SKILL.md)

```text
TARGET: <registry-uri/repo:tag or unknown>
VERDICT: INSUFFICIENT_DATA
REASON: Input is missing required context — at minimum a symptom
  description (the docker / aws ecr error string) and the full
  registry URI (account, region, repository name).
LAYER: UNKNOWN
EVIDENCE:
  - Missing: <list specific missing fields>
REMEDIATION: Re-prompt the operator for: (1) the exact docker or aws
  ecr error string, (2) the full registry URI being pushed to or
  pulled from, and (3) for cross-account cases, the IAM principal
  doing the operation and its account ID.
```

## Worked example — LIFECYCLE_DELETED (moved from SKILL.md)

```text
TARGET: 111111111111.dkr.ecr.us-east-1.amazonaws.com/payments:v3
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: A lifecycle policy rule "expire when count=3, tagStatus=any"
  evaluated in first-match order and deleted the 4th-newest image,
  which happened to be the production release from 2 days ago.
LAYER: LIFECYCLE_DELETED
EVIDENCE:
  - Symptom: docker pull returns "manifest unknown" for payments:v3
    since 03:17 UTC; describe-images no longer lists v3.
  - Probe: get-lifecycle-policy top rule is {type: expire, selection:
    {count: 3, tagStatus: any}}.
  - Probe: cloudtrail lookup-events for BatchDeleteImage at 03:17 UTC
    shows the ECR service principal deleted digest sha256:abc123.
  - Passing: repository policy empty; no manual-delete CloudTrail event.
REMEDIATION:
  1. Re-push the image OR restore from a backup region's replica.
  2. Reorder the lifecycle policy so "keep last 10 tagged" rules sit
     ABOVE "expire count=3" rules; first matching rule wins.
  3. Add tag-rule protection for the prod-* tag prefix.
```
