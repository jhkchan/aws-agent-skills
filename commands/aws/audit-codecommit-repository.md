---
description: Audit a CodeCommit repository for approval-rule coverage, customer-managed KMS encryption, default-branch deletion protection (IAM enforced), notification rules, and the service-wide deprecation/maintenance risk.
nl_triggers:
  - "audit this CodeCommit repository"
  - "check CodeCommit approval rules"
  - "is my CodeCommit repo encrypted"
  - "CodeCommit branch protection"
  - "CodeCommit notification rules"
  - "CodeCommit deprecation"
  - "migrate off CodeCommit"
  - "CodeCommit repository security"
  - "CodeCommit pull request approval"
  - "CodeCommit KMS encryption"
  - "codecommit audit"
  - "repository approval template"
  - "hardening CodeCommit"
routes_to: codecommit-repository-auditor
---

# /aws:audit-codecommit-repository

Activate the `codecommit-repository-auditor` skill and audit one or more
CodeCommit repositories for security and configuration gaps.

## What it does

Reads a CodeCommit repository configuration bundle (repository metadata +
approval rule templates + KMS key ARN + notification rules + branch
protection IAM policies + tags) and applies the ordered classification
logic:

1. Deprecation advisory — CodeCommit is in maintenance/deprecation mode.
   This finding is ALWAYS emitted.
2. Approval rule template — no template linked or
   `numberOfApprovalsNeeded: 0` is NO_APPROVAL_RULE.
3. KMS encryption — `aws/codecommit` (AWS-managed) or null is NO_ENCRYPTION.
4. Default branch + deletion protection — no IAM Deny on
   `codecommit:DeleteBranch` for the default branch is CONFIG_GAP.
5. Notification rules — no CodeStar Notification rules is CONFIG_GAP.
6. Aggregation — worst finding wins:
   NO_APPROVAL_RULE > NO_ENCRYPTION > CONFIG_GAP > DEPRECATION_RISK > OK.

Emits a deterministic VERDICT per repository:

```text
REPO: <repository-name>
VERDICT: NO_APPROVAL_RULE | NO_ENCRYPTION | CONFIG_GAP | DEPRECATION_RISK | OK
REASON: <1-2 sentences citing the worst finding and step>
FINDINGS:
  - [NO_APPROVAL_RULE] <description (Step N)>
  - [DEPRECATION_RISK] CodeCommit is in maintenance/deprecation mode (Step 1, ALWAYS)
REMEDIATION: <specific action per finding, or migration guidance>
```

## When to invoke

Paste a CodeCommit repository configuration and ask any of:

- "audit this CodeCommit repository"
- "check CodeCommit approval rules"
- "is my CodeCommit repo encrypted?"
- "does my repo have branch protection?"
- "are there notification rules on this repo?"
- "should we migrate off CodeCommit?"

A bare repository name + any audit verb ("audit this repo", "check repo
config") also routes here via the orchestrator.

## Inputs

- A CodeCommit repository configuration bundle, pasted inline or
  referenced by file path.
- Repository metadata: defaultBranch, kmsEncryptionKeyId,
  approvalRuleTemplates (with content), notificationRules,
  branchProtectionIamPolicies, tags.
- For live-account audit: a repository name or ARN.

## Outputs

- One VERDICT block per repository (multiple findings aggregate to the
  worst verdict).
- Enumerated FINDINGS list with per-finding label and step citation.
- The DEPRECATION_RISK finding is ALWAYS present regardless of verdict.
- Specific remediation: create approval rule templates, plan CMK-backed
  repo migration, add IAM branch-protection policies, create CodeStar
  notification rules, and evaluate migration to GitHub/GitLab.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for CodeCommit / Developer Tools).
- `/aws:audit-kms-key-policy` to audit the customer-managed KMS key used
  by a CodeCommit repository (if CMK encryption is configured).
