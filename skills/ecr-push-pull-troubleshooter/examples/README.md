# Example usage: ecr-push-pull-troubleshooter

A walkthrough showing the skill diagnosing a cross-account ECR pull
failure that mimics a missing image, demonstrating the symptom-to-layer
triage, the IAM-vs-repository-policy decision (cross-account needs
BOTH sides), the evidence-backed ROOT_CAUSE_IDENTIFIED verdict, and the
resource-policy remediation.

## Input (user prompt)

> Our ECS task in account 222222222222 started failing this morning
> with `CannotPullContainerError`. The task pulls an image from ECR
> in account 111111111111. We've confirmed the image exists and the
> task role has `ecr:BatchGetImage` — help us find why the pull is
> still denied.

```text
Registry: 111111111111.dkr.ecr.us-east-1.amazonaws.com
Repository: cross-account-repo-policy-missing
Tag: 1.0
Image source account: 111111111111
Caller (ECS task execution role) account: 222222222222
Caller IAM role: arn:aws:iam::222222222222:role/ecs-task-exec

aws iam simulate-principal-policy for ecs-task-exec:
  ecr:BatchGetImage on the repository ARN: ALLOWED
  ecr:GetDownloadUrlForLayer on the repository ARN: ALLOWED
  ecr:GetAuthorizationToken on *: ALLOWED

aws ecr get-repository-policy:
  Statement principal: arn:aws:iam::111111111111:root
  (only the source account is listed)

aws ecr describe-images:
  Tag 1.0 exists, 450 MB compressed, pushed 2 hours ago
```

## Skill output

```text
TARGET: 111111111111.dkr.ecr.us-east-1.amazonaws.com/cross-account-repo-policy-missing:1.0
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: Cross-account pull requires BOTH the caller's IAM identity-based
  policy AND the target repository's resource-based policy to allow the
  action. The caller's IAM simulation returns ALLOWED for ecr:BatchGetImage
  and ecr:GetDownloadUrlForLayer (Step 4 PASS), but the repository
  resource-based policy lists only account 111111111111 as principal —
  account 222222222222 is NOT in any statement (Step 5 FAIL).
LAYER: POLICY_REPOSITORY
EVIDENCE:
  - Symptom: ECS task in account 222222222222 fails with
    CannotPullContainerError on an image in account 111111111111.
  - Probe: aws iam simulate-principal-policy for
    arn:aws:iam::222222222222:role/ecs-task-exec returns ALLOWED for
    ecr:BatchGetImage and ecr:GetDownloadUrlForLayer on the repository
    ARN — the IAM side is satisfied.
  - Probe: aws ecr get-repository-policy returns a policy whose only
    statement principal is arn:aws:iam::111111111111:root — account
    222222222222 is not listed. Cross-account access requires the
    caller's account in the repository policy.
  - Probe: aws ecr describe-images confirms tag 1.0 exists (450 MB
    compressed, pushed 2 hours ago) — the image is present, the
    failure is authorisation, not missing image.
  - Passing: auth token freshly issued (not AUTH_TOKEN_EXPIRED);
    repository is AES256-encrypted (not KMS_ACCESS_DENIED).
REMEDIATION:
  1. Add a statement to the repository policy granting account
     222222222222 the pull actions:
     aws ecr set-repository-policy \
       --repository-name cross-account-repo-policy-missing \
       --region us-east-1 \
       --policy-text '{
         "Version": "2012-10-17",
         "Statement": [
           {existing statement preserved},
           {
             "Sid": "CrossAccountPull222222",
             "Effect": "Allow",
             "Principal": {"AWS": "arn:aws:iam::222222222222:root"},
             "Action": ["ecr:BatchGetImage",
                        "ecr:GetDownloadUrlForLayer",
                        "ecr:BatchCheckLayerAvailability"]
           }
         ]
       }' --profile 111111-profile
  2. Preserve the existing statement — set-repository-policy replaces
     the entire policy, not appends.
  3. Verify by re-running the ECS task; it should pull successfully.
CONFIRM: Before changing the repository policy, emit and await:
  "CONFIRM: About to add a cross-account pull statement for account
   222222222222 to repository cross-account-repo-policy-missing.
   Proceed? (yes/no)"
  Do NOT run the CLI until the operator replies yes.
```

## What the skill caught that a generic assistant misses

1. **Distinguished cross-account from same-account.** A generic
   assistant says "add `ecr:BatchGetImage` to the IAM role." The IAM
   role already has it — the simulation proves it. The skill recognises
   that cross-account requires BOTH the IAM side AND the resource-based
   policy side, and the repository policy is the missing side.

2. **Used `simulate-principal-policy` before recommending.** The skill
   verifies the IAM side is satisfied before declaring the repository
   policy the root cause. This avoids the common misdiagnosis of
   "must be IAM" when the IAM is actually fine.

3. **Confirmed the image exists.** `describe-images` confirms the image
   is present — the failure is authorisation, not a missing-image or
   lifecycle-deletion issue. A generic assistant may recommend
   re-pushing the image.

4. **Preserved the existing repository policy statement.** The skill
   explicitly warns that `set-repository-policy` replaces, not appends
   — the existing same-account statement must be preserved. A generic
   assistant may overwrite the policy and break same-account access.

5. **Surfaced the CONFIRM gate.** Changing a resource-based policy can
   leak the repository to unintended principals; the skill requires
   operator confirmation before applying.

## Slash-command invocation

```
/aws:troubleshoot-ecr-push-pull
```

Or via the orchestrator:

```
/aws:pipeline
You: "diagnose why the ECS task cannot pull from cross-account ECR"
```

The orchestrator emits
`[Phase: Troubleshoot | Skills routed: ecr-push-pull-troubleshooter]`
and hands off to this skill for the diagnostic block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the cross-account pull:

```bash
# Confirm the repository policy now lists the caller account
aws ecr get-repository-policy \
  --repository-name cross-account-repo-policy-missing \
  --region us-east-1 --profile 111111-profile

# Confirm the ECS task can retrieve an auth token and pull
aws sts assume-role \
  --role-arn arn:aws:iam::222222222222:role/ecs-task-exec \
  --role-session-name pull-test --duration-seconds 900

# Re-run the task
aws ecs run-task --cluster prod --task-definition <td> \
  --region us-east-1 --profile 222222-profile
```

Then monitor the task's `Running` state and CloudWatch `PullSuccessful`
metric for 5-10 minutes to confirm sustained success.
