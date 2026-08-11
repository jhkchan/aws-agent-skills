# Eval prompt: oam-org-wide-sink-policy-fleet

Deploy an org-wide CloudWatch cross-account observability topology
using `aws:PrincipalOrgID` and CloudFormation StackSets. Walk the
pre-flight checks and emit the standard VERDICT block.

## Scenario

An operator with AWS organization `o-abcdef1234` wants to deploy
CloudWatch cross-account observability for a fleet of 60+ source
accounts. The monitoring account is `111122223333` (us-east-1).
The operator wants an org-wide sink policy so new accounts
auto-attach without manual policy edits.

## Known facts

- **Monitoring account:** `111122223333` (us-east-1).
- **Organization ID:** `o-abcdef1234`.
- **Fleet size:** 60+ source accounts, growing.
- **Metrics to share:** `AWS/EC2`, `AWS/ECS`, `AWS/Lambda`.
- **Log groups to share:** any under `prefix("/aws/")`.
- **Traces / Application Signals:** not required for this fleet.
- **Sink policy approach:** `aws:PrincipalOrgID` condition;
  no manual per-account entries.
- **Link deployment:** CloudFormation StackSets with
  `SERVICE_MANAGED` permission model and auto-deployment enabled.

## Symptom

The operator needs the org-wide sink policy JSON, the StackSets
template, and the `create-stack-set` / `create-stack-instances`
CLI to deploy the link across the org.
