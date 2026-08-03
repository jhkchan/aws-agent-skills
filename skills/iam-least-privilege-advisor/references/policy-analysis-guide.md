# IAM Policy Analysis Reference Guide

Supplementary reference for the IAM Least-Privilege Advisor skill.

## Wildcard action patterns

| Pattern | Example | Risk |
| --- | --- | --- |
| `Action: "*"` | All actions | Admin equivalent — maximum blast radius |
| `Service wildcard` | `s3:*`, `ec2:*` | All operations within a service, including destructive |
| `Read wildcard` | `s3:Get*`, `s3:List*` | Broad read access; may include unexpected APIs (e.g., `s3:GetObjectTorrent`) |
| `List wildcard` | `iam:List*` | Enumerates resources; useful for recon but not destructive |

## Resource patterns

| Pattern | Example | Scope |
| --- | --- | --- |
| `Resource: "*"` | All resources in the account | No scope restriction — dangerous with wildcard actions |
| `ARN with wildcard` | `arn:aws:s3:::app-data-*` | Scoped to a naming prefix — acceptable |
| `Specific ARN` | `arn:aws:s3:::app-data-prod` | Tightly scoped — preferred |

## Classification decision tree

```
Statement has Action: "*" AND Resource: "*"?
  -> OVERPERMISSIVE (admin wildcard)

Statement has wildcard action (e.g., s3:*) AND Resource: "*"?
  -> OVERPERMISSIVE (wildcard on all resources)

Statement has wildcard action (e.g., s3:Get*) AND specific resource ARNs?
  -> AMBIGUOUS (wildcard actions, narrow resources)

Statement has specific named actions AND specific resource ARNs?
  -> LEAST_PRIVILEGE
```

## Common over-permissive patterns found in the wild

1. **AdministratorAccess managed policy** attached to an EC2 instance role
   "just in case" — grants every action on every resource.

2. `s3:*` on `*` used by a Lambda that only reads objects — should be
   `s3:GetObject` on the specific bucket ARN.

3. `iam:PassRole` on `*` — allows passing any role to any service,
   enabling privilege escalation.

4. `sts:AssumeRole` on `*` — allows assuming any role in the account.

## Remediation tools

- **AWS IAM Access Analyzer** — generates least-privilege policies from
  CloudTrail activity. The fastest path from wildcard to scoped.
- **`aws iam simulate-principal-policy`** — tests what actions a principal
  can actually perform, revealing unused permissions.
- **CloudTrail EventSource + EventName** — query CloudTrail to discover
  the exact API calls a workload makes, then build an allow-list from that.
- **AWS managed policies vs inline** — prefer inline or customer-managed
  policies for least-privilege. AWS managed policies (AdministratorAccess,
  PowerUserAccess) reintroduce blast radius.
