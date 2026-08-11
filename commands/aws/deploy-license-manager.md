---
description: Provision an AWS License Manager license configuration with production-grade defaults (vCPU/Instance/Core counting, vendor-specific rules for Oracle/SQL Server, cross-account sharing via Organizations, SSM discovery, violation alerting, self-service grants). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create license configuration"
  - "deploy license manager"
  - "license manager configuration"
  - "track oracle licenses"
  - "track sql server licenses"
  - "license manager vcpu counting"
  - "license manager cross account"
  - "license manager organizations"
  - "license violation alerting"
  - "license manager grants"
  - "ssm license discovery"
  - "license configuration"
  - "license manager"
routes_to: license-manager-deployer
---

# /aws:deploy-license-manager

Activate the `license-manager-deployer` skill and provision an AWS
License Manager license configuration with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. License configuration model (name, counting type, count, rules)
2. License type selection (vCPU, Instance, Core)
3. License rules (Oracle Tenancy/HonorVcpuOptimization, SQL Server coreFactor)
4. Resource associations (EC2 launch template, SSM managed instances, AMI)
5. Cross-account sharing via Organizations (all-features, trusted service, delegated admin)
6. Automated discovery via Systems Manager (inventory for on-premises)
7. License violations detection and alerting (EventBridge + SNS)
8. Self-service portal grants (delegated license consumption)
9. Oracle license tracking specifics (vCPU, tenancy rules)
10. SQL Server licensing specifics (core factor, core counting)
11. Recent features (Identity Center, enhanced violation reporting, CloudWatch metrics)

## When to use

- You need to create a License Manager license configuration.
- You are tracking Oracle Database licenses (vCPU counting).
- You are tracking SQL Server licenses (core counting).
- You need cross-account license sharing via Organizations.
- You need SSM-based discovery of on-premises licensed resources.
- You need license violation detection and alerting.
- You need self-service license grants for teams.

## When NOT to use

- **AWS Marketplace subscription purchase** — use Marketplace skills.
- **IAM policy management** — use IAM skills.
- **AWS Cost Explorer analysis** — use Cost Explorer skills.
- **Auditing existing license configurations** — use License Manager audit skills.

## How to invoke

### Slash command

```
/aws:deploy-license-manager
```

Then provide: license name, counting type (vCPU/Instance/Core), license
count, license rules (vendor-specific if Oracle/SQL Server),
enforcement (hard/soft limit), resource association target, cross-
account sharing target (if needed), SSM discovery (if on-prem),
violation alerting (SNS topic), grant details (if needed), tags.

### Natural language

Any of these routes to the same skill:

- "create a license configuration for Oracle Database"
- "track SQL Server licenses with core counting"
- "share my license configuration across the Organization"
- "set up license violation alerting via SNS"
- "create a grant for my dev team to consume licenses"

### CLI routing

```bash
node cli/bin/cli.js route "create a license manager configuration"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create License
Manager configurations. The output checklist feeds into verification
pipelines and downstream audit skills.

## Example

```
You: /aws:deploy-license-manager

     Create a License Manager config for Oracle DB with 200 vCPU
     entitlement, shared tenancy, honor vCPU optimization, hard
     limit. Associate with launch template lt-aaa111222333.
     Share across Org OU ou-app-abcdef. Delegated admin
     999999999999. Alert via SNS license-alerts.

Skill:
  LICENSE_MANAGER: oracle-db-vcpu-tracking
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Counting type: vCPU
    [✓] License count: 200 (vCPUs)
    [✓] License rules: Tenancy=Shared,HonorVcpuOptimization=true
    [✓] Enforcement: Hard limit (enforce=true)
    [✓] Resource association: EC2 (launch template lt-aaa111222333)
    [✓] Cross-account sharing: Enabled (Organizations, OU ou-app-abcdef)
    [✓] Violation alerting: EventBridge + SNS license-alerts
  VERIFICATION_COMMANDS:
    aws license-manager get-license-configuration --license-configuration-arn <arn> --region us-east-1
```

## References

- Skill definition: `skills/license-manager-deployer/SKILL.md`
- License rules and counting guide: `skills/license-manager-deployer/references/license-rules-and-counting.md`
- Cross-account and discovery guide: `skills/license-manager-deployer/references/cross-account-and-discovery.md`
- Eval suite: `skills/license-manager-deployer/evals/evals.json`
