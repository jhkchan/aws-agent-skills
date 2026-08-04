# End-to-end usage scenario: iam-least-privilege-advisor

A walkthrough showing the skill classifying a multi-statement IAM policy that
contains both a tight read grant and a privilege-escalation grant, then
producing scoped-down remediation. This exercises aggregation (Step 10),
privilege-escalation detection (Step 5), and the CloudTrail-derived remediation
workflow.

## Input (user prompt)

> Review this role policy before we attach it to the `app-reporting-job` EC2
> instance role. We're about to ship to production.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ReadFromDataBucket",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::app-data-prod",
        "arn:aws:s3:::app-data-prod/reports/*"
      ]
    },
    {
      "Sid": "PassRoleForEtl",
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": "*"
    }
  ]
}
```

## Skill output

```text
POLICY: app-reporting-job-role
VERDICT: OVERPERMISSIVE
REASON: Statement 1 (s3:GetObject + s3:ListBucket on arn:aws:s3:::app-data-prod
and its reports/ prefix) is LEAST_PRIVILEGE — specific named actions on specific
ARNs. Statement 2 (iam:PassRole on "*") is OVERPERMISSIVE: iam:PassRole on a
wildcard resource is the most common privilege-escalation vector — the principal
can pass any role in the account to EC2, Lambda, or CloudFormation, and the
passed role's permissions then execute under that service's identity. Policy
verdict is the worst statement (Step 10 aggregation).
RISK: CRITICAL
REMEDIATION: Restrict iam:PassRole in Statement 2 to the specific role ARN the
ETL job needs (e.g., arn:aws:iam::123456789012:role/etl-execution-role). Add
iam:PassRole condition keys to lock the pass to the intended service:
"Condition": {"StringEquals": {"iam:PassedToService": "ec2.amazonaws.com"}}.
Statement 1 requires no change.
```

## What the skill caught that a generic assistant misses

1. **Multi-statement aggregation.** A generic assistant often evaluates each
   statement in isolation and may pronounce the policy "mostly fine" because
   Statement 1 is tight. The skill's Step 10 rule aggregates to the worst
   statement — one OVERPERMISSIVE statement makes the whole policy
   OVERPERMISSIVE.

2. **PassRole on `"*"` is CRITICAL even though neither `Action` nor `Resource`
   is a service wildcard.** The skill's Step 5 recognises `iam:PassRole` on
   `"*"` as a privilege-escalation action that escalates to CRITICAL risk —
   not merely "broad."

3. **The `iam:PassedToService` condition-key remediation.** Generic advice
   often stops at "restrict the resource." The skill supplies the
   service-scoping condition key that prevents the passed role from being
   assumed by a different service.

## Slash-command invocation

```
/aws:audit-iam-least-privilege
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit this role policy before we attach it to production"
```

The orchestrator emits `[Phase: Audit | Skills routed: iam-least-privilege-advisor]`
and hands off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "is this IAM policy over-permissive"
# [Phase: Audit | Skills routed: iam-least-privilege-advisor]
```

## Live-account follow-up (optional, requires AWS CLI)

After scoping down the policy, validate that the principal can still perform
its required operations:

```bash
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::123456789012:role/app-reporting-job \
  --action-names s3:GetObject s3:ListBucket iam:PassRole \
  --resource-arns arn:aws:s3:::app-data-prod/reports/* \
  --profile default
```

Then monitor CloudTrail for `AccessDenied` events for 1-2 weeks and iterate if
the scoped policy is missing a required action.
