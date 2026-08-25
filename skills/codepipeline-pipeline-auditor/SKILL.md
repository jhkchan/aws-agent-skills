---
name: codepipeline-pipeline-auditor
description: Audits AWS CodePipeline pipelines for artifact-store encryption (KMS CMK presence), cross-account or over-permissive action roles, disabled stage transitions, source-action credential posture (GitHub v1 OAuth vs CodeStar Connection), and manual-approval gate coverage. Emits a deterministic verdict (NO_ENCRYPTION | OVERPERMISSIVE_ROLE | DISABLED_STAGE | CONFIG_GAP | OK) per pipeline with enumerated findings and CLI remediation. Use when reviewing pipeline definitions, checking for unencrypted artifact buckets, validating cross-account deployment roles, detecting disabled stages, auditing source credential strength, or verifying production approval gates.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline pipeline-definition classification. Live-account audits use aws codepipeline get-pipeline, get-pipeline-state, list-pipelines, and disable/enable-stage-transition (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: DevTools
  verdict_shape: NO_ENCRYPTION | OVERPERMISSIVE_ROLE | DISABLED_STAGE | CONFIG_GAP | OK
  when_to_use: Reviewing a CodePipeline pipeline definition before production deployment, checking for unencrypted artifact stores, auditing cross-account deploy roles, detecting disabled stage transitions, validating source-action credential strength (GitHub v1 vs CodeStar Connection), or verifying manual-approval gate coverage.
  activation_triggers: audit this codepipeline, is my pipeline artifact store encrypted, check for disabled stage transitions, cross-account deploy role in pipeline, github v1 source deprecated, missing manual approval gate, pipeline security audit, over-permissive pipeline role, codestar connection check
  invocation_schema: 'Input: either (a) a CodePipeline pipeline definition JSON (from get-pipeline), optionally paired with get-pipeline-state output for transition status, OR (b) a pipeline name/ARN for live-account audit. Output: deterministic PIPELINE/VERDICT/REASON/FINDINGS/REMEDIATION block per pipeline, where VERDICT is one of {NO_ENCRYPTION, OVERPERMISSIVE_ROLE, DISABLED_STAGE, CONFIG_GAP, OK, ERROR}.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: CodePipeline, pipeline audit, artifact store, KMS encryption, cross-account role, over-permissive role, disabled stage, stage transition, GitHub v1 source, CodeStar Connection, manual approval, approval gate, artifact bucket, deployment pipeline, CI/CD security
  tags: codepipeline, security, devtools, ci-cd, encryption, cross-account, pipeline, audit
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

All sixteen non-obvious behaviors (service vs action roles, encryptionKey absence, get-pipeline transition blind spot, GitHub v1 deprecation, polling without EventBridge, cross-region artifactStores, silent approval gates, artifact lifecycle, alias ARN fragility, unvalidated RoleArns, CodeBuild project keys, webhook secrets, retry vs re-enable, UpdatePipeline atomicity, per-pipeline encryption, sourceRevisions override, SUPERSEDED mode): [Advanced patterns](references/advanced-patterns.md).

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

Edge cases (partially malformed definition, mixed cross-region encryption, source-only pipelines, mixed role ARNs, non-production approval): [Advanced patterns](references/advanced-patterns.md).

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

Confirmation gate, snapshot, fail-closed verification, transition re-enable caution, CMK role permissions, additive-change preference: [Diagnostic commands](references/diagnostic-commands.md).

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

Cross-region replication, polling quotas, definition-vs-state, artifact lifecycle: [Advanced patterns](references/advanced-patterns.md).

## Recent AWS features (2024-2026)

Recent features — V2 pipelines, EC2 runners, cross-account role chaining: [Advanced patterns](references/advanced-patterns.md).

## References (load on demand)

- [Advanced patterns](references/advanced-patterns.md) — Step-0 expert knowledge, edge-case catalog, CodePipeline internals, recent features
- [Diagnostic commands](references/diagnostic-commands.md) — remediation pre-flight safety checks and snapshot commands

## Domain

AWS CloudOps / CodePipeline CI/CD Security & Compliance.

## AWS documentation

- **AWS CodePipeline User Guide** — https://docs.aws.amazon.com/codepipeline/latest/userguide/welcome.html
- **CodePipeline API Reference (v2)** — https://docs.aws.amazon.com/codepipeline/latest/APIReference/
- **CodePipeline V2 type** — https://docs.aws.amazon.com/codepipeline/latest/userguide/pipeline-types.html
- **CodePipeline Security** — https://docs.aws.amazon.com/codepipeline/latest/userguide/security.html
- **AWS CLI CodePipeline reference** — https://docs.aws.amazon.com/cli/latest/reference/codepipeline/
