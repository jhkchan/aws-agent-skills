# End-to-End Example: License Manager Deployment

A walkthrough showing how to use the `license-manager-deployer` skill
from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning an Oracle Database license configuration with
vCPU-based counting, cross-Organization sharing, and violation
alerting. The configuration needs:

- License type: Oracle Database Standard Edition (vCPU counting)
- License count: 200 vCPUs
- License rules: Tenancy=Shared, HonorVcpuOptimization=true
- Enforcement: hard limit (blocks non-compliant launches)
- Resource association: EC2 launch template lt-aaa111222333
- Cross-account sharing: Organization OU ou-app-abcdef
- Delegated administrator: account 999999999999
- Violation alerting: SNS arn:aws:sns:us-east-1:123456789012:license-alerts

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-license-manager
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a License Manager config for Oracle DB with 200 vCPU
      entitlement, shared tenancy, honor vCPU optimization, hard
      limit. Share across the Org OU ou-app-abcdef. Delegated
      administrator 999999999999. Alert via SNS license-alerts."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a license manager configuration"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
LICENSE_MANAGER: oracle-db-vcpu-tracking (lic-aaa111222333444aaa)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] License configuration name: oracle-db-vcpu-tracking
  [✓] Counting type: vCPU
  [✓] License count: 200 (vCPUs)
  [✓] License rules: Tenancy=Shared,HonorVcpuOptimization=true
  [✓] Enforcement: Hard limit (enforce=true)
  [✓] Resource association: EC2 (launch template lt-aaa111222333)
  [✓] Cross-account sharing: Enabled (Organizations all-features, OU ou-app-abcdef)
  [✓] Delegated administrator: 999999999999
  [✓] SSM discovery: Enabled (inventory configured for managed instances)
  [✓] Violation alerting: EventBridge rule license-manager-violations + SNS arn:aws:sns:us-east-1:123456789012:license-alerts
  [✓] Tags: Vendor=Oracle, Environment=production
VERIFICATION_COMMANDS:
  aws license-manager get-license-configuration --license-configuration-arn arn:aws:license-manager:us-east-1:123456789012:license-configuration:lic-aaa111222333444aaa --region us-east-1
  aws license-manager list-usage-records-for-license-configuration --license-configuration-arn arn:aws:license-manager:us-east-1:123456789012:license-configuration:lic-aaa111222333444aaa --region us-east-1
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the license configuration
LIC_ARN=$(aws license-manager create-license-configuration \
  --name "oracle-db-vcpu-tracking" \
  --license-counting-type vCPU \
  --license-count 200 \
  --license-rules 'Tenancy=Shared,HonorVcpuOptimization=true' \
  --license-rules-enforce \
  --region us-east-1 \
  --query 'LicenseConfigurationArn' --output text)

# Step 2: Enable License Manager in Organizations (from management account)
aws organizations enable-aws-service-access \
  --service-principal license-manager.amazonaws.com

aws organizations register-delegated-administrator \
  --account-id 999999999999 \
  --service-principal license-manager.amazonaws.com

# Step 3: Share to OU (from delegated administrator)
aws license-manager create-license-configuration-cross-account \
  --license-configuration-arn "$LIC_ARN" \
  --target-organization-structure '{"OrganizationalUnits":["ou-app-abcdef"]}' \
  --region us-east-1

# Step 4: Associate with launch template
aws ec2 create-launch-template-version \
  --launch-template-name oracle-workload \
  --launch-template-data '{
    "LicenseSpecifications":[{"LicenseConfigurationArn":"'"$LIC_ARN"'"}]
  }' \
  --region us-east-1

# Step 5: Configure violation alerting (EventBridge + SNS)
aws events put-rule \
  --name license-manager-violations \
  --event-pattern '{
    "source":["aws.license-manager"],
    "detail-type":["License Manager License Configuration Violation"]
  }' \
  --region us-east-1

aws events put-targets \
  --rule license-manager-violations \
  --targets '{"Id":"1","Arn":"arn:aws:sns:us-east-1:123456789012:license-alerts"}' \
  --region us-east-1
```

---

## Step 4 — Post-deployment verification

```bash
# Verify the license configuration
aws license-manager get-license-configuration \
  --license-configuration-arn "$LIC_ARN" \
  --region us-east-1

# Check consumption
aws license-manager list-usage-records-for-license-configuration \
  --license-configuration-arn "$LIC_ARN" \
  --region us-east-1

# Verify EventBridge rule
aws events describe-rule \
  --name license-manager-violations \
  --region us-east-1

# Verify delegated administrator
aws organizations list-delegated-administrators \
  --service-principal license-manager.amazonaws.com
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| License rules | Not configured | Tenancy=Shared, HonorVcpuOptimization=true | Oracle requires vendor-specific rules; without them no Oracle conditions are enforced |
| Counting type | Defaults to vCPU | Explicitly matched to vendor | SQL Server needs Core counting, not vCPU |
| Cross-account | Attempts share without Org enablement | Organizations all-features + trusted service + delegated admin | Org prerequisites are mandatory for cross-account sharing |
| SSM discovery | Not configured | SSM inventory with Aws:SoftwareInventory plugin | On-prem resources invisible to License Manager without SSM inventory |
| Violation alerting | Not configured | EventBridge rule + SNS target | Hard-limit violations emit events but no one is notified without EventBridge |
| Enforcement | Defaults to soft (alert only) | Hard limit for compliance-critical licenses | Soft limit does NOT block non-compliant launches |

---

## Related artifacts

- **Skill definition:** `skills/license-manager-deployer/SKILL.md`
- **License rules and counting guide:** `skills/license-manager-deployer/references/license-rules-and-counting.md`
- **Cross-account and discovery guide:** `skills/license-manager-deployer/references/cross-account-and-discovery.md`
- **Slash command:** `commands/aws/deploy-license-manager.md`
- **Eval suite:** `skills/license-manager-deployer/evals/evals.json`
- **Legacy test cases:** `skills/license-manager-deployer/eval/test-cases.yaml`
