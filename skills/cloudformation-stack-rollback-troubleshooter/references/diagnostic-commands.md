# Diagnostic Commands (load on demand) — CloudFormation Stack Rollback Troubleshooter

Pre-flight and per-step probe commands moved verbatim from SKILL.md. Loaded on demand.

---

## Pre-flight — stack state and gather-info gate (moved from SKILL.md)

```bash
# 1. Stack status and parameters
aws cloudformation describe-stacks \
  --stack-name <name-or-arn> --output json

# 2. Stack events (the specific resource that failed to roll back)
aws cloudformation describe-stack-events \
  --stack-name <name-or-arn> --output json | \
  jq '.StackEvents[] | select(.ResourceStatus | test("FAILED|ROLLBACK"))'

# 3. Stack policy (Deny rules that block rollback)
aws cloudformation get-stack-policy \
  --stack-name <name-or-arn> --output json

# 4. Drift detection (resources that drifted from template)
aws cloudformation describe-stack-resource-drifts \
  --stack-name <name-or-arn> --output json | \
  jq '.StackResourceDrifts[] | select(.StackResourceDriftStatus != "IN_SYNC")'

# 5. Template summary (resources with Replacement: True)
aws cloudformation get-template-summary \
  --stack-name <name-or-arn> --output json
```
## Step 3 — CUSTOM_RESOURCE_TIMEOUT probes (moved from SKILL.md)

```bash
# Identify the provider Lambda (ServiceToken)
aws cloudformation describe-stack-resource \
  --stack-name <name> --logical-resource-id <custom-resource-id> \
  --output json | jq '.StackResourceDetail'

# Check the Lambda's logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/<provider-lambda> \
  --start-time $(date -d '-2 hours' +%s)000 \
  --filter-pattern '"Task timed out" OR "ERROR" OR "cfnresponse"' \
  --output json
```
## Step 5 — IAM_REPLACEMENT probes (moved from SKILL.md)

```bash
# Check if old IAM resource is still in use
aws iam list-attached-role-policies --role-name <old-role> --output json
aws iam list-instance-profiles-for-role --role-name <old-role> --output json

# Check for Replacement: True on IAM types
aws cloudformation get-template-summary \
  --stack-name <name> --output json | \
  jq '.ResourceTypes[] | select(.ResourceType | test("IAM"))'
```
## Step 7 — STACK_POLICY_BLOCKING temporary Allow-policy swap (moved from SKILL.md)

```bash
aws cloudformation set-stack-policy --stack-name <name> \
  --stack-policy-body file://temp-allow-all.json --profile <p>
aws cloudformation continue-update-rollback --stack-name <name> --profile <p>
# After rollback: restore original policy
aws cloudformation set-stack-policy --stack-name <name> \
  --stack-policy-body file://original-policy.json --profile <p>
```
