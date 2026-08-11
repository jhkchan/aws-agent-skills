# Triggers and Namespace Variables Reference (CodePipeline V2)

Supplementary reference for the CodePipeline V2 Deployer skill. Use
when designing event-driven trigger filters, wiring namespace
variables between stages, configuring stage-level conditions, or
migrating from V1 polling / CloudWatch Events rules.

## V2 trigger anatomy

A V2 trigger is a JSON/YAML block on the pipeline definition that
binds to a source action and fires on Git events. It replaces V1's
`PollForSourceChanges` flag and side-car CloudWatch Events rule.

```yaml
Triggers:
  - ProviderType: CodeStarSourceConnection  # or CodeCommit
    GitConfiguration:
      SourceActionName: Source              # must match the source action's Name
      Push:
        - Branches: {Includes: [...], Excludes: [...]}
          FilePaths: {Includes: [...], Excludes: [...]}
          Tags: {Includes: [...], Excludes: [...]}
```

The trigger fires on any push event that satisfies AT LEAST ONE
`Push` block (blocks are OR'd). Within a block, all configured filters
(Branches, FilePaths, Tags) must match (AND'd).

## Filter field semantics

| Filter | Match type | Examples |
|---|---|---|
| `Branches.Includes` | glob (one-level) | `main`, `release/*`, `feature/*` |
| `Branches.Excludes` | glob (one-level) | `experimental/*` |
| `FilePaths.Includes` | glob (recursive) | `src/**`, `services/api/**` |
| `FilePaths.Excludes` | glob (recursive) | `docs/**`, `*.md`, `.github/**` |
| `Tags.Includes` | exact string | `deploy=prod`, `release-v1.2` |
| `Tags.Excludes` | exact string | `wip-*` |

**Glob rules:**
- `*` matches one path segment (no `/`).
- `**` matches zero or more path segments (recursive).
- `release/*` matches `release/v1` and `release/v2` but NOT
  `release/v1/beta`. For multi-level, use `release/**`.
- `main` is exact-match (no glob characters).

## Common trigger patterns

### Production branch only

```yaml
Push:
  - Branches: {Includes: [main]}
```

### Multiple release branches

```yaml
Push:
  - Branches: {Includes: [main, "release/*"]}
```

### Monorepo service-scoped trigger

```yaml
Push:
  - Branches: {Includes: [main]}
    FilePaths: {Includes: [services/api/**], Excludes: [services/api/README.md, "services/api/docs/**"]}
```

### Tagged releases only

```yaml
Push:
  - Tags: {Includes: ["deploy=prod"]}
```

### Multiple independent triggers (OR'd)

```yaml
Push:
  - Branches: {Includes: [main]}
  - Tags: {Includes: ["hotfix=*"]}
```

## Anti-pattern: unscoped trigger

```yaml
Triggers:
  - ProviderType: CodeStarSourceConnection
    GitConfiguration:
      SourceActionName: Source
      Push: []  # NO FILTERS — fires on every push to every branch
```

An empty `Push` block (or omitted filter keys) fires on EVERY push to
EVERY branch. This floods pipeline history, burns per-execution costs
($0.002 × N feature pushes), and risks unintended production deploys
from feature branches. Always scope to production branches at minimum.

## CodeCommit-specific trigger note

CodeCommit triggers use `ProviderType: CodeCommit` and fire on
`referenceCreated` and `referenceUpdated` events. The filter block is
the same shape as CodeStarSourceConnection.

```yaml
Triggers:
  - ProviderType: CodeCommit
    GitConfiguration:
      SourceActionName: Source
      Push:
        - Branches: {Includes: [main, release/*]}
```

## Namespace variables contract

Namespace variables are exported by an action and consumed by
downstream actions or stage conditions. They flow forward only — a
stage CANNOT read variables from a later stage.

### Producer patterns

**CodeBuild (exported-variables):**
```yaml
env:
  exported-variables:
    - IMAGE_TAG
    - IMAGE_URI
    - BUILD_VERSION
```

Variables declared in `exported-variables` and set in the build
environment (via `export`) are captured automatically.

**CloudFormation (OutputFileName):**
```yaml
Configuration:
  ActionMode: CREATE_REPLACE
  OutputFileName: stack-outputs.json
```

The stack's outputs are written to a JSON file in the artifact, then
accessible as `#{DeployVars.Outputs.<OutputKey>}`.

**Literal action variables:**
```yaml
- Name: ApproveProd
  Namespace: ApprovalVars
  Variables:
    - Name: TicketUrl
      Value: https://internal.example.com/CHG12345
```

### Consumer patterns

**Action configuration reference:**
```yaml
Configuration:
  Image1: #{BuildVars.IMAGE_URI}
```

**Stage condition (skip stage if variable is empty):**
```yaml
Conditions:
  - ConditionKey: "#{BuildVars.IMAGE_URI}"
    ConditionOperator: StringEquals
    ConditionValue: ""
    Not: true  # skip if IMAGE_URI IS empty
```

**Nested namespace (JSON-exported):**
```yaml
Configuration:
  ServiceArn: #{DeployVars.Outputs.ServiceArn}
```

## Silent-empty-string failure mode

A missing namespace variable renders as empty string `""` in the
consuming action — NOT an error. A pipeline that deploys
`Image1: #{BuildVars.IMAGE_URI}` with an undefined `IMAGE_URI`
deploys an empty string, which ECS rejects with
"InvalidParameterException."

**Resolution heuristics:**
- Always add a stage condition that validates the variable is
  non-empty before the deploy stage.
- Verify `exported-variables` in `buildspec.yml` lists every variable
  consumed downstream.
- For CloudFormation, use `OutputFileName` and reference via
  `#{DeployVars.Outputs.<Key>}` — more robust than individual export
  variables.

## Secrets and namespace variables

Namespace variables render in plaintext in:
- CloudTrail (the `CreatePipeline` API call records the variable
  references, and pipeline executions log resolved values).
- The pipeline execution history in the console.
- `get-pipeline` and `list-action-executions` API output.

**Never pass secrets as namespace variables.** Use Secrets Manager or
Parameter Store SecureString, referenced by ARN in the action's IAM
role. The pipeline role should have `secretsmanager:GetSecretValue`
scoped to the exact secret ARN, and the build/deploy action reads the
secret at runtime via the AWS SDK.

## Stage-level conditions

V2 supports `Conditions` blocks at the stage level that skip the
stage based on namespace variables. This enables patterns like "deploy
only on prod-tagged commits" without separate pipelines.

```yaml
- Name: DeployProd
  Conditions:
    - ConditionKey: "#{BuildVars.ENV}"
      ConditionOperator: StringEquals
      ConditionValue: "prod"
  Actions:
    - Name: DeployCFN
      ...
```

If `BuildVars.ENV` is not "prod", the DeployProd stage is skipped.
The pipeline execution shows the stage as "Skipped" with the
condition that evaluated to false.

## V1 → V2 trigger migration

V1 pipelines typically have:
- `PollForSourceChanges: true` in the source action configuration, OR
- `PollForSourceChanges: false` with a side-car CloudWatch Events
  rule calling `StartPipelineExecution`.

**Migration procedure:**
1. Set `pipelineType: V2` on the pipeline.
2. Set `DetectOptions: false` (replaces `PollForSourceChanges`).
3. Add a `Triggers` block with appropriate filters.
4. Delete the legacy CloudWatch Events rule:
   `aws events delete-rule --name <rule-name>`.
5. Update the pipeline: `aws codepipeline update-pipeline --cli-input-json file://pipeline.json`.

Without step 4, both the V2 trigger AND the legacy rule fire,
producing duplicate executions.

## AWS documentation

- **CodePipeline V2 triggers reference** — https://docs.aws.amazon.com/codepipeline/latest/userguide/triggers-v2.html
- **Namespace variables** — https://docs.aws.amazon.com/codepipeline/latest/userguide/reference-variables.html
- **Stage conditions** — https://docs.aws.amazon.com/codepipeline/latest/userguide/stage-conditions.html
- **V1 to V2 migration guide** — https://docs.aws.amazon.com/codepipeline/latest/userguide/pipeline-types-migrate.html
