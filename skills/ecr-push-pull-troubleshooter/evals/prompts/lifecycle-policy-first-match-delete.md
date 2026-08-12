# Eval prompt: lifecycle-policy-first-match-delete

Diagnose the ECR pull failure for the following repository. Walk the
symptom-driven diagnostic tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: `docker pull` returns `manifest unknown` for tag `v3` of
`lifecycle-policy-first-match-delete` since 03:17 UTC. The tag was
present and serving production traffic yesterday; no engineer
manually deleted it.

```text
Registry: 111111111111.dkr.ecr.us-east-1.amazonaws.com
Repository: lifecycle-policy-first-match-delete
Tag: v3 (production release, pushed 2 days ago)

aws ecr describe-images:
  v1: pushed 4 days ago, present
  v2: pushed 3 days ago, present
  v3: NOT LISTED (gone since 03:17 UTC)
  v4: pushed 1 hour ago, present
  v5: pushed 30 minutes ago, present

aws ecr get-lifecycle-policy (ruleText):
  {
    "rules": [
      {
        "rulePriority": 1,
        "selection": {"tagStatus": "any", "countType": "imageCountMoreThan", "countNumber": 3},
        "action": {"type": "expire"}
      },
      {
        "rulePriority": 2,
        "selection": {"tagStatus": "tagged", "countType": "imageCountMoreThan", "countNumber": 10, "tagPrefixList": ["prod-"]},
        "action": {"type": "expire"}
      }
    ]
  }

aws cloudtrail lookup-events for BatchDeleteImage 03:00-04:00 UTC:
  ECR service principal deleted digest sha256:abc123 from
  lifecycle-policy-first-match-delete; requestParameters included
  imageTag=v3.

Repository policy: (none — same-account only)
Manual DeleteImage events from any user: (none)
```

Lifecycle policy rules evaluate in order, top to bottom; the FIRST
matching rule wins and no further rule is evaluated for that image.
Rule priority 1 (`tagStatus: any, count: 3`) matches before rule
priority 2 (the `prod-` protection rule), so the 4th-newest image is
deleted regardless of the lower-priority `keep`-intent rule.
