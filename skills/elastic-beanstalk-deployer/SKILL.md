---
name: elastic-beanstalk-deployer
description: 'Provisions AWS Elastic Beanstalk environments with production defaults: application creation, environment tier (web server vs worker), platform (Amazon Linux 2023, Node.js/Python/Java/Go/.NET), deployment policies (all at once, rolling, rolling with additional batch, immutable, traffic splitting), managed platform updates, enhanced health reporting, load balancer (ALB vs NLB), EC2 instance profile, service role, VPC configuration, security groups, auto scaling group, RDS integration, CNAME swap for blue-green, .ebextensions and .platform for infrastructure as code. Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating an Elastic Beanstalk environment, configuring blue-green with CNAME swap, setting up worker tier with SQS, or managing platform updates. Triggers: create elastic beanstalk environment, deploy beanstalk application, beanstalk blue-green cname swap, beanstalk worker tier sqs, beanstalk immutable deployment, ebextensions, beanstalk managed updates.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with elasticbeanstalk and iam access, plus S3 for application version source bundles. Works with Terraform aws_elastic_beanstalk_application / aws_elastic_beanstalk_environment resources and CloudFormation AWS::ElasticBeanstalk::Application / AWS::ElasticBeanstalk::Environment templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Compute
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, elastic-beanstalk, cloudops, deploy, compute, provisioning, blue-green, worker-tier, ebextensions, amazon-linux-2023, immutable-deployment
  dependencies: aws-orchestrator
  keywords: aws, elastic beanstalk, beanstalk, compute, cloudops, deploy, provisioning, blue-green, cname swap, worker tier, web server tier, ebextensions, platform, amazon linux 2023, immutable deployment, rolling deployment, managed updates, application version, environment tier
  when_to_use: Invoke when the user wants to create or configure an AWS Elastic Beanstalk application or environment (web server or worker tier), deploy an application version, configure blue-green deployment via CNAME swap, set up .ebextensions for infrastructure as code, choose a deployment policy, configure managed platform updates, integrate RDS, or manage the application version lifecycle. Do NOT invoke for Amazon ECS/EKS (use container skills), AWS App Runner (use apprunner skills), or EC2 auto scaling groups standalone (use EC2 skills).
---

# Elastic Beanstalk Deployer

An AWS CloudOps agent skill that provisions Elastic Beanstalk
applications and environments with correct defaults. The skill walks
the operator through application creation, environment tier selection
(web server vs worker), platform (Amazon Linux 2023 with managed
runtimes), deployment policy selection, managed platform updates,
enhanced health reporting, load balancer choice, instance profile and
service role setup, VPC and security group configuration, auto scaling,
RDS integration, .ebextensions and .platform hooks, CNAME swap for
blue-green, and application version lifecycle management, captures
architecture decisions, explains why each default matters, and emits
a READY_TO_DEPLOY checklist with copy-pasteable verification commands.

## Activation keywords

create Elastic Beanstalk environment, deploy Beanstalk application,
Beanstalk blue-green CNAME swap, Beanstalk worker tier SQS, Beanstalk
immutable deployment, .ebextensions, Beanstalk managed updates,
Beanstalk platform Amazon Linux 2023, Beanstalk deployment policy,
Beanstalk enhanced health reporting.

## STRICT output contract

When this skill is invoked with an Elastic-Beanstalk-provisioning
request (create an environment, deploy an application version, set up
blue-green with CNAME swap, configure worker tier, choose a deployment
policy, or a partial configuration), the agent MUST respond with the
READY_TO_DEPLOY checklist defined in the "Output format" section using
the literal all-caps labels `ELASTIC_BEANSTALK:`, `VERDICT:`,
`CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface the
checklist with prose, headings, or disclaimers — emit the block as the
first lines of the response. This contract is what assertion-based
evals and downstream provisioning pipelines rely on; deviating from
the literal labels breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Application and environment model | Core Beanstalk model |
| Step 2 — Environment tier (web server vs worker) | Tier selection |
| Step 3 — Platform (Amazon Linux 2023, runtimes) | Platform branch |
| Step 4 — Deployment policies | Deployment strategy |
| Step 5 — Managed platform updates | Patching cadence |
| Step 6 — Enhanced health reporting | Health monitoring |
| Step 7 — Load balancer (ALB vs NLB) | LB selection |
| Step 8 — Instance profile and service role | IAM roles |
| Step 9 — VPC, subnets, security groups | Network placement |
| Step 10 — Auto scaling group | Capacity |
| Step 11 — .ebextensions and .platform | Infrastructure as code |
| Step 12 — RDS integration | Database attach |
| Step 13 — CNAME swap for blue-green | Zero-downtime cutover |
| Step 14 — Application version lifecycle | Version management |
| Step 15 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/deployment-policies.md | Deployment policy detail |
| references/ebextensions-and-platforms.md | .ebextensions + platform detail |

## Mindset

**One-line takeaway:** Elastic Beanstalk is a managed PaaS that
provisions an entire application stack (ELB + ASG + EC2 + deployment
pipeline) from a source bundle. The environment tier (web server vs
worker) determines whether the ELB serves HTTP traffic or the SQS
daemon pulls messages. The deployment policy determines the trade-off
between deployment speed and availability during the cutover.

Three misconceptions dominate Elastic Beanstalk misdesign at
provisioning time:

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Mindset misconceptions".
> Load when: you need the complete argument behind the three Beanstalk misdesign misconceptions.

## Configuration dependency graph (novel heuristic)

Elastic Beanstalk configurations are NOT independent. The service role
must exist before the environment can manage ELB/ASG on your behalf.
The instance profile must exist before EC2 instances can assume it.
The platform branch must be compatible with the solution stack. Use
this graph to sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Service role | IAM trust policy allowing `elasticbeanstalk.amazonaws.com` | environment creation FAILS if the service role lacks `AWSElasticBeanstalkManagedRole` or equivalent inline permissions | ELB, ASG, CloudWatch management by Beanstalk |
| Instance profile | IAM role with EC2 trust policy + S3 read for source bundle | EC2 instances launch but CANNOT pull the application version from S3; deployment appears stuck in "Pending" | application code deployment to each instance |
| Platform / solution stack | solution stack name must match an available Beanstalk platform ARN | using a deprecated platform (Amazon Linux 2 AMI) silently deploys on EOL branch; must use Amazon Linux 2023 | runtime (Node.js, Python, Java, Go, .NET) |
| Load balancer scheme | VPC has public subnets for internet-facing; private subnets for internal | NLB is NOT supported on all platform branches; Docker multi-container requires ALB | traffic distribution to EC2 instances |
| Deployment policy | ALB required for traffic splitting; immutable requires extra capacity | all-at-once causes full downtime if the new version is broken | cutover strategy and blast radius |
| Worker tier | SQS queue ARN required; environment tier must be `SQS/HTTP` | without `aws:elasticbeanstalk:sqsd` namespace config, the SQS daemon does not start | background message processing |
| .ebextensions | source bundle must include `.ebextensions/*.config` in the correct path | syntax errors cause the entire deployment to fail; ordering is lexicographic | infrastructure as code (RDS, DynamoDB, custom resources) |
| CNAME swap | BOTH environments must be `Ready` and `Green`/`Blue` health | swapping CNAMEs on an environment that is still launching causes DNS to point at a non-functional endpoint | blue-green zero-downtime cutover |
| Managed platform updates | must not conflict with deployment window | managed updates and deployments can conflict; managed updates are suppressed during an active deployment | automated patching and platform minor version upgrades |

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Configuration dependency graph".
> Load when: sequencing the service role / instance profile / platform / LB / worker-tier dependencies.

## Expert heuristic: immutable deployment for zero downtime

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Expert heuristic: immutable deployment".
> Load when: choosing a deployment policy by blast radius; includes the decision tree.

## Expert heuristic: .ebextensions for infrastructure as code

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Expert heuristic: .ebextensions".
> Load when: authoring .ebextensions IaC (directory layout, option_settings/Resources/files/commands).

## Expert heuristic: CNAME swap for blue-green

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Expert heuristic: CNAME swap".
> Load when: running the blue-green swap flow and reasoning about DNS TTL overlap.

## Expert heuristic: .ebextensions YAML syntax gotchas

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Expert heuristic: .ebextensions YAML syntax gotchas".
> Load when: a .config file is silently skipped or a deploy fails with no clear error.

## Expert heuristic: worker tier SQS visibility timeout auto-configuration

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Expert heuristic: worker tier SQS visibility timeout auto-configuration".
> Load when: configuring worker-tier SQS visibility timeout, HTTP timeout, or DLQ behavior.

## Expert heuristic: .platform/hooks vs .ebextensions ordering

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Expert heuristic: .platform/hooks vs .ebextensions ordering".
> Load when: mixing .ebextensions and .platform/hooks or debugging hook phase ordering.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Service role exists | Beanstalk needs `aws-elasticbeanstalk-service-role` to manage ELB/ASG | `aws iam get-role --role-name aws-elasticbeanstalk-service-role` |
| Instance profile exists | EC2 instances need a profile to pull the source bundle | `aws iam get-instance-profile --instance-profile-name aws-elasticbeanstalk-ec2-role` |
| S3 bucket for source bundle | Application version must be uploaded to S3 first | `aws s3 ls s3://<bucket>/<key>` |
| Solution stack available | Must match a valid platform ARN | `aws elasticbeanstalk list-available-solution-stacks` |
| VPC and subnets identified | Environment needs subnets for EC2 and ELB | `aws ec2 describe-subnets` |
| Security group(s) identified | EC2 and ELB need security groups | `aws ec2 describe-security-groups` |
| Application exists (or will be created) | Environments belong to an application | `aws elasticbeanstalk describe-applications` |
| SQS queue (for worker tier) | Worker environments need an SQS queue ARN | `aws sqs get-queue-url --queue-name <name>` |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Application and environment model

Elastic Beanstalk organizes resources into applications and
environments. An application is a logical container; environments are
deployable instances of the application.

| Entity | Purpose | API call |
|---|---|---|
| Application | Container for environments, versions, configurations | `create-application` |
| Application version | A specific source bundle in S3, labeled and deployable | `create-application-version` |
| Environment | A running deployment (web server or worker tier) | `create-environment` |
| Configuration template | Saved configuration for reuse across environments | `create-configuration-template` |

**Typical flow:** create application, upload source bundle to S3,
create application version, create environment using that version.

## Step 2 — Environment tier (web server vs worker)

| Feature | Web server tier | Worker tier |
|---|---|---|
| Traffic model | HTTP requests via ELB | Messages pulled from SQS queue |
| Load balancer | ALB or NLB (required for multi-instance) | No ELB (SQS daemon on each instance) |
| Entry point | nginx/Apache forwards to app | SQS daemon posts body to localhost |
| Health checks | ELB health check + enhanced health | Enhanced health (no ELB health check) |
| Auto scaling trigger | CPU, request count, latency | Queue depth (ApproximateNumberOfMessages) |
| Tier name | `WebServer` | `Worker` |

**Worker tier specifics:** the SQS daemon polls the configured queue,
POSTs each message body to the application's HTTP endpoint on
`localhost:5000` (configurable), and deletes the message on 200 OK.
On 4xx/5xx, the message is retried up to `maxReceiveCount`, then sent
to a dead-letter queue.

## Step 3 — Platform (Amazon Linux 2023, runtimes)

Beanstalk platforms are versioned AMIs with a managed runtime stack.
Amazon Linux 2023 (AL2023) is the current generation platform.

| Runtime | Solution stack example (AL2023) |
|---|---|
| Node.js | `64bit Amazon Linux 2023 v6.0.4 running Node.js 20` |
| Python | `64bit Amazon Linux 2023 v6.0.4 running Python 3.11` |
| Java | `64bit Amazon Linux 2023 v6.0.4 running Corretto 21` |
| Go | `64bit Amazon Linux 2023 v6.0.4 running Go 1.21` |
| .NET | `64bit Amazon Linux 2023 v6.0.4 running .NET 8` |

**Platform branch:** each runtime has a platform branch that receives
managed updates (security patches, minor version bumps) within its
lifecycle.

**Deprecation:** Amazon Linux 2 (AL2) platform branches are in
deprecation. New environments MUST use Amazon Linux 2023 branches.

## Step 4 — Deployment policies

| Policy | How it works | Downtime | Cost during deploy | Best for |
|---|---|---|---|---|
| All at once | Deploys to all instances simultaneously | Full fleet during deploy | No extra | Dev, testing |
| Rolling | Deploys in batches; takes batch out of service | Reduced capacity per batch | No extra | Production (cost-sensitive) |
| Rolling + additional batch | Spins up temp instances, deploys in batches | No capacity loss | Temp instances | Production (balanced) |
| Immutable | Launches fresh ASG with new version, swaps when healthy | None (old fleet serves during deploy) | Double capacity | Production (safest) |
| Traffic splitting | Routes a percentage of traffic to new version via ALB | None; canary-style | Temp instances | Production (canary) |

**Immutable** is the recommended default for production environments.
It provides the safest cutover: the old fleet remains untouched until
the new fleet passes health checks.

**Traffic splitting** requires an ALB and supports configurable
percentage (e.g., 10% canary for 5 minutes, then 100%). If health
checks fail during the canary window, Beanstalk rolls back
automatically.

## Step 5 — Managed platform updates

Managed platform updates apply minor version patches and security fixes
to the platform within a configurable window.

> **Moved verbatim** → [references/worked-examples.md](references/worked-examples.md) § "Step 5".
> Load when: enabling managed updates and setting the maintenance window.

Managed updates are suppressed during an active deployment. Schedule
deployments outside the managed update window to avoid conflicts.

## Step 6 — Enhanced health reporting

Enhanced health reporting provides detailed metrics (CPU, latency,
request count, status codes) aggregated from EC2 instances and the ELB.

> **Moved verbatim** → [references/worked-examples.md](references/worked-examples.md) § "Step 6".
> Load when: switching an environment to enhanced health reporting.

Enhanced health is REQUIRED for blue-green CNAME swap health checks
and for managed platform updates to work correctly.

## Step 7 — Load balancer (ALB vs NLB)

| Feature | ALB | NLB |
|---|---|---|
| Protocol | HTTP/HTTPS | TCP/UDP/TLS |
| Health check | HTTP path | TCP port |
| Traffic splitting | Supported | NOT supported |
| Sticky sessions | Cookie-based | Source IP (limited) |
| WebSocket | Supported | N/A (TCP passthrough) |
| Cost | LCU-based | Per-hour + per-GB |

ALB is the default and supports all deployment policies including
traffic splitting. NLB is for TCP-based workloads or ultra-low-latency
requirements where HTTP features are not needed. **Single-instance**
environments have no ELB — the EC2 instance is directly exposed.

## Step 8 — Instance profile and service role

These are TWO separate IAM roles with distinct purposes.

**Service role** (assumed BY Beanstalk): must have trust policy
allowing `elasticbeanstalk.amazonaws.com` and the
`AWSElasticBeanstalkManagedRole` managed policy attached. This role
manages ELB, ASG, and CloudWatch resources on your behalf.

**Instance profile** (assumed BY EC2 instances): must have trust policy
allowing `ec2.amazonaws.com`, the `AWSElasticBeanstalkWebTier` managed
policy (includes S3 read for source bundles), and be attached as an
instance profile.

> **Moved verbatim** → [references/diagnostic-commands.md](references/diagnostic-commands.md) § "IAM pre-flight verification commands".
> Load when: verifying the service role and instance profile before create-environment.

**Critical:** the instance profile MUST have S3 read access to the
bucket where the source bundle is stored. Without it, EC2 instances
launch but cannot pull the application code — the deployment hangs in
"Pending" indefinitely.

## Step 9 — VPC, subnets, security groups

For VPC-mode environments, specify public and private subnets and
security groups:

> **Moved verbatim** → [references/worked-examples.md](references/worked-examples.md) § "Step 9".
> Load when: launching the environment into a specific VPC/subnets/security groups.

For load-balanced environments, the ELB and EC2 instances should be in
the same subnets (or ELB in public subnets, EC2 in private subnets).
For single-instance, the EC2 instance needs a public IP or a NAT
gateway for internet egress.

## Step 10 — Auto scaling group

Beanstalk provisions an ASG behind the environment. Configure min/max
size and scaling triggers:

> **Moved verbatim** → [references/worked-examples.md](references/worked-examples.md) § "Step 10".
> Load when: setting ASG min/max and CPU trigger thresholds.

For worker tier, scale on SQS queue depth: use
`MeasureName=ApproximateNumberOfMessagesVisible` with lower/upper
thresholds based on expected processing time.

## Step 11 — .ebextensions and .platform

.ebextensions provide infrastructure as code within the source bundle.

> **Moved verbatim** → [references/ebextensions-and-platforms.md](references/ebextensions-and-platforms.md) § "Step 11 .ebextensions config examples".
> Load when: writing the 01-options / 02-rds / 03-hooks .config files.

**`.platform/hooks/`** is the AL2023-native hook directory, organized by phase: `prebuild/`, `predeploy/`, `postdeploy/`.

## Step 12 — RDS integration

Beanstalk can attach an RDS instance via .ebextensions. This is
convenient for development but has lifecycle implications.

| Feature | Attached RDS | External RDS |
|---|---|---|
| Creation | Created with environment via .ebextensions | Pre-existing RDS instance |
| Lifecycle | Terminated WITH environment (unless Retain) | Independent lifecycle |
| Connection string | Passed as environment properties | Pass manually as env property |
| Best for | Dev, testing | Production (separate lifecycle) |

**Critical:** attached RDS is terminated when the environment is
terminated, UNLESS `DeletionPolicy: Retain` is set. For production, use
an external RDS instance and pass the connection string as an
environment property.

## Step 13 — CNAME swap for blue-green

> **Moved verbatim** → [references/worked-examples.md](references/worked-examples.md) § "Step 13".
> Load when: executing the green→swap→verify→terminate blue sequence.

## Step 14 — Application version lifecycle

Application versions accumulate over time. Beanstalk has a per-
application version limit (500 by default, soft limit).

> **Moved verbatim** → [references/worked-examples.md](references/worked-examples.md) § "Step 14".
> Load when: creating application versions or applying the max-count lifecycle policy.

## Step 15 — Recent features

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Recent AWS features 2023-2026".
> Load when: deciding on Graviton, traffic splitting, AL2023 metrics, or AbortEnvironmentUpdate.

## NEVER do these things

1. **NEVER use all-at-once deployment for production environments.**
   All-at-once takes the entire fleet out of service simultaneously.
   If the new version is broken, 100% of traffic fails. Use immutable
   or rolling-with-additional-batch for production.

2. **NEVER create an environment without a service role and instance
   profile.** The service role is required for Beanstalk to manage
   ELB/ASG. The instance profile is required for EC2 instances to pull
   the source bundle. Without either, the environment creation or
   deployment fails or hangs.

3. **NEVER use Amazon Linux 2 (AL2) platform branches for new
   environments.** AL2 is in deprecation. New environments MUST use
   Amazon Linux 2023 (AL2023) platform branches.

4. **NEVER rely on attached RDS for production without a Retain
   deletion policy.** Attached RDS is terminated with the environment.
   Set `DeletionPolicy: Retain` in the .ebextensions resource, or use
   an external RDS instance for production databases.

5. **NEVER assume CNAME swap is instant for all clients.** The swap
   is atomic at the DNS level, but DNS TTL means some clients hit the
   old environment for up to 60 seconds. Plan for this overlap.

6. **NEVER ignore .ebextensions ordering.** Directives run in
   lexicographic order. A resource created in `02-config.config` cannot
   be referenced in `01-config.config`. Prefix files with `NN-` to
   enforce order.

7. **NEVER use an NLB with traffic splitting deployment policy.**
   Traffic splitting requires an ALB. If the environment uses an NLB
   or single-instance (no ELB), traffic splitting is not available.

8. **NEVER assume managed platform updates and deployments can run
   simultaneously.** Managed updates are suppressed during an active
   deployment. Schedule deployments outside the managed update window.

9. **NEVER leave application versions accumulating without a lifecycle
   policy.** Beanstalk has a per-application version limit (500 by
   default). Set a lifecycle policy to automatically prune old versions.

10. **NEVER forget the SQS queue configuration for worker tier.**
    Without `aws:elasticbeanstalk:sqsd` namespace options, the SQS
    daemon does not start and messages are never processed.

## Output format

```text
ELASTIC_BEANSTALK: <application-name> / <environment-name> (<environment-id>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Application: <application-name>
  [✓|✗] Environment: <environment-name> (<tier>: WebServer | Worker)
  [✓|✗] Platform: <solution-stack-name> (Amazon Linux 2023)
  [✓|✗] Application version: <version-label> (s3://<bucket>/<key>)
  [✓|✗] Service role: <role-name> (AWSElasticBeanstalkManagedRole attached)
  [✓|✗] Instance profile: <profile-name> (S3 read + WebTier policy)
  [✓|✗] Load balancer: ALB | NLB | Single-instance (no ELB)
  [✓|✗] Deployment policy: All-at-once | Rolling | Rolling+batch | Immutable | Traffic-splitting
  [✓|✗] Enhanced health: enabled | basic
  [✓|✗] Managed updates: enabled (<window>) | disabled
  [✓|✗] VPC: <vpc-id> (subnets: <subnet-list>)
  [✓|✗] Security groups: <sg-list>
  [✓|✗] ASG: min=<n>, max=<n> (trigger: <metric>)
  [✓|✗] .ebextensions: <file-list> | none
  [✓|✗] RDS: attached (<instance-class>) | external | none
  [✓|✗] CNAME: <cname-prefix>.<region>.elasticbeanstalk.com
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws elasticbeanstalk describe-environments --environment-names <env-name>
  aws elasticbeanstalk describe-environment-health --environment-name <env-name>
  aws elasticbeanstalk describe-configuration-settings --environment-name <env-name>
```

### Worked example — web server environment with immutable deployment

```text
ELASTIC_BEANSTALK: myapp / myapp-prod (e-xxx123)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Application: myapp
  [✓] Environment: myapp-prod (WebServer tier)
  [✓] Platform: 64bit Amazon Linux 2023 v6.0.4 running Node.js 20
  [✓] Application version: v2 (s3://myapp-deploy/app-v2.zip)
  [✓] Service role: aws-elasticbeanstalk-service-role (AWSElasticBeanstalkManagedRole)
  [✓] Instance profile: aws-elasticbeanstalk-ec2-role (AWSElasticBeanstalkWebTier + S3 read)
  [✓] Load balancer: ALB
  [✓] Deployment policy: Immutable
  [✓] Enhanced health: enabled
  [✓] Managed updates: enabled (Mon:02:00 UTC, minor level)
  [✓] VPC: vpc-aaa11122 (subnets: subnet-aaa, subnet-bbb)
  [✓] Security groups: sg-app-prod
  [✓] ASG: min=2, max=8 (trigger: CPUUtilization 20-80%)
  [✓] .ebextensions: 01-options.config, 02-rds.config, 03-hooks.config
  [✓] RDS: external (db-prof-xxx, connection via DATABASE_URL)
  [✓] CNAME: myapp-prod.us-east-1.elasticbeanstalk.com
  [✓] Tags: Environment=production, App=myapp
VERIFICATION_COMMANDS:
  aws elasticbeanstalk describe-environments --environment-names myapp-prod
  aws elasticbeanstalk describe-environment-health --environment-name myapp-prod
  aws elasticbeanstalk describe-configuration-settings --environment-name myapp-prod
```

## Error handling

> **Moved verbatim** → [references/error-handling.md](references/error-handling.md) § "Error handling".
> Load when: a launch is stuck, a deploy fails, health is Red, a swap fails, or updates never apply.

## References (load on demand)

- [references/worked-examples.md](references/worked-examples.md) — full command sequences: CNAME-swap blue-green, version lifecycle, VPC launch, ASG triggers, managed updates, enhanced health
- [references/error-handling.md](references/error-handling.md) — deployment failure triage: stuck launches, failed deploys, Red health, swap failures
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — pre-flight IAM verification (service role, instance profile)
- [references/advanced-patterns.md](references/advanced-patterns.md) — expert heuristics (immutable deploy, .ebextensions IaC, CNAME swap, YAML gotchas, worker SQS, hook ordering), dependency-graph deep dive, misconceptions, recent AWS features
- [references/deployment-policies.md](references/deployment-policies.md) — deployment policy decision detail
- [references/ebextensions-and-platforms.md](references/ebextensions-and-platforms.md) — .ebextensions + platform detail, incl. Step 11 config examples

## Domain

AWS CloudOps / Elastic Beanstalk Application & Environment Provisioning.

## AWS documentation

- **Elastic Beanstalk Developer Guide** — https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/Welcome.html
- **Creating an environment** — https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/using-features.environments.html
- **Deployment policies** — https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/using-features.rolling-version-deploy.html
- **.ebextensions** — https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/ebextensions.html
- **Environment tiers** — https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/using-features-managing-env-tiers.html
- **Enhanced health reporting** — https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/health-enhanced-status.html
- **Managed platform updates** — https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/environment-platform-update-managed.html
- **CNAME swap** — https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/using-features.CNAMESwap.html
- **Amazon Linux 2023 platforms** — https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/platforms.al2023.html
