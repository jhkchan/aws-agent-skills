# End-to-end usage scenario: organizations-scp-deployer

A walkthrough showing the skill deploying a multi-layer guardrail
strategy across an organization: a guardrail SCP at the root to deny
unapproved regions, a delegate-strategy allowlist carve-out for a
sandbox OU, and an aws:CalledVia-conditioned IAM guardrail on an
application OU.

## Input (user prompt)

> We are establishing landing-zone guardrails for our organization
> root r-abc1. (1) Deploy a guardrail SCP denying all regions except
> us-east-1, eu-west-1, and us-west-2 at the root. (2) For the
> sandbox OU (ou-sandbox), allow the broad set of services in
> `FullAWSAccess` so devs can experiment — but cap EC2 instance
> types to t3.micro/small/medium. (3) For the application OU
> (ou-app-a), allow IAM role creation only via CloudFormation so
> CDK pipelines do not break. Emit the standard VERDICT block per
> policy.

## Skill output — guardrail region deny at root

```text
POLICY_SPEC: deny-unapproved-regions
VERDICT: READY_TO_DEPLOY
ARCHITECTURE:
  Strategy: guardrail
  Target: r-abc1 (root)
  Target scope: root
  FullAWSAccess: preserved
  Policy type enabled: yes
  Statements: 1
  Condition keys used: aws:RequestedRegion
CHECKLIST:
  [x] Policy type SERVICE_CONTROL_POLICY enabled on root
  [x] Strategy pattern documented (guardrail — additive Deny)
  [x] Intersection with parent SCPs evaluated (root has no parent)
  [x] FullAWSAccess preserved
  [x] Principal element omitted
  [x] Condition key aws:RequestedRegion valid for * action
  [x] Rollback path documented (detach-policy)
  [x] Dry-run validation passed (accessanalyzer:ValidatePolicy)
FINDINGS:
  - [INFO] Policy affects 47 member accounts across 6 OUs
  - [WARN] Global services (CloudFront, IAM, Route 53, WAF) MUST be
    exempt via NotAction or they break region-less API calls
DEPLOY_COMMANDS:
  1. aws accessanalyzer validate-policy --policy-document file://scp.json
     --policy-type RESOURCE_POLICY
  2. aws organizations create-policy --content file://deny-regions.json
     --name deny-unapproved-regions --type SERVICE_CONTROL_POLICY
  3. CONFIRM gate
  4. aws organizations attach-policy --policy-id <id> --target-id r-abc1
  5. aws organizations list-policies-for-target --target-id r-abc1
     --filter SERVICE_CONTROL_POLICY (verify)
```

## Skill output — throttle EC2 instance types in sandbox OU

```text
POLICY_SPEC: cap-ec2-instance-types
VERDICT: READY_TO_DEPLOY
ARCHITECTURE:
  Strategy: throttle
  Target: ou-sandbox
  Target scope: OU
  FullAWSAccess: preserved (at root)
  Statements: 1
  Condition keys used: ec2:InstanceType
CHECKLIST:
  [x] Policy type SERVICE_CONTROL_POLICY enabled on root
  [x] Strategy pattern documented (throttle — Deny with condition)
  [x] Intersection with parent SCPs evaluated (root deny-regions
    also applies — sandbox accounts must respect region allowlist)
  [x] FullAWSAccess preserved
  [x] Principal element omitted
  [x] Condition key ec2:InstanceType valid for ec2:RunInstances
  [x] Rollback path documented (detach-policy)
  [x] Dry-run validation passed
FINDINGS:
  - [INFO] Policy affects 12 sandbox accounts in ou-sandbox
  - [INFO] Sandbox accounts retain FullAWSAccess except for the
    EC2 instance-type throttle
DEPLOY_COMMANDS:
  1. aws organizations create-policy --content file://cap-ec2.json
     --name cap-ec2-instance-types --type SERVICE_CONTROL_POLICY
  2. CONFIRM gate
  3. aws organizations attach-policy --policy-id <id>
     --target-id ou-sandbox
```

## Skill output — guardrail IAM via CloudFormation in app OU

```text
POLICY_SPEC: allow-iam-via-cloudformation
VERDICT: READY_TO_DEPLOY
ARCHITECTURE:
  Strategy: guardrail
  Target: ou-app-a
  Target scope: OU
  FullAWSAccess: preserved (at root)
  Statements: 1
  Condition keys used: aws:CalledVia
CHECKLIST:
  [x] Policy type SERVICE_CONTROL_POLICY enabled on root
  [x] Strategy pattern documented (guardrail — Allow with condition)
  [x] Intersection with parent SCPs evaluated
  [x] FullAWSAccess preserved
  [x] Principal element omitted
  [x] Condition key aws:CalledVia valid for iam:CreateRole, iam:PassRole
  [x] Rollback path documented (detach-policy)
  [x] Dry-run validation passed
FINDINGS:
  - [INFO] Policy affects 8 application accounts in ou-app-a
  - [NOTE] Without aws:CalledVia scoping, an Allow for iam:CreateRole
    would be over-broad — any chained service could abuse it
DEPLOY_COMMANDS:
  1. aws organizations create-policy --content file://via-cfn.json
     --name allow-iam-via-cloudformation --type SERVICE_CONTROL_POLICY
  2. CONFIRM gate
  3. aws organizations attach-policy --policy-id <id>
     --target-id ou-app-a
  4. aws organizations list-policies-for-target --target-id ou-app-a
     --filter SERVICE_CONTROL_POLICY (verify)
```

## What the skill adds over a generic assistant

- Intersection-aware blast-radius analysis (every parent OU is
  evaluated before attach).
- Strategy classification (guardrail vs throttle vs delegate) — the
  delegate strategy triggers an explicit lockout warning.
- Global-service exemption list for region-deny SCPs (CloudFront,
  IAM, Route 53, WAF, billing — the standard foot-gun).
- `aws:CalledVia` pattern recognition for chained-service calls.
- Mandatory CONFIRM gate with documented rollback path.
- Dry-run via `accessanalyzer:ValidatePolicy` before `create-policy`.
