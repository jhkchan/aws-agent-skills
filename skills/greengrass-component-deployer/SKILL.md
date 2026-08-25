---
name: greengrass-component-deployer
description: 'Deploys AWS IoT Greengrass v2 components with production defaults: component recipe YAML (lifecycle hooks: install, startup, shutdown), component versioning (semantic versioning, bump on recipe change), artifact storage (S3 bucket + presigned URLs), component dependencies (HARD vs SOFT dependency types), deployment to thing group (not individual devices), configuration merge (runtime parameters for per-device customization), IoT role alias for Secrets Manager access, Lambda functions as components (aws.lambda component dependency), Docker containers as components (aws.greengrass.DockerApplicationManager + aws.docker.Login), local volume mounts (docker volume / bind mount), cloud-based deployment vs local. Triggers: create greengrass component, deploy greengrass component, greengrass recipe yaml, greengrass deployment thing group, greengrass configuration merge, greengrass lambda component, greengrass docker component, greengrass secret manager, greengrass core device setup, greengrass component version.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with greengrassv2 and s3 access, plus IoT things/thing groups provisioned. Works with Terraform aws_greengrass_component_definition / aws_greengrass_deployment resources and CloudFormation AWS::GreengrassV2::Component / AWS::GreengrassV2::Deployment templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Management
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, greengrass, greengrass-v2, iot, edge, cloudops, deploy, provisioning, component, recipe, lifecycle, lambda, docker, thing-group, configuration-merge
  dependencies: aws-orchestrator
  keywords: aws, greengrass, greengrass v2, iot, edge, component, recipe, cloudops, deploy, provisioning, thing group, lifecycle, artifact, lambda, docker, secret manager, configuration merge, core device
  when_to_use: Invoke when the user wants to create or deploy an AWS IoT Greengrass v2 component, write a component recipe with lifecycle hooks, store component artifacts in S3, manage component dependencies (hard vs soft), deploy a component to a thing group, use configuration merge for per-device runtime parameters, integrate Secrets Manager via IoT role alias, run a Lambda function as a component, run a Docker container as a component, configure local volume mounts, or set up a Greengrass core device. Do NOT invoke for Greengrass v1 (use v1 skills), AWS IoT Core device management (no Greengrass), or AWS Panorama (different edge runtime).
---

# Greengrass Component Deployer

An AWS CloudOps agent skill that deploys AWS IoT Greengrass v2
components with correct defaults. The skill walks the operator
through component recipe creation (lifecycle hooks), versioning,
artifact storage (S3), dependency management (hard vs soft),
deployment targeting (thing groups, NOT individual devices),
configuration merge (runtime parameters), secret manager integration
via IoT role alias, Lambda and Docker as components, local volume
mounts, cloud-based vs local deployment, and core device setup,
captures all provisioning decisions, explains why each default
matters, and emits a READY_TO_DEPLOY checklist with copy-pasteable
verification commands.

## Activation keywords

create Greengrass component, deploy Greengrass component, Greengrass
recipe YAML, Greengrass deployment thing group, Greengrass
configuration merge, Greengrass Lambda component, Greengrass Docker
component, Greengrass secret manager, Greengrass core device setup,
Greengrass component version.

## STRICT output contract

When this skill is invoked with a Greengrass v2 component deployment
request (create a component, deploy to thing group, write a recipe,
package an artifact, configure Lambda or Docker as a component, set
up secrets, or a partial configuration), the agent MUST respond with
the READY_TO_DEPLOY checklist defined in the "Output format" section
using the literal all-caps labels `GREENGRASS_COMPONENT:`,
`VERDICT:`, `CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT
preface the checklist with prose, headings, or disclaimers — emit
the block as the first lines of the response. This contract is what
assertion-based evals and downstream provisioning pipelines rely on;
deviating from the literal labels breaks automation silently.

If any prerequisite is missing, the verdict is
`PREREQUISITES_MISSING` with a specific gap citation in the
checklist (marked `[✗]`), and `READY_TO_DEPLOY` MUST NOT also
appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Component recipe (lifecycle hooks) | Core recipe model |
| Step 2 — Component versioning | Semantic versioning rules |
| Step 3 — Artifact storage (S3) | Artifact packaging |
| Step 4 — Component dependencies (hard vs soft) | Dependency chain |
| Step 5 — Deployment to thing group | Deployment targeting |
| Step 6 — Configuration merge | Per-device customization |
| Step 7 — Secret manager integration (IoT role alias) | Secrets on edge |
| Step 8 — Lambda as component | Lambda runtime on edge |
| Step 9 — Docker as component | Container runtime on edge |
| Step 10 — Local volume mount | Persistent storage on edge |
| Step 11 — Cloud-based vs local deployment | Deployment modes |
| Step 12 — Core device setup | Device prerequisites |
| Step 13 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/recipe-and-lifecycle.md | Recipe + lifecycle detail |
| references/deployment-and-config.md | Deployment + config merge detail |

## Mindset

**One-line takeaway:** A Greengrass v2 component is a software
module that runs on an edge device. The component recipe defines
lifecycle hooks (install, startup, shutdown) as shell scripts.
Configuration merge allows per-device customization of runtime
parameters. Deployments target thing GROUPS, not individual devices
— use a thing group even for a single device so you can add devices
later without re-architecting.

Three misconceptions dominate Greengrass v2 misdesign at provisioning
time:

- **"Deploy the component to a single device."** While technically
  possible, Greengrass v2 deployments should target thing GROUPS, not
  individual devices. A thing group allows you to add or remove devices
  without modifying the deployment. If you deploy to a single thing
  and later need to add a second device, you must create a new
  deployment. Always create a thing group (even with one device) and
  target the group.

- **"The recipe lifecycle section is optional."** It is NOT. The
  lifecycle section defines what happens at install, startup, and
  shutdown. Without lifecycle hooks, the component is a no-op — it
  installs but does nothing. Every component MUST have at least a
  startup hook. The install hook downloads/extracts artifacts; the
  startup hook runs the component logic; the shutdown hook cleans up.

- **"Configuration merge is just default configuration."** It is NOT.
  Default configuration (in the recipe) applies to ALL deployments.
  Configuration merge is a deployment-level override that applies to
  a SPECIFIC deployment (and thus a specific thing group). This allows
  per-device or per-group customization without modifying the recipe.
  For example, the recipe defines `port: 8080` as default, and a
  deployment to a specific thing group merges `port: 8081` to override
  for that group.

## Configuration dependency graph (novel heuristic)

Greengrass v2 component configurations are NOT independent. The
recipe must exist before the component can be created. Artifacts
must be uploaded to S3 before the component version references them.
The core device must be provisioned and running before deployment.
The thing group must exist before the deployment targets it. Use
this graph to sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Component recipe | recipe YAML with lifecycle hooks; manifest with artifacts | recipe MUST reference S3 URIs for artifacts; local paths fail on remote devices | component version (ARN) |
| Component version | recipe YAML uploaded; artifact S3 URIs valid | version bump REQUIRED on recipe change; same version = no update | deployment target |
| S3 artifacts | S3 bucket exists; artifact uploaded; Greengrass token exchange role has s3:GetObject | presigned URLs NOT used by Greengrass; it uses the token exchange role to access S3 | artifact download on device |
| Thing group | IoT things exist; thing group created | thing group can be empty at deploy time but components won't run until devices join | deployment target |
| Deployment | component version exists; thing group exists; core devices running | deployment job is asynchronous; components deploy over minutes | component execution on devices |
| Configuration merge | deployment exists | merge keys MUST match the recipe's configuration schema; mismatched keys are silently ignored | per-device runtime parameters |
| IoT role alias | IAM role with secretsmanager:GetSecretValue; IoT role alias maps to the role; component references alias via SECRET_MANAGER_ROLE_ALIAS env var | the token exchange service rotates credentials automatically; no manual rotation needed | secret access on edge |
| Lambda component | aws.lambda artifact (ZIP); aws.lambda component version deployed as dependency; Lambda runtime specified in recipe | the Lambda ISO runtime is downloaded by the aws.lambda component, not bundled | Lambda execution on edge |
| Docker component | aws.greengrass.DockerApplicationManager deployed; aws.docker.Login for private registries; Docker image accessible | Docker daemon must be running on the core device; image pulled at startup, not install | container execution on edge |
| Core device | Greengrass v2 installed; token exchange role configured; IoT thing provisioned | core device MUST have the Greengrass CLI for local debugging | component deployment target |

**The configuration-merge row is the one a baseline model misses.**
Default configuration in the recipe applies to all deployments.
Configuration merge is a deployment-level override that allows per-
group customization. The procedure below forces an explicit decision
on whether merge is needed.

**Cross-dependency gotchas:**
- Component version must be bumped on EVERY recipe change. Creating
  a component version with the same semantic version as an existing
  one silently does nothing (no update deployed).
- Artifacts are referenced by S3 URI in the recipe manifest, and
  Greengrass uses the token exchange role (NOT presigned URLs) to
  download them. The role must have `s3:GetObject` on the artifact
  bucket.
- Lambda components require the `aws.lambda` component as a HARD
  dependency. Without it, the Lambda runtime is not available on the
  device.
- Docker components require `aws.greengrass.DockerApplicationManager`
  as a HARD dependency. Without it, Docker image management is not
  available.
- The thing group should be created BEFORE the deployment, even if
  empty. Devices can join later and automatically receive the
  deployment.

## Expert heuristic: recipe lifecycle hooks define everything

A baseline model says "write a recipe." The correct heuristic
recognizes that lifecycle hooks are the heart of the recipe. Each
hook is a shell command that runs at a specific lifecycle stage.

```text
Component lifecycle stages:
  Install  → runs ONCE when component is first deployed (or on version update)
             typically: extract artifacts, install dependencies, create directories
  Startup  → runs EVERY TIME the component starts (device boot, restart, recovery)
             typically: run the main logic, start a process, launch a server
  Shutdown → runs when the component stops (undeploy, device shutdown, update)
             typically: kill processes, flush buffers, release resources
  Recover  → OPTIONAL: runs if startup fails
             typically: retry logic, fallback behavior

Recovery timeout: if a startup script does not exit within 60s (default),
Greengrass considers the component failed and runs the recover hook.
```

**Key implication:** the startup hook should be a long-running
process (a daemon, a server, a loop). If the startup script exits
immediately, Greengrass considers the component "errored" and
repeatedly restarts it. For one-shot scripts, use the install hook
instead.

## Expert heuristic: thing group vs individual device targeting

A baseline model says "deploy to the device." The correct heuristic
recognizes that thing groups are the deployment target abstraction.

```text
Deployment targeting decision:
  ├── Single device, will never scale → thing group with 1 member (still recommended)
  ├── Single device, will scale later → thing group (add members later)
  ├── Multiple devices, same config   → thing group (single deployment)
  ├── Multiple devices, different config → thing group + configuration merge per subgroup
  └── Fleet-wide canary rollout       → thing group hierarchy (parent → child groups)

Why thing group even for 1 device:
  ├── Add devices later without creating a new deployment
  ├── Rollback applies to the group (not per-device)
  ├── Configuration merge targets the group
  └── Fleet metrics aggregate by group
```

**Key implication:** always create a thing group for deployment
targeting, even for a single device. This avoids re-architecting
when scaling.

## Expert heuristic: configuration merge vs default configuration

A baseline model says "put all config in the recipe." The correct
heuristic recognizes that configuration has two layers: default (in
recipe) and merge (in deployment).

```text
Configuration layers (later overrides earlier):
  1. Recipe default configuration → applies to ALL deployments of this component
  2. Deployment configuration merge → overrides defaults for THIS deployment's thing group
  3. Local configuration (Greengrass CLI) → overrides deployment merge for THIS device only

Example:
  Recipe default:     { port: 8080, logLevel: "info" }
  Deployment merge:   { port: 8081 }              ← overrides port for this group
  Local override:     { logLevel: "debug" }       ← overrides logLevel for this device only

Effective config on device: { port: 8081, logLevel: "debug" }
```

**Key implication:** use recipe defaults for baseline behavior and
configuration merge for per-group customization. This lets you deploy
the same component version to different groups with different
configurations.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites.
If any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| S3 bucket for artifacts | Component artifacts stored in S3 | `aws s3 ls s3://<bucket>` |
| Token exchange role with s3:GetObject | Greengrass core device downloads artifacts via this role | Check IAM role policy |
| IoT thing exists | Core device registered as IoT thing | `aws iot describe-thing --thing-name <name>` |
| Thing group exists | Deployment targets thing groups | `aws iot describe-thing-group --thing-group-name <name>` |
| Core device running Greengrass v2 | Component runs on the core device | `aws greengrassv2 list-core-devices` |
| Component recipe with lifecycle hooks | Recipe defines install/startup/shutdown | Validate YAML structure |
| Component version bumped | Same version = no update deployed | Check existing component versions |
| Lambda runtime (if Lambda component) | aws.lambda component must be a dependency | Verify dependency in recipe |
| Docker ApplicationManager (if Docker) | Required for Docker image management | Verify dependency in recipe |
| IoT role alias (if secrets) | Maps IAM role for Secrets Manager access | `aws iot describe-role-alias --role-alias <name>` |

If any prerequisite is missing, output
`VERDICT: PREREQUISITES_MISSING` and cite the specific gap.

## Step 1 — Component recipe (lifecycle hooks)

Minimal recipe YAML, lifecycle-hook precedence table, and artifact path variables moved verbatim to [references/recipe-and-lifecycle.md](references/recipe-and-lifecycle.md).
Load on demand when authoring or validating a component recipe.

## Step 2 — Component versioning

Version-bump rules table and create-component-version commands moved verbatim to [references/recipe-and-lifecycle.md](references/recipe-and-lifecycle.md).
Load on demand when publishing a component version.

## Step 3 — Artifact storage (S3)

Artifact upload command, token-exchange role policy, and unarchive types moved verbatim to [references/recipe-and-lifecycle.md](references/recipe-and-lifecycle.md).
Load on demand when packaging artifacts.

## Step 4 — Component dependencies (hard vs soft)

HARD vs SOFT dependency table, recipe snippet, and resolution order moved verbatim to [references/recipe-and-lifecycle.md](references/recipe-and-lifecycle.md).
Load on demand when defining component dependencies.

## Step 5 — Deployment to thing group

Thing-group creation, deployment JSON, verification, and deployment policies table moved verbatim to [references/deployment-and-config.md](references/deployment-and-config.md).
Load on demand when creating the deployment.

## Step 6 — Configuration merge

MERGE/RESET semantics and configuration access in lifecycle scripts moved verbatim to [references/deployment-and-config.md](references/deployment-and-config.md).
Load on demand when overriding configuration per thing group.

## Step 7 — Secret manager integration (IoT role alias)

Secret-access IAM role, IoT role alias creation, and recipe snippet moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when a component reads Secrets Manager secrets.

## Step 8 — Lambda as component

create-component-version --lambda-function, dependency snippet, Lambda config table, and deployment example moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand for Lambda-based components.

## Step 9 — Docker container as component

Docker recipe, private-registry login, and deployment example moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand for Docker-based components.

## Step 10 — Local volume mount

Volume-mount recipe and persistence best-practices table moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand for persistent edge storage.

## Step 11 — Cloud-based deployment vs local deployment

Cloud vs local mode table, Greengrass CLI local deployment, and default-deployment pattern moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when choosing a deployment mode.

## Step 12 — Core device setup

Nucleus install commands, device verification, and token-exchange role notes moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when setting up a core device.

## Step 13 — Recent features

2023-2026 feature notes (component APIs, Docker improvements, merge validation, stream manager, fleet provisioning, CloudWatch metrics, CLI validation) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when recent features matter.

## NEVER do these things

1. **NEVER deploy to an individual device when a thing group exists.**
   Deployments should target thing GROUPS, not individual devices.
   Even for a single device, create a thing group and target it.
   This allows scaling without re-architecting.

2. **NEVER skip the version bump on recipe changes.** Creating a
   component version with the same semantic version as an existing
   one is a no-op. The deployment will not update. Always bump the
   version on EVERY recipe or artifact change.

3. **NEVER use presigned URLs for artifacts.** Greengrass uses the
   token exchange role on the core device to download S3 artifacts.
   Presigned URLs expire and are not managed by Greengrass. Use the
   `s3://` URI format in the recipe and ensure the token exchange
   role has `s3:GetObject` permission.

4. **NEVER make the startup hook a one-shot script.** The startup
   hook should be a long-running process (daemon, server, loop). If
   the startup script exits immediately, Greengrass considers the
   component "errored" and repeatedly restarts it. For one-shot
   scripts, use the install hook.

5. **NEVER forget the aws.lambda dependency for Lambda components.**
   Lambda components require the `aws.lambda` component as a HARD
   dependency. Without it, the Lambda runtime is not available on
   the device and the component will fail to start.

6. **NEVER forget aws.greengrass.DockerApplicationManager for Docker
   components.** Docker components require this as a HARD dependency.
   Without it, Docker image management is not available.

7. **NEVER use hardcoded host paths for component storage.** Use
   `{work:path}` for component-scoped storage. Hardcoded host paths
   may not exist on the device and are not managed by Greengrass.

8. **NEVER assume configuration merge replaces default config.**
   MERGE deep-merges with existing configuration (nested keys are
   merged, not replaced). To remove a key, use RESET, not MERGE with
   null.

9. **NEVER skip the core device health check.** Before deploying,
   verify the core device is HEALTHY. A device in UNHEALTHY state
   will not receive deployments.

10. **NEVER create a deployment without failureDetectionPolicy.**
    Always set `failureDetectionPolicy.action` to `ROLLBACK` (the
    default) so failed deployments revert to the last known good
    state. `DO_NOTHING` leaves devices in a broken state.

## Output format

```text
GREENGRASS_COMPONENT: <component-name>@<version> → <thing-group>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Component recipe: <component-name>@<version> — lifecycle hooks defined (install, startup, shutdown)
  [✓|✗] Version bump: <previous-version> → <new-version>
  [✓|✗] Artifacts: S3 URIs in recipe — s3://<bucket>/<path>
  [✓|✗] Token exchange role: s3:GetObject on <bucket> — configured
  [✓|✗] Thing group: <group-name> (<device-count> devices)
  [✓|✗] Core device(s): <device-name> — HEALTHY
  [✓|✗] Dependencies: HARD [<list>], SOFT [<list>]
  [✓|✗] Configuration merge: <merged-keys or "none (recipe defaults only)">
  [✓|✗] Secret manager: IoT role alias <alias-name> — configured | not required
  [✓|✗] Component type: Generic | Lambda (arn:<lambda-arn>) | Docker (image:<image-name>)
  [✓|✗] Volume mount: {work:path}/<dir> | none
  [✓|✗] Deployment mode: Cloud-based (default deployment) | Local (Greengrass CLI)
  [✓|✗] Deployment policies: failureDetection=ROLLBACK, componentUpdate=NOTIFY_COMPONENTS
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws greengrassv2 describe-component --arn <component-arn> --region <region>
  aws greengrassv2 list-core-devices --region <region>
  aws greengrassv2 get-deployment --deployment-id <deployment-id> --region <region>
```

### Worked example — basic component deployment

```text
GREENGRASS_COMPONENT: com.example.MyComponent@1.0.0 → MyDeviceGroup
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Component recipe: com.example.MyComponent@1.0.0 — lifecycle hooks defined (install, startup, shutdown)
  [✓] Version bump: new component (1.0.0)
  [✓] Artifacts: S3 URIs in recipe — s3://my-greengrass-artifacts/artifacts/com.example.MyComponent/1.0.0/my-script.py
  [✓] Token exchange role: s3:GetObject on my-greengrass-artifacts — configured
  [✓] Thing group: MyDeviceGroup (1 device)
  [✓] Core device(s): MyCoreDevice — HEALTHY
  [✓] Dependencies: HARD [], SOFT []
  [✓] Configuration merge: message="Hello from deployment", logging.level="debug"
  [✓] Secret manager: not required
  [✓] Component type: Generic
  [✓] Volume mount: none
  [✓] Deployment mode: Cloud-based (default deployment)
  [✓] Deployment policies: failureDetection=ROLLBACK, componentUpdate=NOTIFY_COMPONENTS
  [✓] Tags: Environment=production, Application=edge-processor
VERIFICATION_COMMANDS:
  aws greengrassv2 describe-component --arn arn:aws:greengrass:us-east-1:123456789012:components:com.example.MyComponent:versions:1.0.0 --region us-east-1
  aws greengrassv2 list-core-devices --region us-east-1
  aws greengrassv2 get-deployment --deployment-id d-1234567890 --region us-east-1
```

## Error handling

Six failure modes (ERRORED state, unreachable device, artifact download, merge no-op, Lambda start, Docker start) moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand when a deployment misbehaves.

## References (load on demand)

- [references/recipe-and-lifecycle.md](references/recipe-and-lifecycle.md) — recipe schema, lifecycle hooks, versioning, artifact storage, dependencies
- [references/deployment-and-config.md](references/deployment-and-config.md) — thing-group deployment, deployment policies, configuration-merge semantics
- [references/advanced-patterns.md](references/advanced-patterns.md) — secrets via IoT role alias, Lambda/Docker components, volume mounts, deployment modes, core device setup, 2023-2026 features
- [references/error-handling.md](references/error-handling.md) — ERRORED components, unreachable devices, artifact download and merge failures

## Domain

AWS CloudOps / AWS IoT Greengrass v2 Component Deployment & Edge
Computing.

## AWS documentation

- **Greengrass v2 Developer Guide** — https://docs.aws.amazon.com/greengrass/v2/developerguide/what-is-iot-greengrass.html
- **Component recipes** — https://docs.aws.amazon.com/greengrass/v2/developerguide/component-recipe-reference.html
- **Create component** — https://docs.aws.amazon.com/greengrass/v2/developerguide/create-components.html
- **Deploy components** — https://docs.aws.amazon.com/greengrass/v2/developerguide/deploy-components.html
- **Configuration merge** — https://docs.aws.amazon.com/greengrass/v2/developerguide/configure-component-update.html
- **Lambda components** — https://docs.aws.amazon.com/greengrass/v2/developerguide/lambda-functions.html
- **Docker components** — https://docs.aws.amazon.com/greengrass/v2/developerguide/run-docker-container.html
- **Secret manager integration** — https://docs.aws.amazon.com/greengrass/v2/developerguide/secrets-manager.html
- **Core device setup** — https://docs.aws.amazon.com/greengrass/v2/developerguide/setting-up.html
- **Greengrass CLI** — https://docs.aws.amazon.com/greengrass/v2/developerguide/greengrass-cli-component.html
