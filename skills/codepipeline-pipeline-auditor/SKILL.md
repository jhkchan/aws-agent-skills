---
name: codepipeline-pipeline-auditor
description: >-
  Audits AWS CodePipeline pipelines for artifact-store encryption (KMS CMK
  presence), cross-account or over-permissive action roles, disabled stage
  transitions, source-action credential posture (GitHub v1 OAuth vs CodeStar
  Connection), and manual-approval gate coverage. Emits a deterministic
  verdict (NO_ENCRYPTION | OVERPERMISSIVE_ROLE | DISABLED_STAGE | CONFIG_GAP
  | OK) per pipeline with enumerated findings and CLI remediation. Use when
  reviewing pipeline definitions, checking for unencrypted artifact buckets,
  validating cross-account deployment roles, detecting disabled stages,
  auditing source credential strength, or verifying production approval gates.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline pipeline-definition classification.
  Live-account audits use aws codepipeline get-pipeline, get-pipeline-state,
  list-pipelines, and disable/enable-stage-transition (AWS CLI v2, SSO or
  key-based credentials).
keywords:
  - CodePipeline
  - pipeline audit
  - artifact store
  - KMS encryption
  - cross-account role
  - over-permissive role
  - disabled stage
  - stage transition
  - GitHub v1 source
  - CodeStar Connection
  - manual approval
  - approval gate
  - artifact bucket
  - deployment pipeline
  - CI/CD security
tags: [codepipeline, security, devtools, ci-cd, encryption, cross-account, pipeline, audit]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: DevTools
  verdict_shape: "NO_ENCRYPTION | OVERPERMISSIVE_ROLE | DISABLED_STAGE | CONFIG_GAP | OK"
  when_to_use: >-
    Reviewing a CodePipeline pipeline definition before production deployment,
    checking for unencrypted artifact stores, auditing cross-account deploy
    roles, detecting disabled stage transitions, validating source-action
    credential strength (GitHub v1 vs CodeStar Connection), or verifying
    manual-approval gate coverage.
  activation_triggers:
    - "audit this codepipeline"
    - "is my pipeline artifact store encrypted"
    - "check for disabled stage transitions"
    - "cross-account deploy role in pipeline"
    - "github v1 source deprecated"
    - "missing manual approval gate"
    - "pipeline security audit"
    - "over-permissive pipeline role"
    - "codestar connection check"
  invocation_schema: >-
    Input: either (a) a CodePipeline pipeline definition JSON (from
    get-pipeline), optionally paired with get-pipeline-state output for
    transition status, OR (b) a pipeline name/ARN for live-account audit.
    Output: deterministic PIPELINE/VERDICT/REASON/FINDINGS/REMEDIATION block
    per pipeline, where VERDICT is one of {NO_ENCRYPTION, OVERPERMISSIVE_ROLE,
    DISABLED_STAGE, CONFIG_GAP, OK, ERROR}.
---

# CodePipeline Pipeline Auditor

## Mindset

**One-line takeaway:** the verdict is always the **worst** finding across all
dimensions, and an unencrypted artifact store is the highest-severity finding
because pipeline artifacts frequently contain source code, build outputs,
CloudFormation templates, and embedded secrets — all stored in plaintext S3
objects when no KMS key is configured.

CodePipeline is the orchestration spine of CI/CD. Five audit dimensions matter:

1. **Artifact store encryption** — the S3 bucket that stores stage input/output
   artifacts across every stage. Without a customer-managed KMS key, artifacts
   are only as protected as the bucket's default SSE — which may be nothing.
2. **Action roles** — each deploy action assumes an IAM role (`RoleArn` in
   `configuration`) that determines the blast radius of that deployment. A
   cross-account role widens that blast radius to another AWS account.
3. **Stage transitions** — a disabled transition (`DisableStageTransition`)
   silently blocks all executions from advancing past that stage. It is an
   active operational freeze, not a configuration preference.
4. **Source credentials** — GitHub v1 source actions use a persistent OAuth
   token that grants access to every repository the authorizer owns. CodeStar
   Connections are scoped to specific repositories and rotate automatically.
5. **Manual approval gates** — a production pipeline without an approval gate
   deploys without human verification. An approval gate without an SNS topic
   silently drops notifications — approvers never know they are needed.

## Quick reference — verdict thresholds

| Condition | Verdict | Step |
|---|---|---|
| Artifact store has no `encryptionKey` + bucket SSE is none/SSE-S3 only | **NO_ENCRYPTION** | Step 1 |
| Cross-region: any regional `artifactStores` entry lacks `encryptionKey` | **NO_ENCRYPTION** | Step 1 |
| Any action `configuration.RoleArn` account ID differs from pipeline owner | **OVERPERMISSIVE_ROLE** | Step 2 |
| Pipeline state shows a stage inbound transition `enabled: false` | **DISABLED_STAGE** | Step 3 |
| Source action uses `ThirdParty/GitHub` (v1 OAuth, deprecated) | **CONFIG_GAP** | Step 4 |
| `PollForSourceChanges: false` with no EventBridge trigger | **CONFIG_GAP** | Step 4 |
| Production pipeline (Deploy/Prod stage) with no `ManualApproval` action | **CONFIG_GAP** | Step 5 |
| `ManualApproval` action with no `NotificationArn` | **CONFIG_GAP** | Step 5 |
| CMK encryption + same-account roles + all transitions enabled + secure source + approval gate | **OK** | Step 6 |

See the ordered steps below for edge cases. Deep CodePipeline internals
(cross-region replication, polling quotas, artifact lifecycle) are in the
[Deep reference](#deep-reference-codepipeline-internals) section at the end.

## Pre-flight: pipeline structure validation

Before classifying, verify the pipeline definition is well-formed. Several
structural issues short-circuit the audit:

| Attribute | Effect on audit |
|---|---|
| Missing `pipeline` key | **ERROR** — cannot classify. Emit ERROR block. |
| Missing `stages` or empty stages array | **ERROR** — a pipeline with zero stages is invalid. |
| Missing `artifactStore` AND `artifactStores` | **ERROR** — no artifact storage defined. |
| `artifactStore` present AND `artifactStores` present | Use `artifactStores` (cross-region mode takes precedence). |
| Single stage (Source only, no downstream) | Classify normally — a source-only pipeline is valid but limited. Flag lack of approval as CONFIG_GAP if the pipeline name implies production. |

**If the pipeline definition is malformed** (invalid JSON, missing required
keys), output:

```text
PIPELINE: <name or "unknown">
VERDICT: ERROR
REASON: Pipeline definition is not valid JSON or is missing required fields (pipeline, stages, artifactStore) — cannot classify.
REMEDIATION: Retrieve the canonical definition with `aws codepipeline get-pipeline --name <name> --output json` and re-audit.
```

**Pipeline-state data requirement (Step 3 prerequisite):** the pipeline
definition from `get-pipeline` does NOT contain transition states — only
`get-pipeline-state` does. If the input lacks pipeline-state data, note that
disabled-stage detection is limited: you can flag stages that appear
intentionally frozen from metadata context, but you cannot definitively confirm
a transition is enabled without the state output. Always request
`get-pipeline-state` alongside `get-pipeline` for a complete audit.

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious CodePipeline behaviors

These behaviors are easy to misjudge without operational CodePipeline
experience. Each changes a verdict if ignored:

- **The pipeline service role and action roles are DIFFERENT principals.** The
  `pipeline.roleArn` is assumed by the CodePipeline service
  (`codepipeline.amazonaws.com`) to orchestrate stages, read from S3, and
  invoke action providers. Each action with a `configuration.RoleArn` is
  assumed by that action's service principal (e.g.,
  `cloudformation.amazonaws.com`, `ecs-tasks.amazonaws.com`). Using the same
  role for both creates a trust-policy conflict and widens the blast radius.
  When auditing roles, classify the pipeline role and each action role
  independently.

- **`encryptionKey` absence means the pipeline does NOT manage encryption.**
  When `artifactStore.encryptionKey` is absent, CodePipeline writes artifacts
  to the S3 bucket using the bucket's own SSE settings. If the bucket has no
  SSE configuration, artifacts — which can include source code, build outputs,
  and CloudFormation templates with embedded parameter values — are stored in
  plaintext. This is NO_ENCRYPTION, not CONFIG_GAP.

- **`get-pipeline` does NOT show disabled transitions.** Stage transition
  state is runtime metadata set by `DisableStageTransition`. Only
  `get-pipeline-state` returns `stageStates[].transitionStates[]` with
  `enabled: true/false`. An audit that checks only the pipeline definition
  JSON silently misses every disabled stage. Always pair the two API calls.

- **GitHub v1 (`ThirdParty/GitHub`) source actions are deprecated.** They use
  a persistent OAuth token stored in Secrets Manager. This token grants access
  to every repository owned by the authorizing GitHub user — not just the one
  in the pipeline. If the token is compromised, every repo under that user is
  exposed. CodeStar Connections (`AWS/CodeStarConnection`) are scoped to a
  specific connection ARN and can be restricted to named repositories via the
  connection's host configuration.

- **`PollForSourceChanges: false` without an EventBridge rule means the
  pipeline NEVER auto-triggers.** The pipeline only runs on manual
  `StartPipelineExecution`. This is sometimes intentional (gated releases) but
  is frequently a misconfiguration — the operator set it to false to reduce
  polling costs and forgot to wire up the EventBridge rule. Flag as CONFIG_GAP
  unless the pipeline explicitly has an approval gate (intentional manual
  trigger).

- **`artifactStores` (plural) is cross-region mode.** Each regional store has
  its own `encryptionKey`. A common pattern: the primary region uses a CMK but
  a secondary region's store has no `encryptionKey`. Each region's store is
  audited independently — a gap in any region is NO_ENCRYPTION.

- **Manual approval without `NotificationArn` is a silent gate.** The
  `ManualApproval` action type accepts a `NotificationArn` in its
  `configuration` block. When absent, no SNS notification is sent when
  approval is needed. The pipeline execution sits in `InProgress` indefinitely
  until someone manually checks the console. This is a CONFIG_GAP — the gate
  exists on paper but is invisible to the team.

- **Artifact buckets are NOT lifecycle-managed by CodePipeline.** Artifacts
  accumulate indefinitely. The pipeline definition has no lifecycle policy —
  S3 lifecycle rules must be configured on the bucket separately. Over time,
  stale artifacts can expose old source code or templates long after the
  pipeline that created them has been deleted.

- **The encryptionKey `id` accepts key ARNs, key IDs, and alias ARNs.** Aliases
  are pointers — `alias/prod-pipeline-key` can be remapped to a different
  backing key at any time. A pipeline referencing an alias will silently start
  encrypting with the new key material. For audit determinism, prefer key ARNs
  over alias ARNs; flag alias ARNs as a fragility note (not a verdict
  escalation).

- **Action `RoleArn` in `configuration` is NOT validated against IAM at
  pipeline creation.** CodePipeline accepts any role ARN string. If the role
  does not exist or its trust policy does not include the action's service
  principal, the pipeline fails at execution time with `AccessDenied` — not at
  creation. A cross-account role ARN in the configuration is a signal that
  the pipeline deploys into a different account, which widens the trust
  boundary.

- **CodeBuild project encryption is NOT governed by the pipeline's
  artifactStore key.** CodeBuild build actions reference a project name, and
  that project has its own `encryptionKey` setting. A pipeline with a CMK on
  its artifactStore can still have unencrypted build artifacts if the CodeBuild
  project uses the `NO_ENCRYPTION` flag. A thorough audit cross-references
  `codebuild:BatchGetProjects` — but from the pipeline JSON alone, note this
  as a cross-service gap.

- **Webhook secrets for GitHub v1 are stored in pipeline metadata, not in
  Secrets Manager.** When a GitHub v1 source uses a webhook for change
  detection, the webhook secret is stored in the pipeline's `metadata`
  section. This secret is used to validate incoming webhook payloads but is
  NOT encrypted by the pipeline — it relies on the CodePipeline service's own
  envelope encryption. A compromised pipeline definition exposes the webhook
  secret.

- **`RetryStageExecution` does NOT re-enable a disabled transition.** A
  disabled transition blocks ALL executions, including retries. The transition
  must be explicitly re-enabled with `EnableStageTransition` before any
  execution can advance. Operators sometimes confuse retrying an execution
  with un-blocking a stage.

- **`UpdatePipeline` replaces the entire definition atomically — no diff, no
  rollback.** There is no version history for pipeline definitions. The old
  definition is permanently overwritten. `get-pipeline` before `update-pipeline`
  is the only backup path. An accidental `update-pipeline` with a partial JSON
  (missing stages, missing encryptionKey) silently destroys the working
  definition. Always snapshot before modifying.

- **Artifact encryption is per-pipeline, NOT per-stage.** Every stage in a
  pipeline shares ONE artifact store with ONE encryptionKey. You cannot
  encrypt staging artifacts differently from production artifacts within the
  same pipeline. A single compromised KMS key exposes artifacts across every
  stage boundary — Source output, Build output, Deploy input. There is no
  per-stage encryption isolation.

- **`StartPipelineExecution` accepts `sourceRevisions` — an operator can
  deploy a DIFFERENT commit than what the source action detected.** This
  override parameter lets an operator with `codepipeline:StartPipelineExecution`
  inject a specific source revision (commit SHA) without triggering source
  change detection. This is a supply-chain risk: a compromised operator can
  deploy an arbitrary commit that was never pushed through the normal source
  detection path, bypassing any branch-protection rules on the repository.

- **SUPERSEDED execution mode cancels in-flight runs silently.** By default,
  a new source change supersedes (cancels) the currently running execution.
  If commits arrive faster than the pipeline can complete (e.g., a CI burst),
  an execution may be cancelled moments before its Deploy stage — the team
  sees a "Succeeded" on the latest run but the intermediate deployment never
  shipped. `QUEUE` mode (max 500 queued executions) preserves all runs but
  adds latency.

### Step 1: Artifact store encryption (highest priority — plaintext artifacts)

Check the artifact store configuration for KMS encryption:

**Single-region pipeline (`artifactStore`):**
- If `encryptionKey` field is absent → **NO_ENCRYPTION**. The pipeline does
  not manage encryption; artifacts are UNENCRYPTED at rest (or rely entirely on
  the bucket's default SSE, which may be none). If the input includes bucket
  SSE metadata and it is `none` or SSE-S3 only, this is confirmed NO_ENCRYPTION.
  If bucket metadata is not provided, still flag as NO_ENCRYPTION — the absence
  of `encryptionKey` in the pipeline definition means no customer-managed key
  governs artifact access.
- If `encryptionKey.type` is `"KMS"` and `encryptionKey.id` is present → pass
  (encrypted with a CMK). Note whether the `id` is a bare key ID, key ARN, or
  alias ARN — alias ARNs are fragile (remappable).

**Cross-region pipeline (`artifactStores`):**
- Check EACH regional store independently. If ANY store lacks `encryptionKey`
  → **NO_ENCRYPTION**. A common gap: primary region has a CMK, secondary
  region does not.

**Severity rationale:** artifacts transit the S3 bucket at every stage
boundary. They contain source archives, compiled binaries, CloudFormation/SAM
templates, Terraform state files, and sometimes environment-specific parameter
overrides. Unencrypted artifacts are a data-exfiltration vector via S3 bucket
policy misconfiguration or IAM escalation on the bucket — anyone with
`s3:GetObject` on the artifact bucket can read every pipeline artifact without
ever touching KMS.

### Step 2: Cross-account / over-permissive action roles

Extract the pipeline owning account from `pipeline.roleArn` (the 12-digit
account ID in the ARN). For each action that has a `configuration.RoleArn`
field (typically CloudFormation, ECS, Lambda, S3 deploy, Service Catalog,
and Alex Skills Kit deploy actions):

- If any action `RoleArn` account ID differs from the pipeline owner account →
  **OVERPERMISSIVE_ROLE**. The pipeline deploys into or assumes a CROSS_ACCOUNT
  role in a different AWS account. This is sometimes intentional (hub-and-spoke
  deployment, cross-account CI/CD) but is a privilege-escalation risk: if the
  external account is compromised, the attacker can use the pipeline to deploy
  arbitrary resources via the trusted action role.

- If all action `RoleArn` values are same-account → pass for this dimension.
  Note: the action role's own IAM policy may still be over-permissive (e.g.,
  `AdministratorAccess`), but that requires an IAM policy lookup beyond the
  pipeline JSON. Flag as a note: "Action role IAM policy not auditable from
  pipeline definition — recommend `iam-least-privilege-advisor` on the role."

**Special case — the pipeline service role itself:**
- `pipeline.roleArn` with a trust policy allowing `Principal: "*"` is a
  CRITICAL privilege escalation. However, this trust policy is not visible in
  the pipeline definition — it requires `iam:get-role` on the pipeline role.
  If the input includes the pipeline role's trust policy and it allows `"*"`,
  flag as OVERPERMISSIVE_ROLE regardless of action roles.

### Step 3: Stage transition state (operational freeze)

**Requires `get-pipeline-state` output.** If only the pipeline definition is
available (no state), this step cannot definitively classify — note this as a
limitation and skip to Step 4.

For each stage in the pipeline state (`stageStates`):
- Check `inboundTransitionState.enabled`. If `false` for any stage →
  **DISABLED_STAGE**. The stage name and the disabled transition reason
  (`disabledReason`) should be captured in the findings.
- A disabled transition means the pipeline is operationally frozen at that
  point. No execution can advance past it until `EnableStageTransition` is
  called. This may be intentional (production freeze, incident lockdown) or
  accidental (operator forgot to re-enable).

**Expert note:** `DisableStageTransition` does NOT stop in-flight executions
already running in the disabled stage — it only blocks NEW executions from
entering. An execution already in progress when the transition is disabled
will complete normally.

### Step 4: Source action credential posture

For each action with `actionTypeId.category: "Source"`:

| Provider | Owner | Credential model | Verdict impact |
|---|---|---|---|
| `CodeStarConnection` | `AWS` | Scoped connection ARN, auto-rotated, repository-restrictable | Pass (secure) |
| `CodeCommit` | `AWS` | IAM-native (uses pipeline role credentials) | Pass (secure) |
| `S3` | `AWS` | Uses pipeline role to read bucket | Pass, but check bucket exposure separately |
| `GitHub` | `ThirdParty` | Persistent OAuth token in Secrets Manager; grants access to ALL repos under the authorizing user | **CONFIG_GAP** (DEPRECATED, credential-exposure vector) |
| `GitLab` / `Bitbucket` (self-managed) | `ThirdParty` | Varies — typically personal access token | **CONFIG_GAP** (DEPRECATED, same pattern as GitHub v1) |

If any source action uses `ThirdParty/GitHub` (v1) → **CONFIG_GAP**. The v1
integration is DEPRECATED by AWS and should be migrated to CodeStar Connections.

**Polling vs event trigger:**
- `PollForSourceChanges: true` → the pipeline polls the source every 60
  seconds. This works but generates excess API calls and has higher latency
  than event-based detection.
- `PollForSourceChanges: false` with no EventBridge rule configured →
  **CONFIG_GAP**. The pipeline will never auto-trigger. If this is paired
  with a ManualApproval gate downstream, it may be intentional (gated
  releases) — downgrade to a note instead of a finding. If there is no
  approval gate and `PollForSourceChanges: false`, flag as CONFIG_GAP (the
  pipeline silently stops reacting to source changes).

### Step 5: Manual approval gate coverage

Check for `ManualApproval` actions in the pipeline:

- **No `ManualApproval` action found AND the pipeline has a Deploy/Prod stage**
  → **CONFIG_GAP**. A production deployment pipeline without a human approval
  gate deploys automatically on every source change. This is risky for
  production environments where a faulty commit can cause an outage.
  Heuristic for "production pipeline": any stage name containing "Deploy",
  "Prod", "Release", "Production", or any action with `category: "Deploy"`.

- **`ManualApproval` action found but `configuration.NotificationArn` is
  absent or empty** → **CONFIG_GAP**. The approval gate exists but no SNS
  notification is sent. Approvers are never alerted — the pipeline sits in
  `InProgress` until someone manually checks the console.

- **`ManualApproval` action found with a valid `NotificationArn`** → pass.
  The approval gate is properly wired.

### Step 6: Aggregation — worst finding wins

The final verdict is the **maximum severity** across all findings, where:

```
NO_ENCRYPTION > OVERPERMISSIVE_ROLE > DISABLED_STAGE > CONFIG_GAP > OK
```

```text
verdict = max(all_finding_verdicts)
```

If no findings (all dimensions pass), the verdict is **OK**.

## Output format (per pipeline)

```text
PIPELINE: <pipeline-name>
VERDICT: NO_ENCRYPTION | OVERPERMISSIVE_ROLE | DISABLED_STAGE | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its step number>
FINDINGS:
  - [NO_ENCRYPTION] <finding description (Step N)>
  - [CONFIG_GAP] <finding description (Step N)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

**FINDINGS keyword convention:** each finding description MUST include the
uppercase concept keyword for the finding category — `UNENCRYPTED` for
artifact-store encryption gaps, `CROSS_ACCOUNT` for cross-account roles,
`DISABLED` for disabled transitions, `DEPRECATED` for GitHub v1 / legacy
source credentials. This enables deterministic search and alerting on
finding categories across pipeline fleets.

### Worked example — unencrypted artifacts with deprecated source

```text
PIPELINE: prod-deploy-pipeline
VERDICT: NO_ENCRYPTION
REASON: Artifact store has no encryptionKey — pipeline artifacts (source code,
build outputs, templates) are UNENCRYPTED at rest without a customer-managed KMS
key (Step 1). Source also uses DEPRECATED GitHub v1 OAuth credentials (Step 4).
FINDINGS:
  - [NO_ENCRYPTION] artifactStore.encryptionKey is absent; artifacts are UNENCRYPTED at rest (Step 1)
  - [CONFIG_GAP] Source action uses ThirdParty/GitHub (v1) — DEPRECATED OAuth token model (Step 4)
REMEDIATION:
  1. Add a customer-managed KMS key to the artifact store:
     aws codepipeline update-pipeline --cli-input-json file://pipeline-with-cmk.json
  2. Migrate the GitHub source to CodeStar Connection:
     aws codestar-connections create-connection --connection-type GH --name prod-gh-connection
     Then update the source action provider to CodeStarConnection.
```

## Edge-case handling

- **Partially malformed pipeline definition.** If the JSON parses but
  individual stages are missing required fields (`name`, `actions`), classify
  each valid stage normally and emit an ERROR note for malformed stages. Do NOT
  silently classify the entire pipeline as ERROR when only one stage is broken.

- **Cross-region pipeline with mixed encryption.** A pipeline with
  `artifactStores` where us-east-1 has a CMK but eu-west-1 does not is
  NO_ENCRYPTION — the unencrypted regional store exposes all artifacts staged
  for cross-region actions in that region.

- **Source-only pipeline (single stage).** A pipeline with only a Source stage
  and no downstream stages is valid (used for artifact export). Classify
  normally — encryption and source credential checks still apply. Missing
  approval is NOT flagged (there is nothing to approve).

- **Multiple deploy actions with different role ARNs.** If one action uses a
  same-account role and another uses a cross-account role, the verdict is
  OVERPERMISSIVE_ROLE — the widest role determines the blast radius.

- **Manual approval in a non-production pipeline.** If the pipeline name or
  stage names do not imply production (e.g., "dev-test-pipeline"), a missing
  approval gate is NOT a CONFIG_GAP — development pipelines may intentionally
  auto-deploy. Only flag when production context is present.

## Anti-Patterns — NEVER

- NEVER classify a pipeline with no `encryptionKey` as OK or CONFIG_GAP. The
  absence of a customer-managed KMS key means artifacts are stored without
  KMS-managed access control — anyone with S3 access to the bucket can read
  every artifact without touching KMS. This is NO_ENCRYPTION.

- NEVER confuse the pipeline service role (`pipeline.roleArn`) with action
  roles (`configuration.RoleArn` inside actions). The pipeline role
  orchestrates; action roles deploy. An over-permissive pipeline role can
  modify the pipeline itself; an over-permissive action role can create or
  destroy any resource the action supports. Audit both, but classify
  OVERPERMISSIVE_ROLE based on action roles (they have the deployment blast
  radius).

- NEVER assume a disabled stage transition is visible in the pipeline
  definition JSON. `get-pipeline` does NOT return transition states — only
  `get-pipeline-state` does. An audit that checks only the definition
  silently misses every disabled transition.

- NEVER treat GitHub v1 (`ThirdParty/GitHub`) as equivalent to CodeStar
  Connection. The v1 integration uses a persistent OAuth token that grants
  access to every repository under the authorizing user. CodeStar Connections
  are scoped and auto-rotated. v1 is deprecated — always flag it as
  CONFIG_GAP.

- NEVER recommend removing a ManualApproval gate as remediation. The gate is
  a safety control — the fix for a missing notification is to add an SNS
  topic, not to remove the gate. Removing the gate silently makes the pipeline
  auto-deploy without approval.

- NEVER assume `PollForSourceChanges: false` is always a misconfiguration. If
  the pipeline has a ManualApproval gate downstream, disabling polling may be
  intentional (operator-triggered gated releases). Only flag as CONFIG_GAP
  when there is no approval gate AND no EventBridge trigger configured.

- NEVER overlook cross-region artifact stores. A pipeline with `artifactStores`
  (plural) has independent stores per region. Auditing only the primary
  region's store misses encryption gaps in secondary regions where
  cross-region deploy actions stage their artifacts.

- NEVER classify a same-account-only pipeline with a CMK, secure source, and
  approval gate as anything other than OK. Same-account action roles are
  governed by IAM policies (a second authorization layer). The pipeline
  definition alone does not show over-permission unless the role is
  cross-account.

- NEVER recommend deleting a pipeline as remediation without first verifying
  no production workloads depend on it. `DeletePipeline` is irreversible — the
  entire definition, including stage configurations and artifact history, is
  permanently removed.

- NEVER assume the artifact bucket policy is managed by CodePipeline. The
  customer creates and manages the bucket policy independently. A pipeline
  with a CMK can still have artifacts exposed via a permissive bucket policy
  that grants `s3:GetObject` to `"*"`. Note this as a cross-service gap.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`UpdatePipeline`, `DisableStageTransition`, `EnableStageTransition`,
  `DeletePipeline`), the auditor MUST emit:
  `CONFIRM: About to <action> on pipeline <name> in account <account>. This
  affects <consequence>. Proceed? (yes/no)`
  Do NOT execute the CLI command until the operator confirms.

- **Snapshot the pipeline before modification.** Capture the current
  definition for rollback:
  `aws codepipeline get-pipeline --name <name> --output json > /tmp/<name>-backup-$(date +%s).json`
  Pipeline definitions are not versioned — `UpdatePipeline` replaces the entire
  structure atomically with no undo.

- **Verify the pipeline exists and is accessible:**
  `aws codepipeline get-pipeline --name <name>` — fail closed (skip
  remediation) if it returns an error.

- **Before enabling a disabled transition**, confirm the operator understands
  that enabling the transition allows queued executions to advance
  immediately. If the stage was disabled during an incident, verify the
  incident is resolved before re-enabling.

- **Before adding a CMK to the artifact store**, verify the pipeline role has
  `kms:Encrypt`, `kms:Decrypt`, and `kms:GenerateDataKey` on the new key.
  Adding an encryptionKey without granting the pipeline role KMS permissions
  causes all executions to fail with `AccessDenied` at the first artifact
  staging step.

- Prefer additive changes (add an approval stage, add a CMK) over destructive
  changes (remove a stage, delete a pipeline) — additive changes are
  reversible and do not risk breaking existing deployment workflows.

## Remediation guidance

### For NO_ENCRYPTION — artifact store without CMK

1. Create or identify a customer-managed KMS key in the pipeline's region:
   `aws kms create-key --description "CodePipeline artifact encryption" --profile <p>`
2. Grant the pipeline service role KMS permissions:
   `kms:Encrypt`, `kms:Decrypt`, `kms:ReEncrypt*`, `kms:GenerateDataKey*`,
   `kms:DescribeKey` on the new key.
3. Update the pipeline definition to include the `encryptionKey`:
   ```json
   "artifactStore": {
     "type": "S3",
     "location": "<bucket-name>",
     "encryptionKey": {
       "id": "<key-arn>",
       "type": "KMS"
     }
   }
   ```
4. Apply: `aws codepipeline update-pipeline --cli-input-json file://updated-pipeline.json`
5. For cross-region pipelines, repeat for each regional `artifactStores` entry.
6. Enable key rotation: `aws kms enable-key-rotation --key-id <key-id>`

### For OVERPERMISSIVE_ROLE — cross-account action role

1. Determine if the cross-account deployment is intentional. If it is a
   hub-and-spoke or cross-account CI/CD pattern, document the trust
   relationship and add an `ExternalId` condition to the action role's trust
   policy.
2. If the cross-account role is NOT intentional, update the action's
   `configuration.RoleArn` to a same-account role:
   `aws codepipeline update-pipeline --cli-input-json file://fixed-pipeline.json`
3. Audit the cross-account role's IAM policy using
   `iam-least-privilege-advisor` to verify it does not grant
   `AdministratorAccess` or wildcard permissions.

### For DISABLED_STAGE — disabled stage transition

1. Verify the reason for the disabled transition:
   `aws codepipeline get-pipeline-state --name <name>` — check
   `inboundTransitionState.disabledReason`.
2. If the freeze is no longer needed:
   `aws codepipeline enable-stage-transition --name <pipeline> --stage-name <stage> --transition-type Inbound`
3. If the freeze is intentional (incident lockdown), document it and add a
   calendar reminder to review — disabled transitions are frequently forgotten
   and left in place long after the incident resolves.

### For CONFIG_GAP — deprecated source credentials

1. Create a CodeStar Connection:
   `aws codestar-connections create-connection --connection-type GH --name <name> --providers-type GitHub`
2. Complete the connection handshake in the AWS Console (OAuth against GitHub,
   scope to specific repositories).
3. Update the source action in the pipeline definition:
   - Change `owner` from `ThirdParty` to `AWS`
   - Change `provider` from `GitHub` to `CodeStarConnection`
   - Replace `Owner`/`Repo`/`Branch` configuration with `ConnectionArn`,
     `FullRepositoryId`, `BranchName`
4. Apply: `aws codepipeline update-pipeline --cli-input-json file://updated-pipeline.json`

### For CONFIG_GAP — missing manual approval gate

1. Add a `ManualApproval` action before the Deploy stage:
   ```json
   {
     "name": "Approval",
     "actionTypeId": {
       "category": "Approval",
       "owner": "AWS",
       "provider": "Manual",
       "version": "1"
     },
     "configuration": {
       "NotificationArn": "arn:aws:sns:us-east-1:<account>:pipeline-approval",
       "CustomData": "Review and approve production deployment"
     }
   }
   ```
2. Create the SNS topic and subscribe the deployment team:
   `aws sns create-topic --name pipeline-approval`
   `aws sns subscribe --topic-arn <arn> --protocol email --notification-endpoint <team-email>`

### For OK

1. No remediation required for the current posture.
2. Recommend auditing the artifact bucket policy separately for public access.
3. Recommend verifying the pipeline role's IAM policy is least-privilege.
4. For cross-region pipelines, verify each regional KMS key has rotation
   enabled.

## Deep reference: CodePipeline internals

### Cross-region action replication

When a pipeline includes actions in a different region than the pipeline's
home region, CodePipeline uses cross-region replication. The pipeline must
define `artifactStores` (plural) mapping each region to its own S3 bucket and
optional encryption key. Cross-region actions reference their region via the
action's `region` field. CodePipeline automatically copies artifacts between
regional stores — each copy is encrypted/decrypted independently with that
store's key (if present). An unencrypted regional store exposes all artifacts
for actions in that region.

### Polling quotas and EventBridge

CodePipeline polling (`PollForSourceChanges: true`) calls the source provider
approximately every 60 seconds. For CodeCommit, this counts against the
`codecommit:GitPull` rate limit. For GitHub v1, it counts against the GitHub
API rate limit (5,000 requests/hour per token). EventBridge-based detection
eliminates polling entirely — the source provider pushes a change event, and
EventBridge triggers `StartPipelineExecution` with minimal latency. AWS
recommends EventBridge for all source types. Setting
`PollForSourceChanges: false` without setting up EventBridge means the
pipeline only runs on manual trigger.

### Pipeline definition vs pipeline state

Two API calls are needed for a complete audit:
- `get-pipeline` returns the pipeline **definition** — the static structure
  (stages, actions, artifactStore, roleArn). This is what you modify with
  `update-pipeline`.
- `get-pipeline-state` returns the **runtime state** — current execution
  status per stage, transition enabled/disabled state, and latest execution
  ID. This is what you check for disabled transitions and execution health.

An audit that checks only the definition misses: disabled transitions,
in-flight execution status, and per-stage retry counts. Always pair both calls.

### Artifact lifecycle and S3 interaction

Pipeline artifacts are stored in the artifact S3 bucket under the key pattern
`<pipeline-name>/<artifact-name>`. Each stage transition creates a new set of
artifact objects. CodePipeline does NOT delete old artifacts — they accumulate
indefinitely. The customer must configure S3 lifecycle rules on the bucket to
transition old artifacts to cheaper storage tiers or expire them. A pipeline
that runs 50 times/day generates ~100+ artifact objects daily — without
lifecycle rules, the bucket grows without bound.

## Recent AWS features (2024-2026)

- **CodePipeline V2 (2024-2025):** V2 pipelines introduce triggers (Git-based, scheduled), pipeline-level variables, and stage-level execution modes. Auditors should verify that V2 pipelines use triggers scoped to specific branches (not wildcard) and that pipeline variables do not leak secrets in plaintext.
- **CodePipeline.compute / EC2 runner (2025):** CodePipeline can now provision EC2 runners for action execution (similar to GitHub Actions self-hosted runners). Auditors should verify that the runner IAM role and VPC configuration are scoped appropriately.
- **Cross-account actions with IAM role chaining:** Enhanced cross-account deployment support. Auditors should verify that cross-account action roles have ExternalId conditions and are not wildcard-principal.

## Domain

AWS CloudOps / CodePipeline CI/CD Security & Compliance.

## AWS documentation

- **AWS CodePipeline User Guide** — https://docs.aws.amazon.com/codepipeline/latest/userguide/welcome.html
- **CodePipeline API Reference (v2)** — https://docs.aws.amazon.com/codepipeline/latest/APIReference/
- **CodePipeline V2 type** — https://docs.aws.amazon.com/codepipeline/latest/userguide/pipeline-types.html
- **CodePipeline Security** — https://docs.aws.amazon.com/codepipeline/latest/userguide/security.html
- **AWS CLI CodePipeline reference** — https://docs.aws.amazon.com/cli/latest/reference/codepipeline/
