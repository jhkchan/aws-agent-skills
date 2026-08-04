# End-to-end usage scenario: ecr-repository-auditor

A walkthrough showing the skill auditing an ECR repository that has both a
public pull grant (PUBLIC) and scanOnPush disabled with unscanned images
(NO_SCAN), demonstrating severity aggregation, the supply-chain exposure
concept, and the assume-breach remediation workflow.

## Input (user prompt)

> Review this ECR repository before we use it for production container
> deployments. The repo serves images to ECS Fargate tasks.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "RootAccess",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::111111111111:root"},
      "Action": "ecr:*",
      "Resource": "*"
    },
    {
      "Sid": "PartnerPull",
      "Effect": "Allow",
      "Principal": "*",
      "Action": [
        "ecr:BatchGetImage",
        "ecr:GetDownloadUrlForLayer"
      ],
      "Resource": "*"
    }
  ]
}
```

Repository metadata:
- imageScanningConfiguration.scanOnPush: false
- imageTagMutability: MUTABLE
- lifecyclePolicyText: absent
- Images:
  - sha256:abc, tags: ["latest"], imageScanStatus: null
  - sha256:def, tags: ["v1.0"], imageScanStatus: null

## Skill output

```text
REPO: 111111111111.dkr.ecr.us-east-1.amazonaws.com/app-backend
VERDICT: PUBLIC
REASON: Statement "PartnerPull" grants ecr:BatchGetImage and
ecr:GetDownloadUrlForLayer to Principal "*" with no restrictive condition —
any AWS account holder can pull every image layer, exposing application
code, dependencies, and any secrets baked into the image (Step 1b). Multiple
compounding findings: scanOnPush disabled with unscanned images, no lifecycle
policy, and mutable tags.
FINDINGS:
  - [PUBLIC] Principal "*" + PULL actions (BatchGetImage, GetDownloadUrlForLayer)
    with no condition (Step 1b) — total image-layer exposure to the internet
  - [NO_SCAN] scanOnPush: false + 2 images with imageScanStatus: null (Step 2) —
    images entering the registry without vulnerability scanning
  - [NO_LIFECYCLE] No lifecyclePolicyText present (Step 3) — images accumulate
    indefinitely, cost grows unbounded
  - [CONFIG_GAP] imageTagMutability: MUTABLE (Step 4) — supply-chain tag
    overwrite risk
REMEDIATION:
  1. PUBLIC — Remove the "PartnerPull" statement immediately. If public pull
     is genuinely required, replace Principal "*" with specific account/role
     ARNs AND add aws:SourceAccount or aws:SourceVpce conditions.
  2. PUBLIC — Assume breach. Audit CloudTrail for ecr:BatchGetImage and
     ecr:GetDownloadUrlForLayer events from external principals during the
     exposure window. Any pulled image should be considered inspected for
     embedded secrets — rotate secrets found in image layers.
  3. NO_SCAN — Enable scan-on-push:
     aws ecr put-image-scanning-configuration --repository-name app-backend
     --registry-id 111111111111 --image-scanning-configuration scanOnPush=true
     Then manually scan existing images:
     aws ecr start-image-scan --repository-name app-backend --image-id imageDigest=sha256:abc
  4. NO_LIFECYCLE — Apply a lifecycle policy (dry-run with
     get-lifecycle-policy-preview first):
     aws ecr put-lifecycle-policy --repository-name app-backend
     --lifecycle-policy-text file://lifecycle.json
  5. CONFIG_GAP — Set tag immutability:
     aws ecr put-image-tag-mutability --repository-name app-backend
     --image-tag-mutability IMMUTABLE --registry-id 111111111111
```

## What the skill caught that a generic assistant misses

1. **The image-layer exposure multiplier.** A generic assistant says "public
   access is risky." The skill explains that `ecr:BatchGetImage` +
   `ecr:GetDownloadUrlForLayer` grants access to EVERY image layer —
   equivalent to reading all source code, embedded secrets, environment
   variables baked into the image, and dependency versions. One grant, total
   image content exposure.

2. **The empty vs permissive policy distinction.** The skill recognises that
   an ECR repo with no repositoryPolicy (the default) is the SECURE posture
   — access is governed by IAM. It does not flag the absence of a policy as
   a gap.

3. **Per-image scan status vs repo-level config.** A generic assistant checks
   `scanOnPush` and says "it's off." The skill enumerates per-image
   `imageScanStatus` to identify which specific images have never been
   scanned, and distinguishes `null` (never scanned) from `PENDING` and
   `COMPLETE`.

4. **Severity aggregation with per-finding breakdown.** The verdict is PUBLIC
   (worst finding), but the FINDINGS list shows all four dimensions: PUBLIC,
   NO_SCAN, NO_LIFECYCLE, and CONFIG_GAP. The operator can triage each
   independently.

5. **The assume-breach remediation workflow.** Generic advice says "remove
   the access." The skill's remediation includes auditing CloudTrail for pull
   events during the exposure window and rotating secrets found in image
   layers — because the images may have already been pulled and inspected.

## Slash-command invocation

```
/aws:audit-ecr-repository
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit this ECR repository before we use it for production"
```

The orchestrator emits
`[Phase: Audit | Skills routed: ecr-repository-auditor]` and hands off
to this skill for the VERDICT.

## Live-account follow-up (optional, requires AWS CLI)

After remediating the configuration, validate the repository posture:

```bash
# Verify the public principal was removed
aws ecr get-repository-policy --repository-name app-backend \
  --registry-id 111111111111 --profile default --output json \
  | jq '.PolicyText | fromjson | .Statement[] | .Principal'

# Confirm scan-on-push is enabled
aws ecr describe-repositories --repository-names app-backend \
  --registry-id 111111111111 --profile default \
  | jq '.repositories[0].imageScanningConfiguration'

# Verify lifecycle policy is applied
aws ecr get-lifecycle-policy --repository-name app-backend \
  --registry-id 111111111111 --profile default

# Confirm tag immutability
aws ecr describe-repositories --repository-names app-backend \
  --registry-id 111111111111 --profile default \
  | jq '.repositories[0].imageTagMutability'
```

Then monitor CloudTrail for `ecr:BatchGetImage` events from unexpected
principals for 1-2 weeks.
