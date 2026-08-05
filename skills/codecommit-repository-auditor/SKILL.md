---
name: codecommit-repository-auditor
description: >-
  Audits AWS CodeCommit repositories for approval-rule-template coverage,
  customer-managed KMS encryption, default-branch deletion protection (IAM
  enforced, not native), notification-rule alerting, and the CodeCommit
  service-wide deprecation/maintenance mode risk. Emits a deterministic
  verdict (NO_APPROVAL_RULE | NO_ENCRYPTION | CONFIG_GAP | DEPRECATION_RISK
  | OK) per repository with enumerated findings and specific CLI
  remediation. Use when reviewing CodeCommit repositories, checking pull
  request review enforcement, validating encryption-key control, auditing
  branch protection, or assessing migration urgency due to service
  deprecation.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline config classification. Live-account
  audits use aws codecommit get-repository, aws codecommit
  list-approval-rule-templates, aws codecommit list-tags-for-resource, and
  aws codestar-notifications list-notification-rules (AWS CLI v2, SSO or
  key-based credentials).
keywords:
  - CodeCommit
  - repository audit
  - approval rule template
  - KMS encryption
  - branch deletion protection
  - notification rules
  - CodeStar Notifications
  - default branch
  - deprecation
  - maintenance mode
  - migration
  - pull request approval
  - code review enforcement
  - supply chain security
  - repository policy
  - codecommit:DeleteBranch
  - codecommit:References
  - aws/codecommit
  - customer managed key
tags: [codecommit, devtools, security, repository, approval-rule, encryption, branch-protection, deprecation, audit]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: DevTools
  verdict_shape: "NO_APPROVAL_RULE | NO_ENCRYPTION | CONFIG_GAP | DEPRECATION_RISK | OK"
  when_to_use: >-
    Reviewing a CodeCommit repository before production deployment, checking
    pull-request approval enforcement, validating customer-managed KMS
    encryption, auditing branch deletion protection, verifying notification
    alerting, or assessing CodeCommit migration urgency due to service
    deprecation/maintenance mode.
  activation_triggers:
    - "audit CodeCommit repository approval rules and encryption"
    - "check CodeCommit pull request approval enforcement"
    - "is my CodeCommit repo using a customer managed KMS key"
    - "CodeCommit branch deletion protection IAM audit"
    - "CodeCommit notification rules CodeStar audit"
    - "CodeCommit deprecation migration assessment"
    - "migrate off CodeCommit repository audit checklist"
    - "CodeCommit repository security and config gap audit"
  invocation_schema: >-
    Input: either (a) a CodeCommit repository configuration bundle
    (repository metadata + approval rule templates + KMS key ARN +
    notification rules + branch protection IAM policies + tags), OR (b) a
    repository name/ARN for live-account audit. Output: deterministic
    REPO/VERDICT/REASON/FINDINGS/REMEDIATION block per repository, where
    VERDICT is one of {NO_APPROVAL_RULE, NO_ENCRYPTION, CONFIG_GAP,
    DEPRECATION_RISK, OK}.
---

# CodeCommit Repository Auditor

## Quick start — verdict decision tree

```text
FOR EACH repository:
  1. Approval rules? NO template OR numberOfApprovalsNeeded == 0
     → NO_APPROVAL_RULE (highest priority — stop)
  2. Encryption? kmsEncryptionKeyId == aws/codecommit | null | absent
     → NO_ENCRYPTION (immutable — cannot fix without repo recreation)
  3. Branch protection OR notifications missing?
     → CONFIG_GAP
  4. All config passes, no migration-acknowledgment tag?
     → DEPRECATION_RISK
  5. All config passes + migration tag (migration-plan / migration-target)?
     → OK
```

Priority: `NO_APPROVAL_RULE > NO_ENCRYPTION > CONFIG_GAP > DEPRECATION_RISK > OK`

DEPRECATION_RISK is ALWAYS emitted in FINDINGS regardless of verdict.
CodeCommit is in maintenance/deprecation mode — the finding only drives
the verdict when no config gap exists.

## Philosophy & Mindset

Three properties make CodeCommit audit distinct from other AWS services:

1. **No native branch-protection API.** Unlike GitHub, branch deletion
   prevention is enforced entirely through IAM Deny policies on
   `codecommit:DeleteBranch` with `codecommit:References` conditions. A
   repo without these IAM policies has zero protection on any branch.

2. **KMS key is immutable after creation.** `kmsEncryptionKeyId` is set at
   repository creation and CANNOT be changed. A repo using the
   AWS-managed key (`aws/codecommit`) cannot be migrated to a CMK without
   creating a new repository and pushing all history. This is a one-way
   door.

3. **CodeCommit is in maintenance/deprecation mode.** AWS has frozen new
   feature development. A perfectly configured repo still carries
   DEPRECATION_RISK — every audit must surface this.

**The verdict is always the worst finding across all dimensions.**

## Process — classification logic

### Expert knowledge — non-obvious CodeCommit behaviors

These behaviors are easy to misjudge without operational CodeCommit
experience. Each changes the verdict if ignored:

- **Approval rule templates are account-level, not repo-level.** There
  is NO `list-approval-rule-templates --repository-name` API — list ALL
  templates and check each one's linked-repository list. Templates cap
  at 100 per page; use `--next-token` to drain all pages.

- **`numberOfApprovalsNeeded: 0` is effectively disabled.** A linked
  template with zero approvals provides ZERO enforcement. Treat as
  NO_APPROVAL_RULE. Minimum effective value is 1.

- **Merge APIs bypass approval rules entirely.**
  `codecommit:MergeBranchesByFastForward` and
  `codecommit:MergeBranchesBySquash` are NOT gated by approval rule
  templates — approval rules only apply to `merge-pull-request-*` calls.
  A developer with direct merge IAM permissions can merge code without
  any PR or review. Flag this as a risk even when approval rules exist.

- **KMS key is IMMUTABLE.** No `update-repository-encryption-key` API.
  Migrating from AWS-managed to CMK requires creating a new repo and
  pushing all history. The remediation cost is high: repo recreation +
  CI/CD reconfiguration + developer remoting.

- **`aws/codecommit` is a SHARED AWS-managed key.** All repos in the
  account/region share one key. No key policy visibility, no rotation
  control (AWS manages annual rotation), no per-repo isolation.

- **CMK rotation matters for compliance, not just crypto.** A CMK with
  `EnableKeyRotation: false` fails PCI-DSS Requirement 3.6, HIPAA
  164.312(a)(2)(iv), and SOC 2 CC6.1. Active rotation limits blast
  radius of a key compromise — without rotation, a single stolen key
  material decrypts all historical ciphertext indefinitely. Flag
  `EnableKeyRotation: false` as HIGH (additive, does not change verdict
  — the CMK itself is the improvement over AWS-managed).

- **Notification rules are CodeStar Notifications, not CodeCommit.**
  `aws codecommit` APIs never return notification coverage. Use
  `aws codestar-notifications list-notification-rules --resource
  <repo-arn>`. This is the most common audit blind spot — the auditor
  who only queries CodeCommit APIs sees zero notification rules even
  when they exist.

- **`codecommit:References` requires full ref path.** IAM policies must
  use `refs/heads/main`, not bare `main`. Bare names silently fail to
  match — the policy appears valid but provides zero protection.

- **Default branch is not always `main`.** Pre-2020 repos default to
  `master`; migrated repos may use `develop`, `trunk`, `production`.
  Always read `defaultBranch` from `get-repository`. IAM policies
  hardcoded to `refs/heads/main` give zero protection when default is
  `master` — the most common branch-protection false negative.

- **Repository triggers cap at 10 per repo.** Legacy triggers for
  Lambda/SNS have a hard cap. Notification rules (CodeStar) have no
  per-repo cap. If a repo has 10 triggers, additional alerting must
  use CodeStar Notifications.

- **Cross-region replication supports only ONE destination region.**
  Unlike S3, a CodeCommit repo replicates to at most one additional
  region. Multi-region DR requires git mirroring, not native replication.

- **`update-default-branch` does NOT validate branch existence.**
  Switching to a non-existent branch breaks all clones silently — `git
  clone` and `git fetch` fail until corrected. Always verify the branch
  exists before calling this API.

- **Approval rule template `content` is JSON, not a simple count.** The
  `content` field has a `Statements` array; multiple statements are
  AND-ed. Evaluate ALL — the most restrictive applies. A template with
  two statements requiring 1 and 3 approvals needs 4 total approvals.

### Wildcard matching algorithm — repo name to template pattern

Approval rule templates link to repositories by name pattern. To
determine if a template covers a specific repo, apply this algorithm:

```text
For each template T with linked-repository pattern P, repo name R:
  1. P == "*"                     → MATCH (covers all repos)
  2. P == R                        → MATCH (exact)
  3. P ends with "*" (e.g. "my-app-*")
     → MATCH if R starts with prefix before "*"
       (e.g. "my-app-backend" matches, "backend-my-app" does NOT)
  4. P contains no wildcard        → exact match required (P must == R)
  5. No pattern matches            → template does NOT cover R
```

Common false negative: assuming `my-app-*` covers `backend-my-app` —
it does NOT. CodeCommit wildcard patterns are prefix-only.

### Step 1: Deprecation risk (always emit, drives verdict only when no config gap)

- **DEPRECATION_RISK finding is ALWAYS emitted.** Appears in every
  audit regardless of config quality. CodeCommit is frozen — no new
  features, no new APIs, no new encryption options.
- **Verdict impact:** becomes the verdict ONLY when all config dimensions
  pass. Config findings take precedence.
- **Migration acknowledgment:** if repo has tag `migration-plan` or
  `migration-target` with non-empty value (e.g. `active`, `github`),
  deprecation is downgraded to informational — does NOT prevent OK.

### Step 2: Approval rule template evaluation (highest-priority config finding)

- **No template linked** → **NO_APPROVAL_RULE**. PRs mergeable with
  zero approvals. Any principal with `MergePullRequestByFastForward`
  can push directly.
- **Template linked, `numberOfApprovalsNeeded: 0`** →
  **NO_APPROVAL_RULE**. Effectively disabled — approvals auto-satisfy.
- **Template linked, `numberOfApprovalsNeeded >= 1`** → OK.
- **Multiple templates** → evaluate ALL. If ANY has `>= 1`, dimension
  passes (most restrictive statement applies).

### Step 3: KMS encryption evaluation

- **`kmsEncryptionKeyId` is `aws/codecommit`, null, or absent** →
  **NO_ENCRYPTION**. No customer key control — shared AWS-managed key
  across all repos in account/region.
- **CMK ARN present** → OK. Verify rotation enabled (flag as additive
  HIGH if `EnableKeyRotation: false` — see compliance note above).
- Note: "NO_ENCRYPTION" means no *customer-managed* encryption —
  CodeCommit ALWAYS encrypts at rest. The AWS-managed key provides
  encryption but no customer control over key policy or rotation.

### Step 4: Default branch + deletion protection

- **Default branch null or non-existent** → **CONFIG_GAP**. Broken
  state — clones fail, CI/CD cannot resolve default branch.
- **No IAM Deny on `codecommit:DeleteBranch` for default branch ref**
  → **CONFIG_GAP**. Any principal with DeleteBranch can delete it.
- **IAM Deny exists for `refs/heads/<default>`** → OK.

### Step 5: Notification rules

- **No notification rules** → **CONFIG_GAP**. No automated alerting on
  PR/branch events — stealthy attacker pushing malicious code triggers
  zero alerts.
- **Rules exist but target deleted/disconnected SNS topic** →
  **CONFIG_GAP**. Decorative — events generated but not delivered.
- **Rules exist with active SNS target** → OK.

### Step 6: Aggregation — worst finding wins

```text
if approval_rule_finding == FAIL:      verdict = NO_APPROVAL_RULE
elif encryption_finding == FAIL:        verdict = NO_ENCRYPTION
elif branch OR notification == FAIL:    verdict = CONFIG_GAP
elif migration_acknowledged == False:   verdict = DEPRECATION_RISK
else:                                   verdict = OK
```

## Output format (per repository)

```text
REPO: <repository-name>
VERDICT: NO_APPROVAL_RULE | NO_ENCRYPTION | CONFIG_GAP | DEPRECATION_RISK | OK
REASON: <1-2 sentences citing the worst finding and its step>
FINDINGS:
  - [NO_APPROVAL_RULE] <description (Step N)>
  - [DEPRECATION_RISK] CodeCommit is in maintenance/deprecation mode — evaluate migration (Step 1, ALWAYS)
  - [OK] <dimension that passed>
REMEDIATION: <specific action per finding, or migration guidance>
```

### Worked example — no approval rule, AWS-managed key

```text
REPO: my-app-backend
VERDICT: NO_APPROVAL_RULE
REASON: No approval rule template is linked to this repository, so pull
requests can be merged with zero code review (Step 2). The repository also
uses the AWS-managed KMS key with no customer-controlled encryption.
FINDINGS:
  - [NO_APPROVAL_RULE] No approval rule template linked — PRs mergeable with 0 approvals (Step 2)
  - [NO_ENCRYPTION] kmsEncryptionKeyId is aws/codecommit (AWS-managed) — no customer key control (Step 3)
  - [DEPRECATION_RISK] CodeCommit is in maintenance/deprecation mode — evaluate migration (Step 1, ALWAYS)
REMEDIATION:
  1. Create and link an approval rule template: aws codecommit create-approval-rule-template ...
  2. The KMS key cannot be changed post-creation — plan repo migration to a CMK-backed repo.
  3. Evaluate migration to GitHub/GitLab as CodeCommit is deprecated.
```

## Anti-Patterns — NEVER

- **NEVER omit the DEPRECATION_RISK finding.** Every CodeCommit repo
  carries deprecation risk. An audit without it implies the service is
  viable long-term, which it is not.

- **NEVER report "NO_ENCRYPTION" as "data is unencrypted."** CodeCommit
  ALWAYS encrypts at rest. The finding means no customer-managed key.
  Conflating these causes unnecessary panic and erodes trust.

- **NEVER claim the KMS key can be changed post-creation.**
  `kmsEncryptionKeyId` is IMMUTABLE. Remediation requires repo recreation.
  Do not suggest `aws codecommit update-*` for encryption.

- **NEVER assert CodeCommit has native branch-protection rules.** Branch
  protection is IAM-only via Deny on `codecommit:DeleteBranch` with
  `codecommit:References`. Claiming a native feature sends operators
  looking for a non-existent setting.

- **NEVER treat `numberOfApprovalsNeeded: 0` as effective enforcement.**
  Zero approvals = zero enforcement. Functionally identical to no template.

- **NEVER query only `aws codecommit` for notification rules.**
  Notifications are CodeStar Notifications — a separate service. A
  CodeCommit-only query returns zero even when rules exist.

- **NEVER ignore CMK rotation status.** A CMK without rotation fails
  PCI-DSS 3.6, HIPAA 164.312, and SOC 2 CC6.1. Without rotation, stolen
  key material decrypts all historical ciphertext permanently. It does
  not change the verdict but MUST appear in FINDINGS as HIGH.

- **NEVER create a new CodeCommit repo as long-term remediation** without
  flagging deprecation risk. The correct long-term fix is migration to
  GitHub/GitLab.

- **NEVER assume `codecommit:References` accepts bare branch names.**
  Must use `refs/heads/main`, not `main`. Bare names silently fail.

- **NEVER assume the default branch is `main`.** Pre-2020 repos use
  `master`. IAM policies hardcoded to `refs/heads/main` give zero
  protection when default is `master` — most common false negative.

- **NEVER assume a template covers a repo just because it exists.**
  Verify the actual name pattern match using the wildcard algorithm.

- **NEVER classify multiple gaps as anything other than the highest-priority
  gap.** NO_APPROVAL_RULE always supersedes NO_ENCRYPTION. Enumerate all
  findings but the verdict reflects the worst single dimension.

## Pre-flight safety checks

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation,
  emit: `CONFIRM: About to <action> on repository <name> in account
  <account>. Proceed? (yes/no)`
- **IAM policy changes: scope to developer roles ONLY.** Never attach
  Deny policies to admin or break-glass roles — they need deletion
  capability during incident response. Explicitly target roles named
  `developer-*` or `engineer-*`; never use `Principal: "*"`.
- **Default-branch change is disruptive.** Warn that CI/CD pipelines
  referencing the old name need updating.
- **Repository deletion has a 7-day recovery window** via
  `undo-delete-repository`. Always snapshot before deletion.

## Remediation guidance

### NO_APPROVAL_RULE — create and link template

```bash
aws codecommit create-approval-rule-template \
  --approval-rule-template-name require-1-approval \
  --approval-rule-template-content '{"Version":"2018-02-08","Statements":[{"Type":"Approvers","NumberOfApprovalsNeeded":1}]}'

aws codecommit batch-associate-approval-rule-template-with-repositories \
  --approval-rule-template-name require-1-approval \
  --repository-names <repo-name>
```

Existing open PRs are NOT retroactively protected — close and reopen to apply.

### NO_ENCRYPTION — plan repository migration

KMS key is immutable. Path:
1. Create new repo with CMK: `aws codecommit create-repository --repository-name <name>-cmk --kms-key-id <cmk-arn>`
2. Migrate: `git remote add new-origin <url> && git push new-origin --all && git push new-origin --tags`
3. Update CI/CD and developer remotes.
4. Given deprecation, evaluate GitHub/GitLab migration instead.

### CONFIG_GAP — branch protection (IAM enforced)

```bash
aws iam put-role-policy --role-name <developer-role> \
  --policy-name deny-delete-default-branch \
  --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Deny","Action":["codecommit:DeleteBranch","codecommit:GitPush"],"Resource":"arn:aws:codecommit:<region>:<account>:<repo>","Condition":{"StringEqualsIfExists":{"codecommit:References":["refs/heads/main"]}}}]}'
```

Scope to developer-level roles only — never attach to admin/break-glass roles.

### CONFIG_GAP — notification rules (CodeStar Notifications)

```bash
aws sns create-topic --name codecommit-alerts
aws codestar-notifications create-notification-rule \
  --name codecommit-pr-alerts \
  --resource arn:aws:codecommit:<region>:<account>:<repo> \
  --event-type-ids codecommit-pull-request-created codecommit-pull-request-merged \
  --target Type=SNS,TargetArn=arn:aws:sns:<region>:<account>:codecommit-alerts
```

### DEPRECATION_RISK — migration planning

```bash
aws codecommit tag-resource \
  --resource-arn arn:aws:codecommit:<region>:<account>:<repo> \
  --tags migration-plan=active,migration-target=github
```

After migration: `git clone --mirror`, push to GitHub/GitLab, update remotes,
delete CodeCommit repo to reduce attack surface.

### OK

No config remediation needed. DEPRECATION_RISK finding still present —
continue migration planning.

## Reference

### Live-account pagination loop with throttling back-off

CodeCommit and IAM APIs throttle at ~1 req/s burst. For large accounts,
silently truncate at 100 items per page without `--next-token`.

```bash
# Drain all approval rule templates (100/page cap, handles ThrottlingException)
NEXT_TOKEN=""
while true; do
  if [ -z "$NEXT_TOKEN" ]; then
    RESP=$(aws codecommit list-approval-rule-templates --output json 2>&1)
  else
    RESP=$(aws codecommit list-approval-rule-templates --next-token "$NEXT_TOKEN" --output json 2>&1)
  fi
  if echo "$RESP" | grep -q "ThrottlingException"; then
    sleep 2  # exponential backoff on throttle
    continue
  fi
  echo "$RESP" | jq '.approvalRuleTemplates[]'
  NEXT_TOKEN=$(echo "$RESP" | jq -r '.nextToken // empty')
  [ -z "$NEXT_TOKEN" ] && break
  sleep 1  # rate-limit avoidance
done
```

Same pattern applies to `list-repositories` (100/page) and
`codestar-notifications list-notification-rules` (100/page).

### IAM enumeration for branch protection

There is no single API to determine branch-protection coverage. Cross-service
scan required:

1. `aws iam list-roles` (paginated, 100/page).
2. For each role: `list-attached-role-policies` + `list-role-policies`.
3. Retrieve each policy document (`get-policy-version` / `get-role-policy`).
4. Scan for `Effect: Deny` on `codecommit:DeleteBranch` with
   `codecommit:References` matching `refs/heads/<default>`.
5. O(roles x policies) — cache results across repos (only repo ARN match
   changes). Rate-limit to ~1 req/s to avoid `ThrottlingException`.

Read-only auditor roles typically lack `codecommit:ListApprovalRuleTemplates`
and `iam:GetRolePolicy` — surface this permission gap before the operator
approves deeper inspection.

### CodeStar Notifications event types

`codecommit-pull-request-created`, `codecommit-pull-request-updated`,
`codecommit-pull-request-merged`, `codecommit-branch-created`,
`codecommit-branch-deleted`, `codecommit-commit-comment`.

Without rules on at minimum `pull-request-merged` and `branch-deleted`,
critical events go unalerted.

### Approval rule template content structure

```json
{
  "Version": "2018-02-08",
  "Statements": [
    {
      "Type": "Approvers",
      "NumberOfApprovalsNeeded": 2,
      "ApprovalPoolMembers": ["arn:aws:sts::123456789012:assumed-role/senior-devs"]
    }
  ]
}
```

Multiple statements are AND-ed. Empty `ApprovalPoolMembers` means any
principal with `codecommit:ApprovePullRequest` can approve.

## Recent AWS features (2024-2026)

- **CodeCommit closed to new customers (2024):** AWS stopped onboarding new CodeCommit customers. Existing customers can continue using the service, but no new features are being added. Auditors should flag CodeCommit as a deprecation/migration risk — the skill already covers this as DEPRECATION_RISK. Recommend migration to GitHub, GitLab, or Bitbucket for any repos with long-term lifecycle expectations.
- **No new feature launches:** CodeCommit has received no new security features, configuration fields, or capabilities since the freeze. The audit surface is static.

## Domain

AWS CloudOps / Developer Tools Security & CodeCommit Migration Assessment.
