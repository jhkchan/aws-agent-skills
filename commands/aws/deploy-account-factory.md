---
description: Deploy AWS Control Tower Account Factory accounts with production-grade defaults (Service Catalog provisioning, OU placement, SSO permission set assignment, Guardrail inheritance, landing zone baseline StackSets, email uniqueness, alternate contacts, account customization, compliance verification, account lifecycle management). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create aws account control tower"
  - "account factory provision"
  - "vending new account"
  - "control tower account"
  - "account factory"
  - "vend aws account"
  - "sso permission set assignment"
  - "guardrail scp inheritance"
  - "control tower landing zone"
  - "terminate aws account"
  - "custom account baseline"
  - "account factory service catalog"
routes_to: account-factory-deployer
---

# /aws:deploy-account-factory

Activate the `account-factory-deployer` skill and deploy AWS Control
Tower Account Factory accounts with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Account Factory via Service Catalog (provision-product)
2. Organizational Unit placement (registered vs. unregistered)
3. SSO permission set assignment (three-way binding)
4. Guardrail inheritance (SCP, Detective, Config)
5. Landing zone baseline conformance (StackSets)
6. Email and account name uniqueness
7. Alternate contacts (Billing, Security, Operations)
8. Account customization (custom StackSets)
9. Account lifecycle (vending, updating, terminating)
10. Compliance status verification
11. Recent features (customization, group auto-assignment, LZ 3.0+)

## When to use

- You need to vend a new AWS account via Control Tower.
- You are assigning SSO permission sets to groups for an account.
- You want to verify Guardrail (SCP) inheritance.
- You need to customize an account baseline via StackSets.
- You need to set alternate contacts on an account.
- You are terminating an Account Factory account.
- You want to verify baseline StackSet deployment.
- You are moving an account between OUs and need to verify SCPs.

## When NOT to use

- **Raw Organizations account creation** — use organizations-account-
  deployer for accounts outside Control Tower.
- **Landing zone setup/upgrade** — use controltower-control-auditor
  for landing zone version management.
- **SCP authoring** — use organizations-scp-deployer to create or
  update individual SCPs.
- **Identity Center setup** — use Identity Center skills for directory
  configuration, user creation, or group management.

## How to invoke

### Slash command

```
/aws:deploy-account-factory
```

Then provide: account name, root email, target OU, SSO admin email,
permission set assignments (group + permission set), custom baseline
StackSets (if any), alternate contacts, tags.

### Natural language

Any of these routes to the same skill:

- "vending a new production account via Account Factory"
- "create a Control Tower account in the DataPlatform OU"
- "assign DataEngineerAccess to the DataPlatformTeam group"
- "verify Guardrails on my new account"
- "terminate the sandbox-dev account from Account Factory"

### CLI routing

```bash
node cli/bin/cli.js route "vending a new account via account factory"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create or manage
AWS accounts via Control Tower Account Factory. The output checklist
feeds into verification pipelines and downstream governance audit
skills.

## Example

```
You: /aws:deploy-account-factory

     Vend a new data-platform-prod account into the DataPlatform
     OU. Assign DataEngineerAccess to the DataPlatformTeam group.
     SSO instance ssoins-12345.

Skill:
  ACCOUNT_FACTORY: data-platform-prod (123456789012) in OU DataPlatform
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Account email: aws+prod-data-platform@company.com — UNIQUE
    [✓] Target OU: Custom (DataPlatform) — REGISTERED
    [✓] Guardrails (SCP): 8 preventive controls inherited
    [✓] Baseline StackSets: AWSControlTowerLogging — DEPLOYED
    [✓] Permission sets: DataEngineerAccess assigned to DataPlatformTeam
    [✓] SSO provisioning: SUCCEEDED
  VERIFICATION_COMMANDS:
    aws organizations describe-account --account-id 123456789012
    aws organizations list-policies-for-target --target-id 123456789012 --filter SERVICE_CONTROL_POLICY
```

## References

- Skill definition: `skills/account-factory-deployer/SKILL.md`
- Guardrails and baseline: `skills/account-factory-deployer/references/guardrails-and-baseline.md`
- SSO and lifecycle: `skills/account-factory-deployer/references/sso-and-lifecycle.md`
- Eval suite: `skills/account-factory-deployer/evals/evals.json`
