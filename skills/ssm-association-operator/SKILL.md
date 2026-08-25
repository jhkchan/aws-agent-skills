---
name: ssm-association-operator
description: 'Operates AWS Systems Manager (SSM) State Manager associations with production defaults: association creation (document name, targets, schedule), association status (Success/Failed/Pending), compliance reporting, association versioning, output location (S3 bucket with KMS-encrypted SSE), rate control (max-concurrency and max-errors as integer counts, NOT percentages), target via resource tags (dynamic — new instances auto-included) vs instance IDs (static), association automation (apply on cron/rate schedule), association remediation on non-compliance, multi-document association, document-specific parameters, SSM document lifecycle (create/update/default version), and CloudWatch metrics for association execution. Emits an OPERATION_COMPLETED. Triggers: create ssm association, ssm state manager, ssm association schedule, ssm association rate control, ssm association targets, ssm association output s3, ssm association compliance, ssm association version, ssm document parameters, ssm association remediation.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with ssm access (and iam access for role/policy creation, s3 access for output bucket validation). Works with Terraform aws_ssm_association / aws_ssm_document resources and CloudFormation AWS::SSM::Association / AWS::SSM::Document templates.'
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Management
  task_type: operate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: OPERATION_COMPLETED | REVIEW_REQUIRED
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, systems-manager, ssm, state-manager, association, cloudops, operate, compliance, rate-control, ssm-document
  dependencies: aws-orchestrator
  keywords: aws, systems manager, ssm, state manager, association, create association, association schedule, association targets, rate control, max-concurrency, max-errors, compliance, association version, output location, ssm document, document lifecycle, remediation, tag targets, cloudops, operate
  when_to_use: Invoke when the user wants to create or operate an SSM State Manager association — apply a document (AWS-managed or custom) to targets on a schedule, target instances by tag (dynamic) or instance IDs (static), configure rate control (max-concurrency and max-errors as integer counts), route execution output to an S3 bucket, view association status and compliance, version an association, set up remediation when an association drifts to non-compliant, or run multi-document associations. Do NOT invoke for ad-hoc one-off command runs (use ssm-run-command skills), patch baseline creation (use ssm-patch-baseline-deployer), or session manager troubleshooting (use ssm-session-troubleshooter).
---

# SSM Association Operator

An AWS CloudOps agent skill that operates AWS Systems Manager (SSM)
State Manager associations with correct defaults. The skill walks the
operator through the document/target/schedule model, tag-vs-instanceID
targeting, integer rate control, S3 output with KMS-encrypted SSE,
compliance reporting, association versioning, and remediation on
non-compliance, captures the configuration, explains why each default
matters, and emits an OPERATION_COMPLETED checklist with copy-pasteable
verification commands.

## Activation keywords

create SSM association, SSM State Manager, SSM association schedule,
SSM association rate control, SSM association targets, SSM association
output S3, SSM association compliance, SSM association version, SSM
document parameters, SSM association remediation.

## STRICT output contract

When this skill is invoked with an SSM-association-operation request
(create an association, target instances by tag, schedule a document
run, configure rate control, route output to S3, set up remediation,
version an association, or report compliance status), the agent MUST
respond with the OPERATION_COMPLETED checklist defined in the "Output
format" section using the literal all-caps labels `SSM_ASSOCIATION:`,
`VERDICT:`, `CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface
the checklist with prose, headings, or disclaimers — emit the block as
the first lines of the response. This contract is what assertion-based
evals and downstream operations pipelines rely on; deviating from the
literal labels breaks automation silently.

If any prerequisite is missing or the configuration shows a material
gap (S3 output bucket without KMS, percentage-string rate control,
schedule without apply-at-creation, etc.), the verdict is
`REVIEW_REQUIRED` with a specific gap citation in the checklist (marked
`[!]`), and `OPERATION_COMPLETED` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before operating |
| Step 1 — Document/target/schedule model | Core association model |
| Step 2 — Targets: tag vs instance IDs | Targeting decision |
| Step 3 — Rate control (integer counts, NOT percentages) | Concurrency + error threshold |
| Step 4 — Schedule (cron/rate, apply-at-creation) | When associations run |
| Step 5 — Output location (S3 + KMS-encrypted SSE) | Execution artifacts |
| Step 6 — Association status and compliance | Success/Failed/Pending + compliance |
| Step 7 — Association versioning | Update + default version |
| Step 8 — Remediation on non-compliance | Auto-remediation wiring |
| Step 9 — Multi-document associations | Documents chaining |
| Step 10 — SSM document lifecycle | Create/update/default version |
| Step 11 — CloudWatch metrics | Observability |
| Step 12 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/rate-control-and-targets.md | Rate control + targeting detail |
| references/output-and-compliance.md | S3 output + compliance detail |

## Mindset

**One-line takeaway:** An SSM State Manager association applies a
document (AWS-managed or custom) to a set of targets on a schedule.
Targets specified by tag are DYNAMIC — new instances matching the tag
are picked up automatically on the next run. Targets specified by
instance ID are STATIC — new instances are NOT picked up until the
association is updated. Rate control uses `max-concurrency` and
`max-errors` as INTEGER COUNTS (e.g., `10` or `1`), NOT percentages.

Three misconceptions dominate SSM association misoperation:

- **"Rate control accepts percentages as the canonical form."** It
  does, but the integer count form is preferred for deterministic
  behavior across fleets of varying size. A `10%` value on a
  3-instance fleet rounds unpredictably; `max-concurrency: 1` is
  unambiguous. The skill always emits the integer form and flags
  percentage strings as REVIEW_REQUIRED.

- **"Tag-based targets behave the same as instance-ID targets."** They
  do not. Tag targets are dynamic: any instance that gains the tag
  (e.g., newly launched by Auto Scaling) is automatically picked up at
  the next association run. Instance-ID targets are static: the
  association only ever touches the IDs explicitly listed. For
  autoscaling fleets, ALWAYS use tag targets.

- **"The S3 output bucket just needs to exist."** It needs SSE enabled,
  and for production that means a customer-managed KMS key. SSM does
  not enforce SSE, but execution artifacts (stdout/stderr/scripts) can
  contain secrets; shipping them to an unencrypted bucket is a finding.
  The skill flags a missing KMS key as REVIEW_REQUIRED.

## Configuration dependency graph

SSM association configurations are NOT independent. The document must
exist before the association is created. The instance profile must
allow SSM before targets can run anything. Output S3 bucket policy
must allow the SSM service principal to write before output is
delivered. Use this graph to sequence operations.

| Configuration | Hard dependencies | Silent failure | Enables downstream |
|---|---|---|---|
| SSM document | document name exists in account or AWS-managed catalog | custom docs need a default version set before reference | the document body |
| Instance profile | target EC2 instances have AmazonSSMManagedInstanceCore | instances without the role show PingStatus: Inactive and are silently skipped | SSM agent reachability |
| Association (create) | document name; targets; schedule | does NOT run at creation unless `--apply-at-creation` is set | the association itself |
| Rate control | integer counts for max-concurrency and max-errors | percentage strings work but are size-dependent and ambiguous | safe rollout pace |
| Output S3 bucket | bucket exists; SSM service principal has s3:PutObject | without KMS key, output is unencrypted at rest; SSM silently drops output if bucket policy missing | execution artifacts |
| Schedule | cron or rate expression | `rate(30 minutes)` and `cron(0 30 * * * *)` are NOT interchangeable | automated runs |
| Compliance | association has executed at least once | non-compliant status only computed AFTER first run; before that = Pending | drift detection |
| Remediation | association exists; document supports idempotent apply | remediation re-applies document on non-compliance; non-idempotent docs cause side effects | auto-remediation |

**The integer-rate-control row is the one a baseline model misses.**
Many baseline answers emit `max-concurrency: "10%"` because the API
technically accepts percentage strings. The skill normalizes to
integer counts because that is the deterministic, fleet-size-
independent form. The S3-output-needs-KMS row is the second commonly
missed configuration.

## Expert heuristic: integer rate control vs percentage strings

→ Moved to [references/rate-control-and-targets.md](references/rate-control-and-targets.md) — integer-vs-percentage decision model and worst-case blast radius.

## Expert heuristic: tag targets vs instance-ID targets

→ Moved to [references/rate-control-and-targets.md](references/rate-control-and-targets.md) — tag-target vs instance-ID decision model.

## Expert heuristic: S3 output bucket encryption

→ Moved to [references/output-and-compliance.md](references/output-and-compliance.md) — S3 output bucket encryption requirements and silent-finding risk.

## Prerequisites (verify before operating)

Before emitting association commands, verify these prerequisites. If
any are missing, the verdict is **REVIEW_REQUIRED**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| SSM document exists | Association references a document name | `aws ssm describe-document --name <name>` |
| Default document version set | Custom documents need a default version | `aws ssm describe-document --name <name> --query 'Document.DefaultVersion'` |
| Target instances managed by SSM | Targets must have PingStatus: Online | `aws ssm describe-instance-information --filters Key=Tag:Environment,Values=[production]` |
| Output S3 bucket exists | Output location must be writable | `aws s3api head-bucket --bucket <bucket>` |
| KMS key for output bucket | SSE-KMS required for production | `aws s3api get-bucket-encryption --bucket <bucket>` |
| Schedule expression valid | Cron needs seconds field; rate needs units | Validate `cron(...)` or `rate(...)` syntax |

## Step 1 — Document/target/schedule model

An SSM State Manager association binds three things: a document, a set
of targets, and a schedule.

| Component | What it specifies | API field |
|---|---|---|
| Document | What to run (AWS-managed or custom) | `--name AWS-ApplyPatchBaseline` |
| Targets | Which instances to run on | `--targets Key=tag:Environment,Values=production` |
| Schedule | When to run | `--schedule-expression "rate(30 minutes)"` |
| Parameters | Document-specific inputs | `--parameters Operation=Install` |

**AWS-managed documents** include `AWS-ApplyPatchBaseline`,
`AWS-GatherSoftwareInventory`, `AWS-UpdateSSMAgent`,
`AWS-ConfigureCloudWatchOnEC2Instances`. **Custom documents** are
user-authored YAML/JSON defining a sequence of steps; they need a
default version set before they can be referenced.

## Step 2 — Targets: tag vs instance IDs

| Target type | Dynamic? | Use case | Example |
|---|---|---|---|
| Tag | Yes — new tagged instances auto-included | Auto Scaling fleets | `Key=tag:Environment,Values=production` |
| Instance IDs | No — only listed IDs targeted | Pet servers, one-off | `Key=InstanceIds,Values=i-aaa111,i-bbb222` |
| Resource group | Yes — membership rules | Complex grouping | `Key=ResourceGroups,Values=<rg-arn>` |

For any fleet with churn, ALWAYS use tag targets.

## Step 3 — Rate control (integer counts, NOT percentages)

```bash
aws ssm create-association \
  --name "AWS-ApplyPatchBaseline" \
  --targets "Key=tag:Environment,Values=production" \
  --schedule-expression "rate(30 minutes)" \
  --max-concurrency 10 \
  --max-errors 3 \
  --parameters "Operation=Install" \
  --output-location '{"S3Location":{"OutputS3BucketName":"my-ssm-output","OutputS3KeyPrefix":"ssm-output/","OutputS3Region":"us-east-1"}}' \
  --apply-at-creation \
  --region us-east-1
```

**Critical:** the integer form `10` is unambiguous across fleet sizes.
The percentage form `"10%"` rounds unpredictably in small fleets. The
skill normalizes to integers and flags percentage strings as
REVIEW_REQUIRED.

## Step 4 — Schedule (cron/rate, apply-at-creation)

| Expression | Format | Example | Notes |
|---|---|---|---|
| `rate` | `rate(<value> <units>)` | `rate(30 minutes)` | Min: 1 minute; no seconds |
| `cron` | `cron(<sec> <min> <hr> <dom> <mon> <dow> <year>)` | `cron(0 30 2 ? * * *)` | 6 required fields + optional year; AWS cron (NOT Unix) |

**Critical: AWS cron is NOT Unix cron.** AWS cron has 6 fields (with
optional 7th year), starting with SECONDS. Unix cron has 5 fields
starting with minutes. The skill always uses AWS cron syntax.

**Apply-at-creation:** by default, an association does NOT run when
created. It waits for the next scheduled tick. For first-run
validation, set `--apply-at-creation`. The skill always sets it.

## Step 5 — Output location (S3 + KMS-encrypted SSE)

```bash
aws ssm create-association \
  --name "AWS-ApplyPatchBaseline" \
  --targets "Key=tag:Environment,Values=production" \
  --schedule-expression "rate(30 minutes)" \
  --output-location '{
    "S3Location": {
      "OutputS3BucketName": "my-ssm-output",
      "OutputS3KeyPrefix": "ssm-output/",
      "OutputS3Region": "us-east-1"
    }
  }' \
  --region us-east-1
```

**Verify the bucket has KMS-encrypted SSE:**

```bash
aws s3api get-bucket-encryption --bucket my-ssm-output --region us-east-1
# Expected: ServerSideEncryptionConfiguration with SSE-KMS + KMSMasterKeyID
```

**Critical:** SSM does NOT enforce SSE on the output bucket. An
unencrypted bucket is a silent finding. The skill flags any output
bucket without a customer-managed KMS key as REVIEW_REQUIRED. The S3
bucket policy must allow the SSM service principal to `s3:PutObject`,
and the KMS key policy must allow SSM to `kms:GenerateDataKey`.

## Step 6 — Association status and compliance

| Status | Meaning | Action |
|---|---|---|
| `Success` | All targeted instances ran successfully | None |
| `Failed` | One or more instances errored; rate control may have stopped the run | Inspect per-instance output in S3 |
| `Pending` | Association created but not yet executed | Wait, or trigger with `--apply-at-creation` |
| `TimedOut` | Document execution exceeded timeout | Increase timeout or fix document |

```bash
# Association status + execution history
aws ssm describe-association --association-id "<id>" --region us-east-1
aws ssm describe-association-executions --association-id "<id>" --region us-east-1

# Compliance reporting
aws ssm list-compliance-items --filters "Key=ComplianceType,Values=Association" --region us-east-1
aws ssm list-resource-compliance-summaries --filters "Key=ComplianceType,Values=Association" --region us-east-1
```

## Step 7 — Association versioning

Each association update creates a new version (1, 2, 3, ...).

```bash
aws ssm update-association \
  --association-id "<id>" \
  --schedule-expression "rate(15 minutes)" \
  --region us-east-1

aws ssm list-association-versions --association-id "<id>" --region us-east-1
```

**Critical:** there is no built-in rollback command. To revert, read
the desired version's parameters from `list-association-versions` and
re-apply them via `update-association`.

## Step 8 — Remediation on non-compliance

When an association drifts to non-compliant, SSM can auto-remediate by
re-applying the document.

```text
NON_COMPLIANT detected
  → EventBridge rule pattern:
      source: [aws.ssm]
      detail-type: [Configuration Compliance State Change]
      detail.status: [NON_COMPLIANT]
  → Target: SSM Automation or Lambda → StartAssociationsOnce
  → SSM re-applies the document → compliance flips back
```

**Manual re-run:**

```bash
aws ssm start-associations-once --association-ids "<id>" --region us-east-1
```

**Critical:** remediation only works if the document is IDEMPOTENT. A
non-idempotent document (e.g., one that appends to a file) will cause
side effects on re-run. Always verify idempotency before wiring
remediation.

## Step 9 — Multi-document associations

A single association applies ONE document. To apply multiple documents
to the same targets, create SEPARATE associations, OR build a single
custom step-document that runs multiple steps in sequence:

```yaml
schemaVersion: '2.2'
name: Custom-ProvisionAndConfigure
mainSteps:
  - action: aws:runShellScript
    name: installPackage
    inputs:
      runCommand:
        - yum install -y httpd
  - action: aws:runShellScript
    name: configureService
    inputs:
      runCommand:
        - systemctl enable httpd
        - systemctl start httpd
```

Use a step-document when the steps have ordering dependencies. Use
separate associations when the documents are independent.

## Step 10 — SSM document lifecycle

```bash
# Create
aws ssm create-document --content file://doc.yaml --name "Custom-Harden" \
  --document-type Command --document-format YAML --region us-east-1

# Update (creates new version)
aws ssm update-document --content file://doc-v2.yaml --name "Custom-Harden" \
  --document-version "1" --region us-east-1

# Set default version (associations use the default version)
aws ssm update-document-default-version --name "Custom-Harden" \
  --document-version "2" --region us-east-1
```

**Critical:** an association referencing a custom document always uses
the document's DEFAULT VERSION. To pin an association to a specific
version, reference it explicitly: `Custom-HardenBaseline:2`.

## Step 11 — CloudWatch metrics

SSM emits metrics in the `AWS/SSM` namespace.

| Metric | Description |
|---|---|
| `AssociationSuccess` | Count of successful executions |
| `AssociationFailed` | Count of failed executions — alarm on spikes |
| `AssociationTimeout` | Count of timed-out executions |
| `AssociationCompliance` | 1=compliant, 0=non-compliant |

## Step 12 — Recent features

→ Moved to [references/advanced-patterns.md](references/advanced-patterns.md) — recent AWS features (2023-2026).

## NEVER do these things

1. **NEVER use percentage strings for rate control.**
   `max-concurrency: "10%"` behaves differently across fleet sizes.
   Use integer counts (`max-concurrency: 10`, `max-errors: 3`).

2. **NEVER use instance-ID targets for autoscaling fleets.** Instance
   IDs are static; new instances are NOT picked up. Use tag targets.

3. **NEVER configure an output S3 bucket without customer-managed
   KMS-encrypted SSE.** SSM does not enforce SSE; an unencrypted
   bucket is a silent finding.

4. **NEVER create an association without `--apply-at-creation` for the
   first run.** Otherwise it waits for the next scheduled tick.

5. **NEVER use Unix cron syntax.** AWS cron has 6 fields starting with
   SECONDS. `cron(0 30 2 ? * * *)` is AWS cron for 02:30 daily.

6. **NEVER wire remediation for a non-idempotent document.**
   Remediation re-applies the document; non-idempotent documents cause
   side effects on re-run.

7. **NEVER assume compliance status is computed before the first run.**
   A newly created association shows "Pending" until it executes at
   least once.

8. **NEVER update a custom document without setting a default
   version.** Associations reference the default version.

9. **NEVER assume the S3 output bucket policy is correct without
   testing.** SSM silently drops output if the bucket policy does not
   allow the SSM service principal to `s3:PutObject`.

10. **NEVER assume the association will run immediately after
    creation.** By default, the first run happens at the next
    scheduled execution.

## Output format

```text
SSM_ASSOCIATION: <association-name> (<association-id>)
VERDICT: OPERATION_COMPLETED | REVIEW_REQUIRED
CHECKLIST:
  [✓|!] Document: <document-name> (version <v|default>)
  [✓|!] Targets: <tag-key>=<values> (dynamic) | InstanceIds=<ids> (static)
  [✓|!] Schedule: <cron|rate expression>
  [✓|!] Apply-at-creation: ENABLED | DISABLED
  [✓|!] Rate control: max-concurrency=<N>, max-errors=<N> (integer form)
  [✓|!] Output S3: s3://<bucket>/<prefix> (SSE-KMS) | UNENCRYPTED [!]
  [✓|!] Parameters: <key=value list>
  [✓|!] Compliance: COMPLIANT | NON_COMPLIANT | PENDING (first run)
  [✓|!] Status: Success | Failed | Pending
  [✓|!] Association version: <v>
  [✓|!] CloudWatch alarm: <alarm-name or "none">
  [✓|!] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws ssm describe-association --association-id <association-id> --region <region>
  aws ssm describe-association-executions --association-id <association-id> --region <region>
  aws ssm list-compliance-items --filters Key=ComplianceType,Values=Association --region <region>
  aws s3api get-bucket-encryption --bucket <output-bucket> --region <region>
```

### Worked example — tag-targeted scheduled association with integer rate control and KMS-encrypted S3 output

```text
SSM_ASSOCIATION: PatchProductionFleet (a-1a2b3c4d5e6f7g8h9)
VERDICT: OPERATION_COMPLETED
CHECKLIST:
  [✓] Document: AWS-ApplyPatchBaseline (default version)
  [✓] Targets: tag:Environment=production (dynamic)
  [✓] Schedule: rate(30 minutes)
  [✓] Apply-at-creation: ENABLED
  [✓] Rate control: max-concurrency=10, max-errors=3 (integer form)
  [✓] Output S3: s3://my-ssm-output/ssm-output/ (SSE-KMS, key arn:aws:kms:us-east-1:123456789012:key/abc123)
  [✓] Parameters: Operation=Install, SnapshotId=latest
  [✓] Compliance: COMPLIANT
  [✓] Status: Success
  [✓] Association version: 3
  [✓] CloudWatch alarm: ssm-patch-failures-prod
  [✓] Tags: Environment=production, Owner=cloudops
VERIFICATION_COMMANDS:
  aws ssm describe-association --association-id a-1a2b3c4d5e6f7g8h9 --region us-east-1
  aws ssm describe-association-executions --association-id a-1a2b3c4d5e6f7g8h9 --region us-east-1
  aws ssm list-compliance-items --filters Key=ComplianceType,Values=Association --region us-east-1
  aws s3api get-bucket-encryption --bucket my-ssm-output --region us-east-1
```

## Error handling

→ Moved to [references/error-handling.md](references/error-handling.md) — six failure modes: zero targets, stuck Pending, output not delivered, Failed status, NON_COMPLIANT, rate-control stop.

## References (load on demand)

- [references/rate-control-and-targets.md](references/rate-control-and-targets.md) — pre-existing; extended with the integer-rate-control and tag-vs-instance-ID expert heuristics moved from SKILL.md.
- [references/output-and-compliance.md](references/output-and-compliance.md) — pre-existing; extended with the S3 output bucket encryption expert heuristic moved from SKILL.md.
- [references/advanced-patterns.md](references/advanced-patterns.md) — recent AWS features (2023-2026): association-level KMS, target-locations, calendar schedules, EventBridge triggers, compliance dashboard.
- [references/error-handling.md](references/error-handling.md) — error-handling deep dive: zero targets, Pending stall, S3 output drop, Failed runs, NON_COMPLIANT after success, rate-control stop.

## Domain

AWS CloudOps / AWS Systems Manager (SSM) State Manager Association
Operations & Compliance Management.

## AWS documentation

- **SSM State Manager** — https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-state.html
- **Creating associations** — https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-state-assoc.html
- **Targeting instances** — https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-state-target.html
- **Rate control** — https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-state-rate-control.html
- **Cron schedules** — https://docs.aws.amazon.com/systems-manager/latest/userguide/reference-cron-and-rate-expressions.html
- **S3 output** — https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-rc-output.html
- **Compliance** — https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-compliance.html
- **Association versions** — https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-state-association-versions.html
- **SSM documents** — https://docs.aws.amazon.com/systems-manager/latest/userguide/documents.html
- **CloudWatch metrics for SSM** — https://docs.aws.amazon.com/systems-manager/latest/userguide/monitoring-cloudwatch-metrics.html
