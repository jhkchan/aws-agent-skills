---
description: Provision AWS CodeArtifact repositories with production-grade configuration (domain creation, repository creation across formats — npm, pip, maven, nuget, cargo, rubygems, swift, generic; upstream repositories; external connections to public registries — npmjs, pypi, maven-central; cross-account domain sharing via RAM; repository IAM policies — read/write/consume; codeartifact login CLI for npm/pip/maven; package ingestion via copy-package-versions; lifecycle policies). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "codeartifact domain"
  - "codeartifact repository"
  - "create codeartifact"
  - "provision codeartifact"
  - "npm codeartifact"
  - "pip codeartifact"
  - "maven codeartifact"
  - "nuget codeartifact"
  - "cargo codeartifact"
  - "rubygems codeartifact"
  - "swift codeartifact"
  - "codeartifact upstream"
  - "codeartifact external connection"
  - "codeartifact login"
  - "codeartifact copy-package"
  - "codeartifact domain sharing"
  - "ram codeartifact"
  - "codeartifact iam policy"
  - "cross-account codeartifact"
  - "codeartifact lifecycle policy"
  - "codeartifact publish"
routes_to: codeartifact-repository-deployer
---

# /aws:deploy-codeartifact-repository

Activate the `codeartifact-repository-deployer` skill and provision an
AWS CodeArtifact domain or repository with production-grade
configuration.

## What it does

The skill walks a 10-step provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Create (or reuse) the domain
2. Create the repository
3. Configure external connections (public: npmjs, pypi, maven-central, ...)
4. Configure upstream repositories (internal-first, external-last)
5. Configure repository IAM policies (consume vs publish)
6. Wire CI builds via the `codeartifact login` CLI
7. Cross-account domain sharing via RAM
8. Package ingestion via `copy-package-versions`
9. Configure lifecycle policies (optional)
10. Tag, verify, and test the login

## When to use

- You want to create a CodeArtifact domain or repository with
  production defaults.
- You are configuring upstream repositories and external connections.
- You want to share a domain across AWS accounts (RAM resource share).
- You are setting up repository IAM (consume vs publish).
- You want to wire a CI build to CodeArtifact via the `login` CLI.
- You want to check for provisioning blockers (missing parent domain,
  external connection unavailable in Region, missing CI role).

## How to invoke

### Slash command

```
/aws:deploy-codeartifact-repository
```

Then provide: domain name (existing or new), repository name, package
format (npm / pip / maven / nuget / cargo / rubygems / swift / generic),
external connections, upstream chain, CI role ARN (consume), release
role ARN (publish), cross-account consumer account ID (if sharing),
and lifecycle preferences.

### Natural language

Any of these routes to the same skill:

- "create a codeartifact npm repository"
- "share a codeartifact domain with another account"
- "configure upstream repositories for codeartifact"
- "wire pip to codeartifact"
- "set up codeartifact login for maven"

### CLI routing

```bash
node cli/bin/cli.js route "deploy codeartifact repository"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The output checklist feeds into verification pipelines and downstream
skills (e.g., CI/CD pipeline automators that consume the CodeArtifact
login credentials, and IAM least-privilege auditors for repository
policy review).

## Example

```
You: /aws:deploy-codeartifact-repository

     Provision a CodeArtifact npm repository named shared-npm in
     us-east-1. Domain shared (existing). Associate public:npmjs
     external connection. Upstream to shared-internal. CI consume
     for ci-build role, publish for release-pipeline role. Use
     codeartifact login for npm. Account: 123456789012.

Skill:
  REPOSITORY: shared-npm
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓]      Domain — shared (existing, owner 123456789012)
    [✓]      Repository — shared-npm
    [✓]      Format — npm
    [✓]      Upstream chain — shared-internal -> external:npmjs
    [✓]      External connection — public:npmjs
    [✓]      Consume policy — arn:aws:iam::123456789012:role/ci-build
    [✓]      Publish policy — arn:aws:iam::123456789012:role/release-pipeline
  VERIFICATION_COMMANDS:
    aws codeartifact describe-domain --domain shared --domain-owner 123456789012
    aws codeartifact describe-repository --domain shared --repository shared-npm
    aws codeartifact list-external-connections --domain shared
    aws codeartifact get-repository-endpoint --domain shared --repository shared-npm --format npm
    aws codeartifact login --tool npm --repository shared-npm --domain shared --domain-owner 123456789012
```

## References

- Skill definition: `skills/codeartifact-repository-deployer/SKILL.md`
- Deployment CLI commands: `skills/codeartifact-repository-deployer/references/deployment-cli-commands.md`
- Upstreams and cross-account guide: `skills/codeartifact-repository-deployer/references/upstreams-and-cross-account-guide.md`
- Eval suite: `skills/codeartifact-repository-deployer/evals/evals.json`
