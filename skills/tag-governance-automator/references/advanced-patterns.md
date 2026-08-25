# Advanced Patterns — Tag Governance Automator

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Step 0: Expert knowledge — non-obvious TagPolicy + tagging behaviors

These behaviors change the governance design if ignored:

- **Tag policies are enforced only on resource types listed in
  `enforced_for`.** A policy with an `Environment` tag key but
  `enforced_for: ["ec2:instance"]` does NOT enforce on S3 buckets,
  Lambda functions, RDS instances, or any other type. Operators
  frequently publish a policy and assume it covers the full fleet.

- **`enforced_for` uses `service:resource-type` notation** (e.g.,
  `ec2:instance`, `s3:bucket`, `lambda:function`, `rds:db-instance`,
  `dynamodb:table`). A typo (`ec2:Instance` vs `ec2:instance`) silently
  disables enforcement. Always verify with the AWS service authorization
  reference.

- **Tag policies block `CreateTags` / `Put*Tagging` / `TagResource`
  calls that violate the policy** — they do NOT retroactively fix
  existing resources. Resources tagged before the policy was attached
  remain non-compliant until remediated. Use Config + remediation
  (Step 7) to handle the backlog.

- **Resource Groups Tagging API `tag-resources` is NOT atomic.** The
  API returns a `FailedResourcesMap` for resources that could not be
  tagged (permission denied, throttled, wrong region). Always check
  the response — a "successful" call may have partially failed.

- **`resourcegroupstaggingapi get-resources` is region-scoped.** To
  inventory resources across all regions, iterate over
  `ec2 describe-regions` and aggregate. There is no native global
  tag query. A common pitfall is querying only `us-east-1` and
  reporting 100% compliance.

- **Config `required-tags` managed rule checks up to 5 tag keys per
  rule.** If you require more than 5 tags, deploy multiple required-tags
  rules (e.g., `required-tags-core` for 5 keys, `required-tags-ext` for
  the next 5). A single rule silently ignores keys beyond the 5th.

- **Cost allocation tag activation is per-account (not org-level).**
  In an Organization with 50 member accounts, activating the `Owner`
  tag for cost reporting requires activating it in EACH account's
  Billing settings (or via the org payer account's consolidated
  activation if enabled). A single `ce update-cost-allocation-tags-status`
  call applies to the payer account only.

- **ABAC `aws:PrincipalTag` is resolved at session creation.** If you
  change a user's `Team` tag in IAM, existing sessions still carry the
  old value until the session expires or is revoked. ABAC policy
  changes and principal tag changes must be coordinated with session
  refresh.

- **`aws:RequestTag` is only valid on create/tag API calls** (RunInstances,
  CreateBucket, CreateFunction, CreateTags). It cannot be used in a
  policy that governs read operations. A common mistake is writing
  `aws:RequestTag/Environment` into a `Deny` statement for `s3:GetObject`
  — the condition silently never matches.

- **SSM Automation `aws-ApplyEC2Tags` style runbooks do not exist as a
  single managed document for all resource types.** EC2 uses
  `ec2:CreateTags`, S3 uses `s3:PutBucketTagging`, Lambda uses
  `lambda:TagResource`, RDS uses `rds:AddTagsToResource`. A custom
  SSM Automation document must branch by resource type OR you deploy
  one document per resource type.

- **Tag policies do NOT enforce on AWS-generated tags** (e.g.,
  `aws:cloudformation:stack-name`, `aws:createdBy`). These are system
  tags; user-defined tag policies apply only to user-supplied tag keys.

## Step 4: Resource Groups Tagging API bulk operations

For bulk tagging / untagging / inventory across resource types and
regions. The Tagging API normalizes the tagging interface across 30+
AWS services.

Bulk tag resources:

```bash
aws resourcegroupstaggingapi tag-resources \
  --resource-arn-list \
    "arn:aws:ec2:us-east-1:111111111111:instance/i-0abc" \
    "arn:aws:s3:::my-bucket" \
    "arn:aws:lambda:us-east-1:111111111111:function:my-fn" \
  --tags Owner=platform-team,Environment=prod,CostCenter=cc-1001
# Returns: { "FailedResourcesMap": {} } on success
```

Bulk untag:

```bash
aws resourcegroupstaggingapi untag-resources \
  --resource-arn-list "arn:aws:s3:::my-bucket" \
  --tag-keys Owner Environment
```

Find resources by tag (multi-region iteration):

```bash
for region in $(aws ec2 describe-regions --query 'Regions[].RegionName' --output text); do
  aws resourcegroupstaggingapi get-resources \
    --tag-filters Key=Environment,Values=["prod"] \
    --resources-per-page 100 \
    --region "$region"
done > all-prod-resources.jsonl
```

List all tag keys and values in an account:

```bash
aws resourcegroupstaggingapi get-tag-keys
aws resourcegroupstaggingapi get-tag-values --key Environment
```

**Critical:** always check `FailedResourcesMap` in the response. A
non-empty map means some resources were not tagged (permission,
throttling, non-existent ARN). Log and retry the failed ARNs.

**Console alternative — Tag Editor:** for one-off bulk tag editing
across regions without scripting, use the AWS Tag Editor console
(Resource Groups & Tag Editor → Tag Editor). It supports
region-scoped resource discovery, multi-select, and bulk add/replace/
delete tag operations across resource types. Tag Editor is a manual
operator tool — it is NOT automatable via API and should NOT be the
primary mechanism for fleet-wide governance. Use it for ad-hoc
remediation sprints or initial backfill; use the Tagging API
(above) and Config remediation (Step 7) for ongoing automation.

## Step 5: Wire Config `required-tags` managed rule

The Config managed rule `required-tags` checks that specified tag keys
exist on resources. It is the enforcement complement to the advisory
tag policy.

Deploy a required-tags rule via CLI:

```bash
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "required-tags-core",
    "Source": {
      "Owner": "AWS",
      "SourceIdentifier": "REQUIRED_TAGS"
    },
    "Scope": {
      "ComplianceResourceTypes": [
        "AWS::EC2::Instance",
        "AWS::S3::Bucket",
        "AWS::Lambda::Function",
        "AWS::RDS::DBInstance"
      ]
    },
    "InputParameters": "{\"tag1Key\":\"Environment\",\"tag2Key\":\"Owner\",\"tag3Key\":\"Project\",\"tag4Key\":\"CostCenter\",\"tag5Key\":\"Application\"}"
  }'
```

If you need more than 5 keys, deploy a second rule:

```bash
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "required-tags-ext",
    "Source": {"Owner": "AWS", "SourceIdentifier": "REQUIRED_TAGS"},
    "Scope": {"ComplianceResourceTypes": ["AWS::EC2::Instance", "AWS::S3::Bucket"]},
    "InputParameters": "{\"tag1Key\":\"Backup:Required\",\"tag2Key\":\"ComplianceTier\",\"tag3Key\":\"DataClassification\"}"
  }'
```

Verify:

```bash
aws configservice describe-config-rules \
  --config-rule-names required-tags-core required-tags-ext

aws configservice get-compliance-details-by-config-rule \
  --config-rule-name required-tags-core \
  --compliance-types NON_COMPLIANT --limit 10
```

## Step 6: Security Hub integration

Tag compliance findings flow into Security Hub via the Config →
Security Hub integration pipe. The relevant control in Foundational
Security Best Practices (FSBP) is `[EC2.26]`, `[S3.10]`, `[Lambda.3]`
and similar — each checks for required tags on the resource type.

Enable Security Hub with FSBP:

```bash
aws securityhub enable-security-hub \
  --enable-default-standards
```

Verify the tag-related controls are active:

```bash
aws securityhub describe-standards-controls \
  --standards-subscription-arn arn:aws:securityhub:us-east-1:111111111111:standards/aws-foundational-security-best-practices/v/1.0.0 \
  --query 'Controls[?contains(ControlId, `Tag`)]'
```

For custom tag-compliance findings (beyond FSBP), import a finding
directly:

```bash
aws securityhub batch-import-findings \
  --findings '[{
    "SchemaVersion": "2018-10-08",
    "Id": "tag-violation/i-0abc123",
    "ProductArn": "arn:aws:securityhub:us-east-1:111111111111:product/111111111111/default",
    "GeneratorId": "custom-tag-checker",
    "AwsAccountId": "111111111111",
    "Types": ["Software and Configuration Checks/AWS Security Best Practices"],
    "CreatedAt": "2026-01-01T00:00:00Z",
    "UpdatedAt": "2026-01-01T00:00:00Z",
    "Severity": {"Label": "MEDIUM"},
    "Title": "Missing required tag: CostCenter",
    "Description": "EC2 instance i-0abc123 is missing the CostCenter tag.",
    "Resources": [{
      "Type": "AwsEc2Instance",
      "Id": "arn:aws:ec2:us-east-1:111111111111:instance/i-0abc123",
      "Region": "us-east-1",
      "Tags": {"Environment": "prod"}
    }]
  }]'
```

## Appendix A — Canonical tag key reference

| Tag key | Type | Required? | Common allowed values | Consumers |
|---|---|---|---|---|
| `Environment` | Required | Yes | `dev`, `staging`, `prod` | ABAC, Cost Explorer, Config scoping |
| `Owner` | Required | Yes | email / team alias | Accountability, alert routing |
| `Project` | Required | Yes | project code | Cost allocation |
| `CostCenter` | Required | Yes | `cc-NNNN` | Finance reporting |
| `Application` | Required | Yes | app name | Dependency mapping |
| `Team` | Required (ABAC) | If ABAC | team name | ABAC `aws:PrincipalTag/Team` |
| `Backup:Required` | Optional | No | `true`, `false` | Backup policy routing |
| `ComplianceTier` | Optional | No | `tier-1`, `tier-2`, `tier-3` | Audit cadence |
| `DataClassification` | Optional | No | `public`, `internal`, `confidential` | Macie, KMS routing |
| `CreatedAt` | Auto | No | ISO timestamp (auto-tagger) | Age-based cleanup |
| `CreatorARN` | Auto | No | IAM ARN (auto-tagger) | Audit trail |
| `CreatedVia` | Auto | No | `auto-tagger`, `console`, `terraform` | Provisioning source |

## Recent AWS features (2024-2026)

- **Organizations TagPolicy ABAC support (2024-2025):** Tag policies
  now integrate directly with ABAC patterns via `aws:ResourceTag`
  conditions. A tag policy that enforces `Team` on resources combined
  with an IAM policy using `aws:ResourceTag/Team` =
  `${aws:PrincipalTag/Team}` gives org-wide team-scoped access without
  per-team policies.

- **`ce update-cost-allocation-tags-status` GA (2023-2024):**
  Programmatic activation of cost allocation tags — previously
  Billing-console-only. The API enables org-wide automated activation
  via a script iterating member accounts. Legacy accounts may still
  require the console path.

- **Resource Groups Tagging API `get-resources` pagination improvements
  (2024):** Higher `--resources-per-page` limits and faster
  cross-region aggregation. Multi-region tag inventory is now practical
  for fleets of 100k+ resources.

- **Config required-tags multi-rule support (2024):** Multiple
  `required-tags` rules per account are now fully supported without
  evaluation conflicts. Previously, overlapping scopes produced
  inconsistent compliance states.

- **Security Hub custom findings for tag violations (2024-2025):**
  `batch-import-findings` now accepts custom tag-compliance findings
  with `AwsAccountId` + `Resources[].Tags`, enabling integration with
  third-party tag governance tools (not just Config-managed rules).

- **EventBridge cross-account event routing for auto-tagging (2024):**
  A single auto-tagger Lambda in the org management account can now
  receive CloudTrail events from member accounts via EventBridge
  cross-account routing. Previously required per-account Lambda
  deployment.

- **IAM session tagging for ABAC (2024):** `sts:AssumeRole` with
  `--tags` and `--transitive-tag-keys` allows ABAC across role chains.
  Session tags propagate through the AssumeRole chain, enabling
  team-scoped cross-account access without long-lived principal tags.

## Expert heuristic: tag governance blast radius

Tag governance changes are deceptively high-risk. A single misconfigured
TagPolicy attached to the org root can block ALL `CreateTags` calls
across the entire organization — including infrastructure-as-code
pipelines (Terraform, CloudFormation) that tag resources on creation.
The result is a fleet-wide provisioning outage within minutes.

**The rule (non-negotiable):**

> ALWAYS test tag policies in a sandbox OU first. Attach the policy to
> a non-production OU, verify enforcement on 3+ resource types, then
> promote to root. NEVER attach an untested TagPolicy to the org root
> on first contact.

**Why this rule exists:** the TagPolicy `enforced_for` list blocks
API calls. If the `allowed_values` are wrong (a typo, a missing valid
value), every `CreateTags` call with the "wrong" value fails. Terraform
apply fails. CloudFormation stack create fails. Auto-scaling launches
fail (if the launch template tags the instance). The blast radius is
the entire OU tree.

**Concrete scoping techniques:**

| Technique | Mechanism | Blast-radius limit |
|---|---|---|
| Sandbox OU attachment | Attach policy to `ou-sandbox` only | Zero production exposure |
| Single resource type | `enforced_for: ["ec2:instance"]` only | Limits to one service |
| `allowed_values` with wildcard | Include `*` as a temporary allowed value during rollout | Allows all values; enforcement is on key presence only |
| Config rule before TagPolicy | Deploy Config `required-tags` first (detect only) | Detect + report without blocking API calls |
| Dry-run via CloudTrail replay | Replay recent CloudTrail `CreateTags` events against the policy offline | Identifies what would have been blocked |

**Pre-production validation protocol (3-phase rollout):**

1. **Phase 1 — DETECT (Config only):** Deploy Config `required-tags`
   rules. Monitor NON_COMPLIANT counts for 1 week. Identify resources
   that would be affected. Do NOT deploy the TagPolicy yet.
2. **Phase 2 — ENFORCE (sandbox OU):** Attach the TagPolicy to a
   sandbox OU. Create test resources with compliant and non-compliant
   tags. Verify the API blocks the non-compliant call. Fix any
   false-positive blocks.
3. **Phase 3 — ENFORCE (root):** Promote the TagPolicy to the org
   root. Monitor CloudTrail for `TagPolicyViolationException` spikes.
   Have a rollback plan (`detach-policy`) ready.

**Cost allocation tag activation blast radius:** activating a tag key
in Billing does NOT affect resource operations — it only controls
whether the tag appears as a dimension in Cost Explorer / CUR. The
risk is reporting-only (a misnamed tag key produces a useless
dimension). Always verify tag key spelling against the actual resource
tags (`resourcegroupstaggingapi get-tag-keys`) before activating.

**ABAC blast radius:** an ABAC policy that uses `aws:PrincipalTag/Team`
on an untagged role produces an immediate access outage for every
session of that role. Always verify principal tags before deploying
the policy. Deploy in `Audit` mode first (use `aws:PrincipalTag/Team`
in a `Deny` with `StringNotEquals` to LOG violations via CloudTrail
before enforcing).

**Surface in the output:** for any recommended tag governance change,
include `BLAST_RADIUS: <scope>` (e.g., `org-root`,
`sandbox-ou-scoped`, `single-account`) and `VALIDATION_PHASE:
<detect | sandbox-enforce | root-enforce>`. If `VALIDATION_PHASE` is
not `root-enforce`, do NOT mark the recommendation as production-ready.
