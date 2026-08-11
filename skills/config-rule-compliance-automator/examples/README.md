# End-to-end usage scenario: config-rule-compliance-automator

A walkthrough showing the skill designing a CIS compliance baseline
deployment: an AUTOMATION_DEPLOYED managed-rule S3 encryption pipeline
via StackSets, and a REVIEW_REQUIRED multi-account setup where the
Config Aggregator is missing.

## Input (user prompt)

> Design Config compliance automation for our AWS organization. We need
> CIS 2.1 S3 encryption with automatic remediation deployed via
> StackSets, and we want to understand our current multi-account
> compliance posture.

```
Design reference: prod-compliance-baseline
Organization management account: 111111111111
Target OU: ou-xxxx-security
Regions: us-east-1, us-west-2, eu-west-1, ap-southeast-2

Baseline 1: CIS 2.1 S3 Encryption
  Rule: s3-bucket-server-side-encryption-enabled (AWS-managed)
  Remediation: AWS-EnableS3BucketEncryption (automatic, reversible)
  Deployment: StackSet with auto-deployment

Baseline 2: Current multi-account posture audit
  Existing rules: root-account-mfa-enabled, cloudtrail-enabled
  Config Aggregator: NOT CONFIGURED
  StackSet auto-deployment: DISABLED
  Regions covered: us-east-1 only
```

## Skill output

```text
COMPLIANCE: prod-compliance-baseline
FRAMEWORK: CIS AWS Foundations Benchmark (2.1)
RULES:
  - Managed: s3-bucket-server-side-encryption-enabled, s3-bucket-versioning-enabled
  - Custom: none required (managed rules cover CIS 2.1)
  - Custom Policy (Guard): none
REMEDIATION:
  - Automatic: s3-bucket-server-side-encryption-enabled → AWS-EnableS3BucketEncryption
  - Automatic: s3-bucket-versioning-enabled → AWS-EnableS3BucketVersioning
AGGREGATOR:
  - Status: configured (org-wide)
  - Scope: all member accounts, all active regions
FRAMEWORK_DEPLOYMENT:
  - Method: StackSet (cis-compliance-baseline)
  - Auto-deployment: enabled
  - Regions: us-east-1, us-west-2, eu-west-1, ap-southeast-2
VERDICT: AUTOMATION_DEPLOYED
GAP: None
TEMPLATE:
  aws cloudformation create-stack-set --stack-set-name cis-compliance-baseline --template-body file://cis-conformance-pack.yaml --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM --permission-model SERVICE_MANAGED --auto-deployment Enabled=true,RetainStacksOnAccountRemoval=false
  aws cloudformation create-stack-instances --stack-set-name cis-compliance-baseline --deployment-targets OrganizationalUnitIds=["ou-xxxx-security"] --regions us-east-1,us-west-2,eu-west-1,ap-southeast-2

COMPLIANCE: prod-compliance-baseline
FRAMEWORK: CIS AWS Foundations Benchmark (audit)
RULES:
  - Managed: root-account-mfa-enabled, cloudtrail-enabled
  - Custom: none deployed
  - Custom Policy (Guard): none
REMEDIATION:
  - Automatic: none
  - Manual: none
AGGREGATOR:
  - Status: NOT CONFIGURED
  - Scope: N/A
FRAMEWORK_DEPLOYMENT:
  - Method: individual put-config-rule (per-account, per-region)
  - Auto-deployment: disabled
  - Regions: us-east-1 only
VERDICT: REVIEW_REQUIRED
GAP: (1) Config Aggregator not configured — deploy org aggregator for cross-account visibility. (2) Auto-deployment disabled on StackSet — new accounts won't receive rules. (3) Multi-region coverage missing — rules in us-east-1 only. Steps: deploy aggregator (Step 7), enable auto-deployment, add regions to StackSet instances.
```

**Account-level aggregate verdict: AUTOMATION_DEPLOYED for S3 encryption
baseline + REVIEW_REQUIRED for multi-account posture.** Deploy the S3
encryption StackSet immediately; remediate the aggregator and
multi-region gaps before claiming full compliance coverage.

## What the skill caught that a generic assistant misses

1. **The region-scoping gap.** A generic assistant deploys the rule to
   `us-east-1` and assumes global coverage. The skill deploys via
   StackSets to all active regions — Config rules are region-specific.

2. **The CAPABILITY_IAM requirement.** A generic assistant omits
   `--capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM` on the StackSet.
   The skill always includes it — without it, role creation silently
   fails.

3. **The auto-deployment gap.** A generic assistant creates the StackSet
   without auto-deployment. The skill always enables it — new accounts
   added to the OU automatically receive the conformance pack.

4. **The aggregator visibility distinction.** A generic assistant
   assumes the aggregator can remediate. The skill flags that the
   aggregator provides VISIBILITY only — remediation must be deployed
   per account via StackSets.

5. **The managed-vs-custom rule selection.** A generic assistant might
   build a custom Lambda rule for S3 encryption. The skill selects the
   managed rule — no Lambda cost, AWS-maintained, no runtime overhead.

## Slash-command invocation

```
/aws:automate-config-rule-compliance
```

Or via the orchestrator:

```
/aws:pipeline
You: "design CIS compliance automation for S3 encryption"
```

## CLI routing

```bash
node cli/bin/cli.js route "automate Config compliance"
# [Phase: Automate | Skills routed: config-rule-compliance-automator]
```

## Live-account invocation (requires AWS CLI)

```bash
# Check Config recorder status
aws configservice describe-configuration-recorders --region us-east-1

# List existing Config rules
aws configservice describe-config-rules --region us-east-1

# Check existing conformance packs
aws configservice describe-conformance-packs --region us-east-1

# Check Config Aggregator
aws configservice describe-configuration-aggregators --region us-east-1

# Check StackSets
aws cloudformation list-stack-sets --region us-east-1

# Check Organizations integration
aws organizations describe-organization --query 'Organization.Id' --output text
```

Then paste the output into the skill for compliance baseline design.
