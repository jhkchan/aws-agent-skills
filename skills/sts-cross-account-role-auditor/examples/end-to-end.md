# End-to-end usage scenario: sts-cross-account-role-auditor

A walkthrough showing the skill classifying a multi-statement role trust
policy that contains both a same-account trust (OK) and a confused-deputy
service principal without a source guard (EXTERNAL_TRUST). This exercises
aggregation (Step 9), confused-deputy detection (Step 4), and the
`aws:SourceArn` / `aws:SourceAccount` remediation.

## Input (user prompt)

> We have a role called `data-pipeline-access` that a Lambda function needs
> to assume for cross-service data access. Here's the trust policy. The
> internal CI runner also needs to assume it. Is this trust policy safe?

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowCiRunner",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::123456789012:role/app-ci-runner"
      },
      "Action": "sts:AssumeRole"
    },
    {
      "Sid": "AllowLambdaService",
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

Role ARN: `arn:aws:iam::123456789012:role/data-pipeline-access`

## Skill output

```text
ROLE: data-pipeline-access
VERDICT: EXTERNAL_TRUST
REASON: Statement 1 (Principal: arn:aws:iam::123456789012:role/app-ci-runner
on same account 123456789012) is OK — same-account, specific role ARN. Statement 2
(Principal: {"Service": "lambda.amazonaws.com"} with no Condition) is EXTERNAL_TRUST:
lambda.amazonaws.com is a confused-deputy-risk service. Any AWS customer can create
a Lambda function that triggers an AssumeRole call to this role via the Lambda service,
which the trust policy trusts. The role's entire permission set is exposed to
cross-account exploitation. Role verdict is the worst statement (Step 9 aggregation).
RISK: HIGH
REMEDIATION: Add a source-guard condition to Statement 2 to prevent the confused-deputy
attack:
  "Condition": {
    "ArnLike": {
      "aws:SourceArn": "arn:aws:lambda:us-east-1:123456789012:function:*"
    },
    "StringEquals": {
      "aws:SourceAccount": "123456789012"
    }
  }
This restricts the Lambda service to assume the role only when invoked on behalf of
account 123456789012 and from a function matching the ARN pattern. Use BOTH SourceArn
and SourceAccount for defense-in-depth — SourceArn scopes to a specific resource;
SourceAccount is a fallback if Lambda does not populate SourceArn on all code paths.
Statement 1 requires no change.
```

## What the skill caught that a generic assistant misses

1. **The confused-deputy problem.** A generic assistant often sees
   `Principal: {"Service": "lambda.amazonaws.com"}` and treats it as a
   standard Lambda execution-role pattern — "this is fine, Lambda needs to
   assume the role." The skill recognises that the Lambda service is callable
   by ANY AWS customer, creating a confused-deputy vector: another account's
   Lambda function can trigger an AssumeRole call that the Lambda service
   makes on their behalf, and the trust policy does not distinguish "your
   Lambda" from "their Lambda."

2. **Multi-statement aggregation.** A generic assistant may evaluate each
   statement in isolation and say "Statement 1 is fine, Statement 2 is a
   standard pattern" without aggregating. The skill's Step 9 rule aggregates
   to the worst statement — one EXTERNAL_TRUST statement makes the entire
   role EXTERNAL_TRUST, regardless of how tight the other statements are.

3. **The SourceArn + SourceAccount dual-guard remediation.** Generic advice
   often stops at "add a condition" without specifying which keys. The skill
   supplies both `aws:SourceArn` (resource-level scope, the stronger guard)
   AND `aws:SourceAccount` (account-level fallback) and explains why both
   are needed: some services do not populate `SourceArn` on all code paths,
   making `SourceAccount` a necessary fallback.

## Slash-command invocation

```
/aws:audit-sts-cross-account-role
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit this role's trust policy before we deploy the Lambda integration"
```

The orchestrator emits `[Phase: Audit | Skills routed: sts-cross-account-role-auditor]`
and hands off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "who can assume this role"
# [Phase: Audit | Skills routed: sts-cross-account-role-auditor]
```

## Live-account follow-up (optional, requires AWS CLI)

After hardening the trust policy, verify the Lambda function can still
assume the role:

```bash
aws sts simulate-principal-policy \
  --policy-source-arn arn:aws:iam::123456789012:role/lambda-exec-role \
  --action-names sts:AssumeRole \
  --resource-arns arn:aws:iam::123456789012:role/data-pipeline-access \
  --profile default
```

Then monitor CloudTrail for `AssumeRole` events on the role for 1-2 weeks to
confirm the source guard does not break legitimate workflows.
