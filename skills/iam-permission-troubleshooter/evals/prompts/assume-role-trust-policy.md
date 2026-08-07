# Eval prompt: assume-role-trust-policy

Diagnose the following `sts:AssumeRole` failure. Walk the trust policy
(resource-based) path first, then the identity-based path. Emit the
standard VERDICT block (INCIDENT, VERDICT, ROOT_CAUSE, EVIDENCE,
ROOT_CAUSE_CATALOG, REMEDIATION).

## Scenario

A CI/CD runner using role `arn:aws:iam::111111111111:role/cicd-runner`
attempts to assume `arn:aws:iam::222222222222:role/deploy-target` via
`sts:AssumeRole`.

## Known facts

- The `cicd-runner` role identity policy includes:
  - `sts:AssumeRole` on `arn:aws:iam::222222222222:role/deploy-target`
- The `deploy-target` role's `assumeRolePolicyDocument` has:
  ```json
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "AWS": "arn:aws:iam::222222222222:role/internal-deploy"
        },
        "Action": "sts:AssumeRole"
      }
    ]
  }
  ```
- No SCP, boundary, or session policy on either side.

## Symptom

```
User: arn:aws:sts::111111111111:assumed-role/cicd-runner/github-actions
is not authorized to perform: sts:AssumeRole on resource:
arn:aws:iam::222222222222:role/deploy-target
```
