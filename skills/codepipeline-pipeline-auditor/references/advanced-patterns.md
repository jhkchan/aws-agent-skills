# Advanced Patterns — CodePipeline Pipeline Auditor

Load-on-demand deep dives moved verbatim from SKILL.md: Step-0 expert knowledge, edge cases, internals, and recent features.

## Step 0 — Expert knowledge: non-obvious CodePipeline behaviors

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

## Deep reference — CodePipeline internals

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
