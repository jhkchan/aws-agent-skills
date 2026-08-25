---
name: serverlessrepo-application-deployer
description: 'Provisions AWS Serverless Application Repository (SAR) applications with production defaults: SAM template (template.yaml) with Transform: AWS::Serverless-2016-10-31, README.md (required for publish), LICENSE (required for public), application packaging (zip upload or S3 bucket with code URI), semantic versioning (SemVer — required for every publish), application sharing model (private vs account-grant vs public), application policy (who can deploy cross-account), nested applications (AWS::Serverless:: Application), application parameters (cloudformation parameters surfaced at deploy time), deployment role (CAPABILITY_IAM / CAPABILITY_NAMED_IAM / CAPABILITY_AUTO_EXPAND), SAM transform during deploy (transform happens BEFORE CloudFormation sees the template), published author profile (author name, URL. Triggers: publish serverless application, sar publish, serverless application repository, sam package, sam deploy, sar application policy, cross-account sar deploy, nested sar application, semantic version sar.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS SAM CLI (sam package, sam deploy) or AWS CLI v2 with serverlessrepo create-application / put-application-policy / create-cloud-formation-change-set. Requires an S3 bucket for artifact storage and IAM permissions for cloudformation:CreateChangeSet, serverlessrepo:CreateApplication, and the transforms the SAM template declares.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: DevTools
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, serverless, sar, sam, cloudformation, cloudops, deploy, devtools, semantic-versioning, application-policy, nested-application, cross-account
  dependencies: aws-orchestrator
  keywords: aws, serverless application repository, sar, sam, sam template, sam deploy, sam package, cloudformation, semantic versioning, application policy, nested application, cross-account deploy, application sharing, public application, private application, appregistry, deployment role, lambda, cloudops, deploy, devtools
  when_to_use: Invoke when the user wants to publish a serverless application to the Serverless Application Repository, share an application privately or publicly, deploy an application from SAR via CloudFormation, version an application update using semantic versioning, compose nested SAR applications, configure an application policy for cross-account deployment, or understand the SAM transform pipeline. Do NOT invoke for AWS Service Catalog product registration (different catalog), CDK app publishing (CDK has its own publishing path), or AppRegistry metadata grouping (AppRegistry is metadata-only, not a deploy surface).
---

# Serverless Application Repository Deployer

An AWS CloudOps agent skill that provisions AWS Serverless Application
Repository (SAR) applications with correct defaults. The skill walks
the operator through the SAM template structure, packaging (zip upload
or S3), semantic versioning, the application sharing model (private vs
account-grant vs public), the application policy that gates cross-
account deploy, the SAM transform pipeline (transform happens BEFORE
CloudFormation), nested application composition, the deployment role
and capabilities, and application deletion/cleanup. It captures the
application definition decisions, explains why each default matters,
and emits a READY_TO_DEPLOY checklist with copy-pasteable verification
commands.

## Activation keywords

publish serverless application, sar publish, serverless application
repository, sam package, sam deploy, sar application policy, cross-
account sar deploy, nested sar application, semantic version sar.

## STRICT output contract

When this skill is invoked with a SAR-provisioning request (publish
an application, share an application, deploy someone else's
application, version an update, compose nested applications, or a
partial configuration), the agent MUST respond with the
READY_TO_DEPLOY checklist defined in the "Output format" section
using the literal all-caps labels `SAR_APPLICATION:`, `VERDICT:`,
`CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface the
checklist with prose, headings, or disclaimers — emit the block as
the first lines of the response. This contract is what assertion-
based evals and downstream provisioning pipelines rely on; deviating
from the literal labels breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Application structure (template.yaml + README + LICENSE) | Core app anatomy |
| Step 2 — SAM transform pipeline | Transform happens before CFN |
| Step 3 — Packaging (zip upload or S3 code URI) | Artifact storage |
| Step 4 — Semantic versioning | Every publish needs a version |
| Step 5 — Application sharing (private vs public) | Visibility model |
| Step 6 — Application policy (cross-account deploy) | Who can deploy |
| Step 7 — Deployment via CloudFormation change set | Deploy mechanism |
| Step 8 — Deployment role and capabilities | IAM surface |
| Step 9 — Nested applications | Composition |
| Step 10 — Application parameters | Surfaced at deploy time |
| Step 11 — Author profile and labels | Published metadata |
| Step 12 — Deletion and cleanup | Teardown |
| Step 13 — SAR vs AppRegistry | Avoid confusion |
| Step 14 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/sam-transform-and-deploy.md | Transform + deploy detail |
| references/sar-publishing-and-sharing.md | Publishing + sharing detail |

## Mindset

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#mindset).
> Three provisioning-time misconceptions: publish vs deploy, cross-account 403 without an application policy, mandatory immutable SemVer.

## Configuration dependency graph (novel heuristic)

SAR application configurations are NOT independent. The SAM template
must exist before packaging. Packaging must complete before publish.
Publish must complete before sharing. The application policy must
exist before cross-account deploy. Use this graph to sequence
provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| SAM template (template.yaml) | Valid YAML; Transform declared; resources under 200 | Template with unresolved `CodeUri` uploads raw path, not code | the application definition |
| README.md | Required at publish time (CreateApplication / UpdateApplication) | Empty README is accepted but app cannot be shared publicly without content | public sharing eligibility |
| LICENSE | Required for PUBLIC sharing only; private apps can omit | App without LICENSE cannot be made public (API rejects) | public sharing |
| Packaging (sam package) | S3 bucket exists; IAM s3:PutObject | Forgetting to package → CodeUri points to local path → deploy fails | S3-backed code artifact |
| Semantic version | Required at every publish; must be unique per application | Reusing a version → API rejects with ConflictException; no overwrite | update management |
| Publish (create-application) | Template packaged; README present; version set | Publishing without an application policy → only the publisher account can deploy | catalog entry |
| Application policy | Application published; consumer AWS account ID(s) known | Policy omitted → cross-account deploy fails with 403 | cross-account deployment |
| Deployment (create-cloud-formation-change-set) | Application published; consumer has permission; capabilities match | Missing CAPABILITY_AUTO_EXPAND → nested application deploy fails | running stack |
| Nested application | Parent template uses AWS::Serverless::Application; child app published and accessible | Child app not shared → parent deploy fails at expand time | composition |

**The application-policy-gates-cross-account row is the one a
baseline model misses.** Publishing the app is necessary but NOT
sufficient for cross-account use. The policy must explicitly grant
each consumer account (for private) or be set to public (for public
apps). The SAM-transform-before-CFN row is the second commonly
misunderstood step.

**Cross-dependency gotchas:**

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#configuration-dependency-graph--cross-dependency-gotchas).
> Five gotchas: deploy-time transform, CAPABILITY_AUTO_EXPAND for nested apps, private sharing tiers, stack vs SAR deletion, version embedded in the ARN.

## Expert heuristic: the SAM transform pipeline

A baseline model says "upload the template and deploy." The correct
heuristic recognizes that SAR stores the RAW SAM template and the
transform happens at DEPLOY time on the CONSUMER side.

```text
Publisher flow:
  1. Write template.yaml (Transform: AWS::Serverless-2016-10-31)
  2. sam package → uploads code to S3, produces packaged.yaml
  3. serverlessrepo create-application → stores SAM template + metadata
  4. (optional) serverlessrepo put-application-policy → grants consumers

Consumer flow:
  1. serverlessrepo create-cloud-formation-change-set → SAR fetches template
  2. SAM transform runs → AWS::Serverless::Function → AWS::Lambda::Function
  3. CloudFormation receives the EXPANDED template
  4. CloudFormation creates/updates the stack with CAPABILITY_IAM
```

**Key implication:** the publisher's SAM template must be self-
contained and valid for transformation. Any intrinsic function refs
must resolve within the consumer's account at deploy time. The
publisher cannot pre-transform — the transform is inherently a deploy-
time operation because it may generate account-specific resources
(IAM roles, API Gateway stage names, etc.).

## Expert heuristic: application policy gates cross-account deploy

A baseline model publishes the app and assumes it is deployable
everywhere. The correct heuristic recognizes three sharing tiers,
each with a different deploy permission model.

```text
Sharing tier decision:
  ├── PRIVATE (default)
  │     → Only the publisher account can deploy
  │     → No application policy needed
  │     → ARN: arn:aws:serverlessrepo:<region>:<acct>:apps/<app>
  │
  ├── PRIVATE + APPLICATION POLICY (account-grant)
  │     → Publisher grants specific AWS account IDs
  │     → put-application-policy with Principal: {AWS: ["arn:...:<acct>"]}
  │     → Each granted account can deploy via create-cloud-formation-change-set
  │     → Top-level deployment status: "AWS::ServerlessRepo::Application"
  │
  └── PUBLIC
        → Anyone can discover and deploy (with capabilities)
        → Requires LICENSE file in the application
        → No application policy needed (public = open)
        → Public apps appear in the SAR catalog search
```

**Key implication:** the application policy is the access control
mechanism for PRIVATE cross-account sharing. For PUBLIC apps, the
policy is implicit (anyone). Missing the policy for a private cross-
account deploy is the #1 cause of "403 Forbidden" at deploy time.

## Expert heuristic: semantic versioning for update management

A baseline model treats versioning as a label. The correct heuristic
recognizes that SAR uses semantic versioning as an immutable,
monotonic identity for each published version.

```text
Semantic version rules (SAR enforces strict SemVer):
  Format: MAJOR.MINOR.PATCH[-prerelease]
    ├── MAJOR — breaking changes (new required parameters, removed resources)
    ├── MINOR — backward-compatible features (new optional parameters, new resources)
    ├── PATCH — backward-compatible fixes (bug fixes, template corrections)
    └── -prerelease — alpha/beta/rc (e.g., 1.0.0-beta, 2.0.0-rc.1)

  Immutability:
    ├── Each version is published ONCE — cannot overwrite
    ├── Re-publishing the same version → ConflictException
    └── To update, publish a NEW version (e.g., 1.0.0 → 1.0.1)

  Consumer update:
    ├── Consumer pins: SemVerVersion: "1.0.0"
    ├── To update: change to "1.0.1" and re-run create-cloud-formation-change-set
    └── SAR keeps ALL versions — consumers can rollback by pinning older
```

**Key implication:** versioning is the ONLY update mechanism. There
is no "latest" pointer — consumers must reference a specific version.
Plan version increments as part of the release pipeline.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| SAM template (template.yaml) exists and is valid | The template defines the application resources | `sam validate --template template.yaml` |
| Transform declared in template | Required for SAM resources to expand | Confirm `Transform: AWS::Serverless-2016-10-31` |
| README.md exists | Required for publish (any visibility) | Check file exists and has content |
| LICENSE exists (for public sharing) | Required for public apps; private can omit | Check file exists if sharing=public |
| S3 bucket for packaging | sam package uploads code artifacts to S3 | `aws s3 ls s3://<bucket>` |
| Semantic version defined | Every publish requires a unique version | Confirm version string follows SemVer |
| AWS account ID (publisher) | The publishing account owns the application | `aws sts get-caller-identity` |
| Consumer account IDs (for private sharing) | Application policy grants specific accounts | Confirm account IDs |
| IAM: serverlessrepo:CreateApplication | Required to publish | Check policy includes serverlessrepo actions |
| IAM: cloudformation:CreateChangeSet | Required to deploy | Check CloudFormation permissions |
| Sharing decision (private vs public) | Determines policy requirements | Confirm visibility scope |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Application structure (template.yaml + README + LICENSE)

A SAR application consists of three required components (LICENSE is
required only for public sharing):

| Component | Required for | Purpose |
|---|---|---|
| template.yaml (SAM) | All publishes | Defines the serverless resources |
| README.md | All publishes | Human-readable documentation; required by SAR API |
| LICENSE | Public sharing only | Open-source license; private apps can omit |
| (optional) metadata.yaml | Not required | Extra metadata; SAR API has dedicated fields |

> Moved to [references/sam-transform-and-deploy.md](references/sam-transform-and-deploy.md#step-1--application-structure-minimal-templateyaml--readme).
> Minimal template.yaml (Transform, Parameters, S3-event Lambda, Outputs) and required README.md content.

## Step 2 — SAM transform pipeline

The SAM transform (AWS::Serverless-2016-10-31) is a macro that
expands `AWS::Serverless::*` resource types into CloudFormation-
native resources. This expansion happens at DEPLOY time (when the
consumer deploys the app), not at publish time.

> Moved to [references/sam-transform-and-deploy.md](references/sam-transform-and-deploy.md#step-2--sam-transform-pipeline-expansion-table-and-dry-run).
> SAM type expansion table, auto-generated IAM roles note, transform dry run via sam build/package.

## Step 3 — Packaging (zip upload or S3 code URI)

Before publishing, the application's code must be packaged into an
S3-backed artifact. The `sam package` command handles this.

> Moved to [references/sam-transform-and-deploy.md](references/sam-transform-and-deploy.md#step-3--packaging-sam-package-and-s3-artifact-requirements).
> sam package CLI, CodeUri rewrite to S3, published-template rule, S3 bucket requirements.

## Step 4 — Semantic versioning

Every publish operation requires a semantic version. The version
follows SemVer format: `MAJOR.MINOR.PATCH[-prerelease]`.

> Moved to [references/sar-publishing-and-sharing.md](references/sar-publishing-and-sharing.md#step-4--semantic-versioning-bump-table-and-publish-cli).
> MAJOR/MINOR/PATCH/prerelease bump table, create-application publish and version-update CLI, unique-version rule.

## Step 5 — Application sharing (private vs public)

SAR applications have three sharing tiers:

| Tier | Visibility | Deploy permission | LICENSE required |
|---|---|---|---|
| PRIVATE (default) | Only publisher account | Publisher only | No |
| PRIVATE + policy | Discoverable by granted accounts | Granted accounts only | No |
| PUBLIC | Everyone (catalog search) | Anyone with capabilities | YES |

> Moved to [references/sar-publishing-and-sharing.md](references/sar-publishing-and-sharing.md#step-5--application-sharing-status-check-and-public-verification).
> get-application sharing-status check and IsVerifiedAuthor public-app verification.

## Step 6 — Application policy (cross-account deploy)

For PRIVATE cross-account sharing, the publisher must grant each
consumer account via an application policy.

> Moved to [references/sar-publishing-and-sharing.md](references/sar-publishing-and-sharing.md#step-6--application-policy-cross-account-grant-cli).
> put-application-policy / get-application-policy CLI; CreateCloudFormationChangeSet action gates consumer deploy.

## Step 7 — Deployment via CloudFormation change set

Consumers deploy a SAR application by creating a CloudFormation change
set from the application. This triggers the SAM transform and creates
the stack.

> Moved to [references/sam-transform-and-deploy.md](references/sam-transform-and-deploy.md#step-7--deployment-via-cloudformation-change-set).
> Consumer deploy CLI: create-cloud-formation-change-set, execute-change-set, sam deploy.

## Step 8 — Deployment role and capabilities

The consumer's deployment role must have permissions for all resources
the SAM template creates. The capabilities declare what the stack is
allowed to do.

| Capability | When required |
|---|---|
| CAPABILITY_IAM | Template creates IAM roles/policies (SAM auto-generates these) |
| CAPABILITY_NAMED_IAM | Template creates IAM resources with custom names |
| CAPABILITY_AUTO_EXPAND | Template contains nested applications (AWS::Serverless::Application) |
| CAPABILITY_RESOURCE_POLICY | Template modifies resource policies (e.g., S3 bucket policy) |

**Critical:** most SAM templates need at least CAPABILITY_IAM because
the transform auto-generates IAM roles for functions with `Policies`.
Nested applications additionally require CAPABILITY_AUTO_EXPAND.

## Step 9 — Nested applications

A SAR application can include other SAR applications using the
`AWS::Serverless::Application` resource type. This enables composition.

> Moved to [references/sam-transform-and-deploy.md](references/sam-transform-and-deploy.md#step-9--nested-applications-parent-template).
> Parent template with AWS::Serverless::Application (Location/Parameters/NotificationARNs/TimeoutInMinutes).

**Requirements for nested applications:**
- The nested app must be published and accessible (shared or public).
- The consumer must have deploy permission for the nested app.
- CAPABILITY_AUTO_EXPAND is REQUIRED at deploy time.
- The nested app deploys as a nested CloudFormation stack.

## Step 10 — Application parameters

Parameters defined in the SAM template are surfaced to the consumer
at deploy time. The consumer provides values via `--parameter-overrides`.

> Moved to [references/sam-transform-and-deploy.md](references/sam-transform-and-deploy.md#step-10--application-parameters-template-and-overrides).
> Parameters YAML (BucketName, MemorySize, EnableXRay) and --parameter-overrides deploy example.

## Step 11 — Author profile and labels

> Moved to [references/sar-publishing-and-sharing.md](references/sar-publishing-and-sharing.md#step-11--author-profile-and-labels).
> Author profile field table: author, home-page-url, source-code-url, labels (max 10), SpdxLicenseId, IsVerifiedAuthor.

## Step 12 — Deletion and cleanup

Deleting a SAR application is a two-step process: delete the deployed
stack, then delete the application from the catalog.

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#step-12--deletion-and-cleanup).
> Two-step teardown: delete-stack then delete-application; neither cascades to the other.

## Step 13 — SAR vs AppRegistry

SAR and AppRegistry serve different purposes:

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#step-13--sar-vs-appregistry).
> SAR vs AppRegistry comparison: deploy surface vs metadata grouping, versioning, sharing.

## Step 14 — Recent features

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#step-14--recent-features).
> 2023-2026: sam build esbuild, public-app verification streamlining, nested version ranges, transform performance, cross-region deploy, CDK SAR construct.

## NEVER do these things

1. **NEVER publish a SAR application without a README.md.** The SAR
   API requires README content at publish time. Without it, the
   CreateApplication call fails.

2. **NEVER publish as PUBLIC without a LICENSE file.** Public apps
   require a license. The API rejects public publishes without one.
   Private apps can omit the license.

3. **NEVER reuse a semantic version.** Each publish must use a unique
   version. Reusing a version results in a ConflictException. Plan
   version increments as part of the release pipeline.

4. **NEVER forget the SAM transform declaration.** The template must
   include `Transform: AWS::Serverless-2016-10-31`. Without it,
   `AWS::Serverless::*` types are not recognized and the deploy fails.

5. **NEVER deploy a nested application without CAPABILITY_AUTO_EXPAND.**
   Templates with `AWS::Serverless::Application` require this
   capability. CloudFormation rejects the change set without it.

6. **NEVER assume publishing makes an app deployable cross-account.**
   For private apps, you MUST add an application policy granting each
   consumer account. Without the policy, consumers get a 403.

7. **NEVER forget that the SAM transform auto-generates IAM roles.**
   Even if the template does not explicitly declare AWS::IAM::Role,
   the transform creates roles for functions with `Policies`.
   CAPABILITY_IAM is required.

8. **NEVER confuse SAR with AppRegistry.** SAR deploys serverless
   applications from SAM templates. AppRegistry groups existing
   resources for metadata. They are different services.

9. **NEVER assume deleting the CloudFormation stack deletes the SAR
   app.** The stack and the SAR catalog entry are separate. Delete
   both explicitly. Conversely, deleting the SAR app does not delete
   already-deployed stacks.

10. **NEVER upload the raw template.yaml (with local CodeUri) to SAR.**
    Always run `sam package` first to replace local CodeUri with S3
    URIs. Publishing the raw template means consumers cannot access
    the code.

## Output format

```text
SAR_APPLICATION: <application-name> (<semantic-version>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] SAM template: <template-file> (Transform: AWS::Serverless-2016-10-31)
  [✓|✗] README.md: present | MISSING (required for publish)
  [✓|✗] LICENSE: present | not required (private) | MISSING (required for public)
  [✓|✗] Packaging: sam package → S3 artifact <s3-uri>
  [✓|✗] Semantic version: <version> (SemVer format)
  [✓|✗] Sharing: Private | Private+Policy (<account-ids>) | Public
  [✓|✗] Application policy: granted (<account-ids>) | not needed (private) | public (implicit)
  [✓|✗] Capabilities: CAPABILITY_IAM [CAPABILITY_NAMED_IAM] [CAPABILITY_AUTO_EXPAND]
  [✓|✗] Parameters: <param-list> surfaced at deploy time
  [✓|✗] Nested applications: none | <child-app-ids>
  [✓|✗] Author profile: <author>, labels: <label-list>
  [✓|✗] Application ARN: arn:aws:serverlessrepo:<region>:<acct>:apps/<name>
VERIFICATION_COMMANDS:
  aws serverlessrepo get-application --application-id <arn> --region <region>
  aws cloudformation describe-stacks --stack-name <stack-name> --region <region>
```

### Worked example — private app with SAM deploy and cross-account policy

```text
SAR_APPLICATION: s3-file-processor (1.0.0)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] SAM template: template.yaml (Transform: AWS::Serverless-2016-10-31)
  [✓] README.md: present (S3 File Processor documentation)
  [✓] LICENSE: present (Apache-2.0)
  [✓] Packaging: sam package → s3://my-artifacts/s3-processor-1.0.0.zip
  [✓] Semantic version: 1.0.0
  [✓] Sharing: Private+Policy (granted to 999999999999)
  [✓] Application policy: PutApplicationPolicy → Principal: 999999999999, Action: CreateCloudFormationChangeSet
  [✓] Capabilities: CAPABILITY_IAM (transform auto-generates Lambda execution role)
  [✓] Parameters: BucketName (String, required), MemorySize (Number, default 256)
  [✓] Nested applications: none
  [✓] Author profile: Jacky Chan, labels: s3, lambda, event-driven
  [✓] Application ARN: arn:aws:serverlessrepo:us-east-1:123456789012:apps/s3-file-processor
VERIFICATION_COMMANDS:
  aws serverlessrepo get-application --application-id arn:aws:serverlessrepo:us-east-1:123456789012:apps/s3-file-processor --region us-east-1
  aws serverlessrepo get-application-policy --application-id arn:aws:serverlessrepo:us-east-1:123456789012:apps/s3-file-processor --region us-east-1
```

## Error handling

> Moved to [references/error-handling.md](references/error-handling.md#-createapplication-fails-with).
> Six failure modes: README required, ConflictException, 403 policy gap, missing CAPABILITY_AUTO_EXPAND, transform failed, artifact upload.

## References (load on demand)

- [advanced-patterns](references/advanced-patterns.md) — Mindset misconceptions, cross-dependency gotchas, deletion/cleanup, SAR vs AppRegistry, recent AWS features
- [error-handling](references/error-handling.md) — Six API failure modes: missing README, ConflictException, 403 policy gap, AUTO_EXPAND, transform failure, artifact upload
- [sam-transform-and-deploy](references/sam-transform-and-deploy.md) — Transform/deploy deep reference plus moved Step 1/2/3/7/9/10 template, packaging, and deploy CLI
- [sar-publishing-and-sharing](references/sar-publishing-and-sharing.md) — Publishing/sharing deep reference plus moved Step 4/5/6/11 versioning, sharing, policy, and author-profile CLI

## Domain

AWS CloudOps / AWS Serverless Application Repository Application
Publishing & Deployment.

## AWS documentation

- **Serverless Application Repository** — https://docs.aws.amazon.com/serverlessrepo/latest/devguide/what-is-serverlessrepo.html
- **Publishing applications** — https://docs.aws.amazon.com/serverlessrepo/latest/devguide/serverlessrepo-publishing-applications.html
- **Sharing applications** — https://docs.aws.amazon.com/serverlessrepo/latest/devguide/serverlessrepo-sharing-applications.html
- **Deploying applications** — https://docs.aws.amazon.com/serverlessrepo/latest/devguide/serverlessrepo-consuming-applications.html
- **SAM transform** — https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/transform.html
- **AWS::Serverless::Application** — https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/sam-resource-application.html
- **Application policies** — https://docs.aws.amazon.com/serverlessrepo/latest/devguide/serverlessrepo-how-to-use.html
- **SAM CLI reference** — https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-reference.html
- **Semantic versioning** — https://semver.org/
