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
    - "audit this CodeCommit repository"
    - "check CodeCommit approval rules"
    - "is my CodeCommit repo encrypted"
    - "CodeCommit branch protection"
    - "CodeCommit notification rules"
    - "CodeCommit deprecation"
    - "migrate off CodeCommit"
    - "CodeCommit repository security"
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

## Mindset

**One-line takeaway:** the verdict is always the **worst** finding across
all dimensions, and CodeCommit's deprecation/maintenance mode is an
**always-present strategic risk** that surfaces as DEPRECATION_RISK when
every config dimension passes.

Three properties make CodeCommit audit distinct from other AWS services:

- **CodeCommit has NO native branch-protection API.** Unlike GitHub's
  protection rules, CodeCommit branch deletion prevention is enforced
  entirely through IAM Deny policies on `codecommit:DeleteBranch` with
  `codecommit:References` conditions. A repo without these IAM policies
  has zero protection on any branch — including the default branch.
- **The KMS key is immutable after creation.** `kmsEncryptionKeyId` is set
  at repository creation and CANNOT be changed. A repo using the
  AWS-managed key (`aws/codecommit`) cannot be migrated to a CMK without
  creating a new repository and pushing all history. This makes the
  encryption finding a one-way door.
- **CodeCommit is in maintenance/deprecation mode.** AWS announced no new
  features or investment. While existing repos continue to function, the
  service carries long-term viability risk that must be surfaced on every
  audit — a perfectly configured repo still has DEPRECATION_RISK.

## Quick reference — verdict thresholds

| Condition | Verdict | Step |
|---|---|---|
| No approval rule template linked (or `numberOfApprovalsNeeded: 0`) | **NO_APPROVAL_RULE** | Step 2 |
| `kmsEncryptionKeyId` is `aws/codecommit`, null, or absent | **NO_ENCRYPTION** | Step 3 |
| No notification rules AND/OR no IAM branch-deletion protection on default branch | **CONFIG_GAP** | Step 4/5 |
| All config dimensions pass, no migration-acknowledgment tag | **DEPRECATION_RISK** | Step 1/6 |
| All config dimensions pass + migration-acknowledgment tag present | **OK** | Step 6 |

Priority order (worst finding wins):
`NO_APPROVAL_RULE > NO_ENCRYPTION > CONFIG_GAP > DEPRECATION_RISK > OK`

The deprecation finding is ALWAYS emitted regardless of verdict — it
appears in FINDINGS on every CodeCommit repository. It only drives the
verdict when no higher-severity config finding exists.

## Pre-flight: CodeCommit deprecation advisory

**CodeCommit is in AWS maintenance/deprecation mode.** As of 2025, AWS
has frozen new feature development and actively recommends migration to
GitHub, GitLab, or Git-based alternatives. Key implications:

1. **No new features.** Existing functionality continues, but no
   enhancements (no new approval-rule features, no new branch-protection
   APIs, no new encryption options). Security patches continue but the
   roadmap is frozen.
2. **No new account-level capabilities.** Cross-region replication, native
   branch protection, and advanced CI/CD integrations will not arrive.
3. **Migration planning is mandatory.** Every audit MUST include a
   deprecation finding recommending migration evaluation. The question is
   not "should we migrate?" but "when and how?"
4. **The `aws/codecommit` AWS-managed key persists.** Even after migrating
   all repos, the managed key remains in the account until all repos are
   deleted — it cannot be manually removed.

**Every audit output MUST include this finding:**
`[DEPRECATION_RISK] CodeCommit is in maintenance/deprecation mode —
evaluate migration to GitHub/GitLab. This finding is ALWAYS present on
CodeCommit repositories.`

**Live-account pre-flight checks (skip for offline config audit):**
1. Verify the caller has `codecommit:GetRepository` — read-only auditor
   roles typically can, but approval-rule-template listing requires
   `codecommit:ListApprovalRuleTemplates` which is often missing from
   read-only roles. Surface this before the operator approves deeper
   inspection.
2. Notification rules are NOT in the CodeCommit API — they are managed
   via AWS CodeStar Notifications
   (`aws codestar-notifications list-notification-rules --resource
   arn:aws:codecommit:<region>:<acct>:<repo>`). An auditor who only
   queries `codecommit` APIs will miss notification coverage entirely.
3. Branch-protection IAM policies require `iam:ListRolePolicies` /
   `iam:GetRolePolicy` to enumerate — CodeCommit APIs cannot reveal
   which IAM policies protect branches. This is a cross-service audit.

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious CodeCommit behaviors

These behaviors are easy to misjudge without operational CodeCommit
experience. Each changes the verdict if ignored:

- **Approval rule templates are account-level, not repo-level.** A
  template is created at the account/region level and then linked to
  repositories by name pattern. There is NO `list-approval-rule-templates
  --repository-name` API — you must list ALL templates
  (`aws codecommit list-approval-rule-templates`) and check each one's
  linked repository list to determine coverage for a specific repo.

- **`numberOfApprovalsNeeded: 0` is an effectively disabled template.** A
  template linked to the repo with `numberOfApprovalsNeeded: 0` provides
  ZERO enforcement — the approval rule is instantly satisfied. Treat as
  NO_APPROVAL_RULE. The minimum effective value is 1.

- **The KMS key is IMMUTABLE.** `kmsEncryptionKeyId` is set at
  `create-repository` time and cannot be changed post-creation. There is
  no `update-repository-encryption-key` API. To migrate from the
  AWS-managed key to a CMK, you must create a new repository and push
  all history. This is why NO_ENCRYPTION is a high-severity finding — the
  remediation is expensive (repo recreation + CI/CD reconfiguration +
  developer remoting).

- **CodeCommit does NOT have native branch-protection rules.** Unlike
  GitHub's `protection_rules`, CodeCommit branch deletion prevention is
  enforced via IAM Deny policies:
  `Deny codecommit:DeleteBranch` with `codecommit:References` condition
  matching the branch name (e.g., `refs/heads/main`). A repo audit that
  only checks CodeCommit config (not IAM) will miss the absence of
  branch protection. The IAM policy is the ONLY enforcement layer.

- **Notification rules are CodeStar Notifications, not CodeCommit.**
  Notification rules for CodeCommit events (PR created, branch deleted,
  commit pushed) are managed via the
  `aws codestar-notifications` API, NOT the `codecommit` API. The ARN
  format for the resource is the CodeCommit repo ARN. An auditor using
  only `aws codecommit` commands will never see notification coverage.

- **`aws/codecommit` is a SHARED AWS-managed key.** All repos in the
  account/region using the default encryption share a single
  AWS-managed KMS key. You cannot view its key policy, control its
  rotation schedule (automatic, annual), or restrict which repos it
  encrypts. It is fundamentally a "trust AWS" posture.

- **Repository size quota is 5 GB (soft limit 25 GB).** A repo exceeding
  5 GB without a limit increase will reject pushes. Large monorepos
  with binary assets hit this silently. This is an operational risk, not
  a security verdict driver, but flag as a note if the repo is near the
  limit.

- **Default-branch deletion breaks all clones.** If the default branch
  is deleted, `git clone` and `git fetch` fail until a new default is
  set via `aws codecommit update-default-branch`. CodeCommit does NOT
  prevent default-branch deletion by default — only IAM Deny policies
  can block it.

- **Cross-account access is via repository policy OR IAM.** CodeCommit
  repository policies (resource-based) are optional. Without a policy,
  access is controlled by IAM alone. A repo with no policy is NOT more
  or less secure — it simply means access control is IAM-only.

- **Approval rule template content is a JSON structure, not a simple
  count.** The template's `content` field is a JSON object with an
  `Statements` array, each specifying `NumberOfApprovalsNeeded` and
  optional `ApprovalPoolMembers`. A template can have multiple
  statements with different approval requirements. Evaluate ALL
  statements — the MOST RESTRICTIVE applies.

- **`codecommit:References` condition uses `refs/heads/<branch>` format.**
  When writing IAM branch-protection policies, the condition key value
  must use the full ref path (`refs/heads/main`), not just the branch
  name (`main`). Using the bare branch name silently fails to match.

- **Pagination and API quotas for live-account audit.**
  `aws codecommit list-approval-rule-templates` returns at most 100
  templates per page — use `--next-token` to drain all pages; accounts
  with many templates will silently truncate on the first page.
  `aws codestar-notifications list-notification-rules` paginates at 100
  per page as well. Both APIs throttle at ~1 request/second in burst
  mode — an auditor scanning 500+ repos should batch and rate-limit to
  avoid `ThrottlingException`. The `list-repositories` API also caps at
  100/page; for large accounts, always iterate to completion.

- **Approval rule template wildcard patterns can silently mismatch.**
  A template linked to `my-app-*` covers `my-app-backend` but NOT
  `backend-my-app`. When verifying coverage, pattern-match the actual
  repository name against the template's linked-repository name list —
  do not assume a template is linked just because the name sounds
  similar. A template linked to `*` (all repos) covers every repo, but
  templates linked to specific names require exact matches.

- **Default branch is not always `main`.** CodeCommit repos created
  before ~2020 default to `master`; repos migrated from other systems
  may use `develop`, `trunk`, or `production`. Always read
  `defaultBranch` from `get-repository` metadata — do NOT assume
  `main`. Branch-protection IAM policies that hardcode `refs/heads/main`
  provide ZERO protection when the default branch is `master`.

- **Live-account IAM enumeration for branch protection requires
  cross-service role-policy scanning.** There is no single API to
  determine "which IAM policies protect this branch." See the
  [Deep reference](#iam-enumeration-procedure-for-branch-protection)
  section for the full O(roles x policies) scan procedure.

### Step 1: Deprecation risk (always emit, drives verdict only when no config gap)

Evaluate the CodeCommit service-wide deprecation status:

- **DEPRECATION_RISK finding is ALWAYS emitted.** CodeCommit is in
  maintenance/deprecation mode. This finding appears in every audit
  output regardless of configuration quality.
- **Verdict impact:** DEPRECATION_RISK becomes the verdict ONLY when all
  config dimensions (approval rules, encryption, branch protection,
  notifications) pass. If any config dimension fails, the config finding
  takes precedence as the verdict.
- **Migration acknowledgment check:** if the repository has a tag
  indicating migration planning (e.g., `migration-plan`, `migration-target`,
  `codecommit-migration`), the deprecation finding is downgraded to
  informational and does NOT prevent an OK verdict. The tag value should
  be non-empty (e.g., `migration-plan: active`, `migration-target: github`).
  A tag key with an empty value does NOT count as acknowledgment.
  Recognized migration-acknowledgment tag keys: `migration-plan`
  (value e.g. `active`, `scheduled`, `evaluating`), `migration-target`
  (value e.g. `github`, `gitlab`, `bitbucket`). Any non-empty value on
  either tag key satisfies the acknowledgment check.

### Step 2: Approval rule template evaluation (highest-priority config finding)

Check whether the repository has effective approval rule coverage:

- **No approval rule template linked** → **NO_APPROVAL_RULE** finding.
  Without a template, pull requests can be merged with zero approvals.
  Any principal with `codecommit:MergeBranchesByFastForward` /
  `codecommit:MergePullRequestByFastForward` can push directly.
- **Template linked but `numberOfApprovalsNeeded: 0`** → **NO_APPROVAL_RULE**
  finding. The template is effectively disabled — approvals auto-satisfy.
- **Template linked with `numberOfApprovalsNeeded >= 1`** → OK for this
  dimension. At least one approval is required before merge.
- **Multiple templates linked** → evaluate ALL. If ANY template has
  `numberOfApprovalsNeeded >= 1`, the dimension passes (the most
  restrictive statement applies). If ALL linked templates have
  `numberOfApprovalsNeeded: 0`, the dimension fails.

This is the highest-priority config finding because unreviewed code merges
are a direct integrity attack vector — malicious code can enter the
codebase without any human review.

### Step 3: KMS encryption evaluation

Check `kmsEncryptionKeyId` in the repository metadata:

- **`kmsEncryptionKeyId` is `aws/codecommit`, null, or absent** →
  **NO_ENCRYPTION** finding. The repo uses the AWS-managed default key.
  You have no control over the key policy, no ability to enable/disable
  rotation independently (AWS manages it), and no ability to restrict
  which repos the key encrypts. The key is shared across ALL repos in
  the account/region.
- **`kmsEncryptionKeyId` is a customer-managed key ARN** → OK for this
  dimension. The CMK gives you control over key policy, rotation
  schedule, and cross-account access. Verify the CMK has rotation
  enabled (delegate to `kms-key-policy-auditor` for the key policy audit).
- **CMK with `EnableKeyRotation: false`** → note as an additive finding
  (HIGH, but does not change the verdict — the CMK itself is the
  improvement over the AWS-managed key). Recommend enabling rotation.

Note: "NO_ENCRYPTION" does NOT mean data is unencrypted — CodeCommit
ALWAYS encrypts at rest. It means there is no customer-managed
encryption. The AWS-managed key provides encryption but no customer
control. This distinction is critical for accurate reporting.

### Step 4: Default branch + deletion protection

Check the default branch configuration and IAM branch-protection policies:

- **Default branch is null or points to a non-existent branch** →
  **CONFIG_GAP** finding. The repository is in a broken state — clones
  fail, CI/CD pipelines cannot resolve the default branch.
- **Default branch exists but no IAM Deny policy protects it from
  deletion** → **CONFIG_GAP** finding. Any principal with
  `codecommit:DeleteBranch` on the repo can delete the default branch,
  breaking all clones and pipelines. Unlike GitHub, there is no
  repo-level "protect branch" toggle.
- **IAM Deny policy exists for `codecommit:DeleteBranch` on
  `refs/heads/<default>` → OK for this dimension. Branch deletion is
  blocked at the IAM layer.

### Step 5: Notification rules

Check for CodeStar Notification rules on the repository:

- **No notification rules** → **CONFIG_GAP** finding. Without
  notification rules, there is no automated alerting on repository
  events (PR created, branch deleted, direct push to default branch).
  A stealthy attacker pushing malicious code triggers zero alerts.
- **Notification rules exist** → OK for this dimension. Verify the rules
  target an active SNS topic with valid subscribers (not a dead topic).
- **Notification rules exist but target a deleted/disconnected SNS topic**
  → **CONFIG_GAP** finding. The rules are decorative — events are
  generated but not delivered.

### Step 6: Aggregation — worst finding wins

The final verdict is the **highest-priority** finding, where:

```
NO_APPROVAL_RULE > NO_ENCRYPTION > CONFIG_GAP > DEPRECATION_RISK > OK
```

```text
if approval_rule_finding == FAIL:
    verdict = NO_APPROVAL_RULE
elif encryption_finding == FAIL:
    verdict = NO_ENCRYPTION
elif branch_protection_finding == FAIL or notification_finding == FAIL:
    verdict = CONFIG_GAP
elif migration_acknowledged == False:
    verdict = DEPRECATION_RISK
else:
    verdict = OK
```

The deprecation finding is ALWAYS included in FINDINGS regardless of the
verdict — it is never suppressed.

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

## Edge-case handling

- **Repository with no policy document.** A CodeCommit repo without a
  resource-based policy is NOT a security gap — access defaults to
  IAM-only. Do not flag the absence of a repository policy as a finding.

- **Approval rule template linked but repository name uses a wildcard
  pattern.** Templates can be linked to all repos (`*`) or specific names.
  A template linked via wildcard pattern covers the repo. Verify the
  pattern actually matches (e.g., `my-app-*` matches `my-app-backend`
  but not `backend-my-app`).

- **Multiple CONFIG_GAP findings (no notifications AND no branch
  protection).** The verdict is still CONFIG_GAP — both findings are
  enumerated in FINDINGS, but the verdict does not escalate. CONFIG_GAP
  represents any operational gap; multiple gaps compound the remediation
  scope but not the verdict label.

- **Repository in a deleted state.** If `repositoryDescription` shows
  deletion in progress, output `VERDICT: DEPRECATION_RISK, REASON:
  Repository is being deleted — no action required.`

## Anti-Patterns — NEVER

- NEVER omit the DEPRECATION_RISK finding from any CodeCommit audit.
  Even a perfectly configured repo carries the deprecation risk. An audit
  that does not mention deprecation is incomplete and misleading — it
  implies the service is a viable long-term platform, which it is not.

- NEVER report "NO_ENCRYPTION" as "data is unencrypted." CodeCommit
  ALWAYS encrypts at rest. The finding means no customer-managed
  encryption key — the AWS-managed key is in use. Conflating "no CMK"
  with "no encryption" causes unnecessary panic and erodes trust in the
  audit.

- NEVER claim that the KMS key can be rotated or changed after repository
  creation. The `kmsEncryptionKeyId` is IMMUTABLE — there is no
  `update-repository-encryption` API. Remediation requires creating a new
  CMK-backed repository and migrating all history, CI/CD, and developer
  remotes. Do not suggest `aws codecommit update-*` for encryption.

- NEVER assert that CodeCommit has native branch-protection rules.
  CodeCommit does NOT have a "protect branch" API or setting. Branch
  protection is enforced entirely via IAM Deny policies on
  `codecommit:DeleteBranch` and `codecommit:GitPush` with
  `codecommit:References` conditions. Claiming a native feature exists
  causes the operator to look for a non-existent setting.

- NEVER treat `numberOfApprovalsNeeded: 0` as an effective approval rule.
  A template with zero required approvals provides NO enforcement — PRs
  are mergeable without any review. This is functionally identical to
  having no template at all.

- NEVER query only `aws codecommit` APIs for notification rules.
  Notification rules are managed by AWS CodeStar Notifications
  (`aws codestar-notifications`), a separate service. A CodeCommit-only
  query returns zero results even when notification rules exist. This is
  the most common audit blind spot.

- NEVER recommend creating a new CodeCommit repository as a long-term
  remediation without flagging the deprecation risk. Creating a new repo
  to add CMK encryption perpetuates dependence on a deprecated service.
  The correct long-term remediation is migration to GitHub/GitLab.

- NEVER assume `codecommit:References` accepts bare branch names. The
  condition key requires the full ref path: `refs/heads/main`, not
  `main`. An IAM policy using the bare name silently fails to match and
  provides zero protection.

- NEVER skip checking IAM policies for branch protection. CodeCommit APIs
  cannot reveal which IAM policies protect branches — this is a
  cross-service audit requiring `iam:ListRolePolicies` and
  `iam:GetRolePolicy`. An audit that only checks CodeCommit config will
  miss the absence of branch protection.

- NEVER classify a repository with both NO_APPROVAL_RULE and NO_ENCRYPTION
  as anything other than NO_APPROVAL_RULE. The priority ordering
  (NO_APPROVAL_RULE > NO_ENCRYPTION) ensures the most direct security
  risk (unreviewed code merges) is the headline verdict, with encryption
  noted as a secondary finding.

- NEVER assume the default branch is always `main`. CodeCommit repos
  created before ~2020 default to `master`; migrated repos may use
  `develop`, `trunk`, or custom names. Always read `defaultBranch` from
  the repository metadata. IAM branch-protection policies hardcoded to
  `refs/heads/main` provide zero protection when the default branch is
  `master` — the most common branch-protection audit false negative.

- NEVER assume an approval rule template covers the repository just
  because a template exists in the account. Templates are linked by
  repository name or wildcard pattern. A template linked to `my-app-*`
  does NOT cover `backend-my-app`. Verify the actual name match before
  classifying the approval-rule dimension as OK.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (create-approval-rule-template, associate-with-repositories,
  update-default-branch, delete-repository), the auditor MUST emit:
  `CONFIRM: About to <action> on repository <name> in account <account>.
  This affects <consequence>. Proceed? (yes/no)`
- **Approval rule template creation is additive and safe** — it does not
  block existing PRs retroactively, only new PRs created after the
  template is linked. Existing open PRs remain unprotected until closed.
- **Default-branch change is disruptive.** `aws codecommit
  update-default-branch` changes what all clones check out. Warn the
  operator that CI/CD pipelines referencing the old default branch name
  will need updating.
- **Repository deletion is irreversible.** `aws codecommit
  delete-repository` permanently removes the repo after a 7-day
  retention window (recoverable via `undo-delete-repository` only within
  that window). Always snapshot before deletion.
- **IAM policy changes affect all principals.** Adding a Deny policy for
  branch protection may unintentionally block legitimate admin roles.
  Always scope Deny statements to specific role ARNs, not
  `Principal: "*"`.

## Remediation guidance

### For NO_APPROVAL_RULE — create and link an approval rule template

1. Create an approval rule template requiring at least 1 approval:
   ```bash
   aws codecommit create-approval-rule-template \
     --approval-rule-template-name require-1-approval \
     --approval-rule-template-content '{"Version":"2018-02-08","Statements":[{"Type":"Approvers","NumberOfApprovalsNeeded":1}]}'
   ```
2. Link the template to the repository:
   ```bash
   aws codecommit batch-associate-approval-rule-template-with-repositories \
     --approval-rule-template-name require-1-approval \
     --repository-names <repo-name>
   ```
3. Verify the link:
   ```bash
   aws codecommit list-approval-rule-templates
   ```
4. Note: existing open PRs are NOT retroactively protected. Close and
   reopen them to apply the new rule.

### For NO_ENCRYPTION — plan repository migration to CMK-backed repo

The KMS key is immutable post-creation. The only remediation path:

1. Create a new repository with a customer-managed KMS key:
   ```bash
   aws codecommit create-repository \
     --repository-name <repo-name>-cmk \
     --kms-key-id arn:aws:kms:<region>:<account>:key/<cmk-id>
   ```
2. Migrate all branches and tags:
   ```bash
   git remote add new-origin https://git-codecommit.<region>.amazonaws.com/v1/repos/<repo-name>-cmk
   git push new-origin --all && git push new-origin --tags
   ```
3. Update CI/CD pipelines and developer remotes to the new repository.
4. Delete the old repository after verifying the migration.

Note: Given CodeCommit's deprecation, evaluate migrating to GitHub/GitLab
instead of creating a new CodeCommit repo.

### For CONFIG_GAP — branch protection (IAM enforced)

1. Create an IAM Deny policy preventing default-branch deletion:
   ```bash
   aws iam put-role-policy --role-name <developer-role> \
     --policy-name deny-delete-default-branch \
     --policy-document '{
       "Version": "2012-10-17",
       "Statement": [{
         "Effect": "Deny",
         "Action": ["codecommit:DeleteBranch", "codecommit:GitPush"],
         "Resource": "arn:aws:codecommit:<region>:<account>:<repo>",
         "Condition": {"StringEqualsIfExists": {"codecommit:References": ["refs/heads/main"]}}
       }]
     }'
   ```
   Note: use `refs/heads/<branch>`, not the bare branch name. Scope the
   policy to developer-level roles only — do NOT attach to admin/break-glass
   roles that need deletion capability during incident response.

### For CONFIG_GAP — notification rules (CodeStar Notifications)

1. Create an SNS topic for repo alerts:
   ```bash
   aws sns create-topic --name codecommit-alerts
   ```
2. Create a notification rule:
   ```bash
   aws codestar-notifications create-notification-rule \
     --name codecommit-pr-alerts \
     --resource arn:aws:codecommit:<region>:<account>:<repo> \
     --event-type-ids codecommit-pull-request-created codecommit-pull-request-merged \
     --target Type=SNS,TargetArn=arn:aws:sns:<region>:<account>:codecommit-alerts
   ```
3. Subscribe the team email/Slack:
   ```bash
   aws sns subscribe --topic-arn arn:aws:sns:<region>:<account>:codecommit-alerts \
     --protocol email --notification-endpoint team@example.com
   ```

### For DEPRECATION_RISK — migration planning

1. Tag the repository with a migration plan:
   ```bash
   aws codecommit tag-resource \
     --resource-arn arn:aws:codecommit:<region>:<account>:<repo> \
     --tags migration-plan=active,migration-target=github
   ```
2. Evaluate migration tools:
   - `git clone --mirror` the CodeCommit repo
   - Push to GitHub/GitLab remote
   - Update CI/CD and developer remotes
3. After migration, delete the CodeCommit repository to reduce attack
   surface and stop paying for unused storage.

### For OK

1. No config remediation required.
2. The DEPRECATION_RISK finding is still present — continue migration
   planning. An OK verdict means the config is sound, not that the
   service is a viable long-term platform.

## Deep reference: CodeCommit branch-protection vs. GitHub

### Why CodeCommit branch protection is IAM-only

GitHub provides repo-level `protection_rules` via the API — a single
`PUT /repos/{owner}/{repo}/branches/{branch}/protection` call protects
a branch. CodeCommit has no equivalent. The enforcement layer is IAM:

1. A Deny policy on `codecommit:DeleteBranch` prevents branch deletion.
2. A Deny policy on `codecommit:GitPush` with `codecommit:References`
   condition prevents direct pushes to protected branches.
3. Approval rule templates prevent merging PRs without review.

This means branch protection in CodeCommit is distributed across IAM
(identity-based policies) and CodeCommit (approval rules). An auditor
must check BOTH layers — neither alone provides complete protection.

### IAM enumeration procedure for branch protection

There is no single API to determine "which IAM policies protect this
branch." The auditor must perform a cross-service scan:

1. Enumerate all IAM roles: `aws iam list-roles` (paginated, 100/page).
2. For each role, list attached managed policies:
   `aws iam list-attached-role-policies --role-name <name>`.
3. For each role, list inline policies:
   `aws iam list-role-policies --role-name <name>`.
4. Retrieve each policy document (managed: `aws iam get-policy-version`;
   inline: `aws iam get-role-policy`).
5. Scan each document for `Effect: Deny` on `codecommit:DeleteBranch`
   or `codecommit:GitPush` with a `codecommit:References` condition
   matching `refs/heads/<default-branch>`.
6. If at least one Deny policy exists matching the repo ARN and default
   branch ref, the branch is protected. Otherwise, it is unprotected.

This is an O(roles x policies) scan. Cache results when auditing multiple
repos in the same account — the policy documents do not change between
repos (only the repo ARN match changes). Rate-limit to ~1 req/s to avoid
`ThrottlingException` on IAM APIs.

### Approval rule template content structure

The `content` field of an approval rule template is a JSON object:

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

Multiple statements are AND-ed — all must be satisfied before merge. An
empty `ApprovalPoolMembers` means any principal with
`codecommit:ApprovePullRequest` can approve.

### CodeStar Notifications event types

Common event-type IDs for CodeCommit notification rules:
- `codecommit-pull-request-created`
- `codecommit-pull-request-updated`
- `codecommit-pull-request-merged`
- `codecommit-branch-created`
- `codecommit-branch-deleted`
- `codecommit-commit-comment`

Without notification rules on at minimum `pull-request-merged` and
`branch-deleted`, critical events go unalerted.

## Domain

AWS CloudOps / Developer Tools Security & CodeCommit Migration Assessment.
