---
description: Deploy an AWS Config aggregator with production-grade configuration (organization aggregator with delegated admin, authorized accounts with per-account authorization, org-level conformance packs, organization config rules with Lambda processors, proactive rules for pre-deployment evaluation). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create config aggregator"
  - "deploy config aggregator"
  - "organization aggregator"
  - "aws config delegated administrator"
  - "authorized accounts aggregation"
  - "conformance pack organization"
  - "organization config rule"
  - "proactive config rules"
  - "config lambda processor"
  - "cross-region config visibility"
  - "config multi-account compliance"
  - "config aggregator vs recorder"
  - "aws config multi-account"
routes_to: config-aggregator-deployer
---

# /aws:deploy-config-aggregator

Activate the `config-aggregator-deployer` skill and deploy an AWS Config
aggregator with production-grade configuration.

## What it does

The skill walks a 9-step deployment procedure and emits a
READY_TO_DEPLOY checklist:

1. Aggregation type selection (Organization vs Authorized accounts)
2. Delegated administrator setup (organization only)
3. Create the aggregator (organization or authorized-account)
4. Authorize source accounts (authorized-account only)
5. Verify recorders in source accounts
6. Conformance packs at organization level
7. Organization config rules with Lambda processor
8. Proactive rules (pre-deployment evaluation)
9. Verification and post-deployment checks

## When to use

- You need to create a new Config aggregator (organization or authorized).
- You want to enable Config across an AWS Organization via delegated admin.
- You need to deploy conformance packs at the organization level.
- You want to set up organization config rules with custom Lambda logic.
- You want to enable proactive compliance checks (shift-left).
- You want to check for deployment blockers (missing delegated admin,
  recorders not running, missing delivery channels).

## How to invoke

### Slash command

```
/aws:deploy-config-aggregator
```

Then provide: aggregator name, aggregation type (organization or
authorized accounts), organization ID or account list, source regions,
conformance packs, config rules, and any optional features (Lambda
processors, proactive rules).

### Natural language

Any of these routes to the same skill:

- "create a Config aggregator"
- "deploy an organization aggregator for Config"
- "set up Config delegated administrator"
- "deploy conformance packs org-wide"
- "enable proactive config rules"
- "configure Config multi-account compliance"

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The output checklist feeds into verification pipelines and audit skills
(config-rule-deployer for individual account Config rules).

## Example

```
You: /aws:deploy-config-aggregator

     Deploy a Config aggregator in us-east-1. Organization aggregator.
     Org ID o-abc123def. Delegated admin 123456789012. All accounts,
     all regions. Deploy conformance pack OperationalBestPractices-for-
     Security at org level. Add a Lambda processor org config rule for
     tag policy compliance.

Skill:
  AGGREGATOR: org-compliance-aggregator
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓]      Aggregator type — OrganizationAggregationSource (OrganizationID: o-abc123def)
    [✓]      Delegated administrator — 123456789012 (Config enabled, all features)
    [✓]      Source accounts — all accounts in Organization o-abc123def (auto-discovered)
    [✓]      Source regions — all enabled regions
    [✓]      Recorder — config recorder running on delegated admin
    [✓]      Conformance packs — OperationalBestPractices-for-Security (deployed org-wide)
    [✓]      Organization config rules — tag-policy-compliance (Lambda processor, ACTIVE)
    [✓]      Tags — Environment=production, Governance=compliance
    [OPTIONAL] Aggregation authorization — not needed (organization aggregator auto-authorizes)
  VERIFICATION_COMMANDS:
    aws configservice describe-configuration-aggregators --configuration-aggregator-names org-compliance-aggregator --region us-east-1
    aws configservice describe-configuration-aggregator-sources-status --configuration-aggregator-name org-compliance-aggregator --region us-east-1
    aws configservice describe-organization-conformance-packs --region us-east-1
```

## References

- Skill definition: `skills/config-aggregator-deployer/SKILL.md`
- Deployment CLI commands: `skills/config-aggregator-deployer/references/deployment-cli-commands.md`
- Conformance packs, proactive rules guide: `skills/config-aggregator-deployer/references/conformance-packs-and-proactive-rules.md`
- Eval suite: `skills/config-aggregator-deployer/evals/evals.json`
