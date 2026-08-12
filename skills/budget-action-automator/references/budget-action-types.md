# Budget Action Types Reference

Supplementary reference for the Budget Action Automator skill. Use
when selecting an action type, designing the IAM/SCP/SSM payload,
or debugging a budget action that did not fire.

## Action type matrix

| Action type | API value | Target | Reversible | Use case |
|---|---|---|---|---|
| Notify only | `Notification` (not `put-budget-action`) | SNS/email | Yes | Reporting, soft alert |
| Restrict IAM user | `APPLY_IAM_ACTION` | IAM user/group/role | Yes (detach policy) | Per-identity enforcement |
| Block new resources | `APPLY_SCP_FAMILY` | Org account/OU | Yes (detach SCP) | Hard fleet enforcement |
| Stop EC2 | `APPLY_SSM_ACTION` (STOP_EC2_INSTANCES) | EC2 instance IDs | Yes (start instances) | Cost containment via shutdown |
| Custom action | EventBridge → Lambda | Any resource | Varies | Slack, tagging, multi-region |

## API parameter contract

### `APPLY_IAM_ACTION`

```json
{
  "IamActionDefinition": {
    "PolicyArn": "arn:aws:iam::111111111111:policy/budget-restrict",
    "Users": ["ci-bot-prod"],
    "Groups": [],
    "Roles": []
  }
}
```

The policy ARN must already exist. The budget action ATTACHES the
policy on breach; it does NOT detach on recovery.

### `APPLY_SCP_FAMILY`

```json
{
  "ScpActionDefinition": {
    "PolicyId": "p-abc123def456",
    "PolicyDocument": "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Deny\",\"Action\":[\"ec2:RunInstances\"],\"Resource\":\"*\"}]}"
  }
}
```

The SCP must already exist in Organizations. The policy document is
a JSON string — escape inner quotes.

### `APPLY_SSM_ACTION`

```json
{
  "SsmActionDefinition": {
    "ActionSubType": "STOP_EC2_INSTANCES",
    "Region": "us-east-1",
    "InstanceIds": ["i-0abc123def456"]
  }
}
```

Single-region, static instance list. For tag-based or multi-region,
use EventBridge → Lambda.

## Execution role requirements

The execution role MUST have:

1. A trust policy allowing `budgets.amazonaws.com` to assume it.
2. Permissions for the action:
   - IAM: `iam:AttachUserPolicy`, `iam:AttachRolePolicy`,
     `iam:AttachGroupPolicy`
   - SCP: `organizations:AttachPolicy`, `organizations:DetachPolicy`
   - SSM: `ssm:StartAutomationExecution`, plus the runbook's
     required permissions
3. A path that does not exceed the role-session-duration limits.

Bootstrap trust policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "budgets.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

## Common budget action states

| State | Meaning | Operator action |
|---|---|---|
| `PENDING` | Action armed, threshold not yet breached | None |
| `EXECUTED` | Action fired | Verify resource state; verify SCP/IAM/SSM applied |
| `ERROR` | Action attempted but failed | Check execution role; check target exists |
| `DISABLED` | Action explicitly disabled | Re-enable if intended |

## Common failures and fixes

| Failure | Root cause | Fix |
|---|---|---|
| Action stays in `ERROR` | Execution role trust policy missing `budgets.amazonaws.com` | Update trust policy |
| SNS notification never delivered | Topic policy missing budgets service principal | Add `Service: budgets.amazonaws.com` to topic policy |
| SCP attached but no effect | SCP target is wrong (root vs OU vs account) | Verify target via `describe-organization` |
| IAM policy attached but user not restricted | Policy has no `Deny` or has a conflicting `Allow` with `NotAction` | Review IAM policy logic |
| Forecast fires at unexpected % | Forecast is probabilistic (80% confidence) | Pair with higher actual threshold |
| Tag-scoped budget returns $0 | Cost allocation tag not activated | Activate via `ce update-cost-allocation-tags-status` |
| SCP not detaching after period reset | Budgets does NOT auto-detach | Wire Lambda to detach stale SCPs |

## Threshold pairing recommendations

| Pattern | Forecast | Actual | Notes |
|---|---|---|---|
| Notify-only | 80% | 100% | Two-stage alerting |
| IAM action | 90% | 100% | Forecast triggers IAM, actual confirms |
| SCP deny | n/a | 100% | Hard enforcement at breach |
| Stop EC2 | n/a | 110% | Above actual threshold (last resort) |
| Combined | 80% notify, 90% IAM | 100% SCP, 110% SSM | Full escalation ladder |

## Approval model

- `MANUAL` — requires IAM user to approve each fire via console or
  CLI. Recommended for production SCP on first deploy.
- `AUTOMATIC` — fires immediately on threshold breach. Only after
  validation cycle (see SKILL.md expert heuristic).
