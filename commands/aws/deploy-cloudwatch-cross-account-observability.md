---
description: Provision CloudWatch cross-account observability via Observability Access Manager (OAM) — creates the monitoring account sink, attaches source accounts via OAM links, configures sharing (metrics, logs, traces, Application Signals), wires Managed Grafana and AMP cross-account data sources, and emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "cloudwatch cross-account"
  - "observability access manager"
  - "oam sink"
  - "oam link"
  - "cross-account observability"
  - "monitoring account observability"
  - "source account observability"
  - "cross-account metrics"
  - "cross-account logs"
  - "cross-account traces"
  - "cross-account application signals"
  - "managed grafana cross-account"
  - "amp cross-account"
  - "oam create-sink"
  - "oam create-link"
  - "oam put-sink-policy"
  - "cloudwatch multi-account"
  - "cross-account service map"
  - "oam attach link"
routes_to: cloudwatch-cross-account-observability-deployer
---

# /aws:deploy-cloudwatch-cross-account-observability

Activate the `cloudwatch-cross-account-observability-deployer`
skill and provision CloudWatch cross-account observability with
production-grade configuration.

## What it does

The skill walks a 10-step provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Create the OAM sink in the monitoring account
2. Authorize source accounts via the sink policy
3. Create the source account IAM role (oam:CreateLink on sink ARN)
4. Create the OAM link from the source account (sharing scopes)
5. Verify the link is attached to the sink
6. Wire Managed Grafana to query via the sink role
7. Attach AMP workspace for cross-account Prometheus queries
8. Enable cross-account Application Signals (two-step: link + per-source enable)
9. Verify cross-account data flows (metrics, logs, traces, service maps)
10. Tag, alarm, and visualize cross-account

## When to use

- You want to create an OAM sink and attach source accounts.
- You are configuring sharing scopes (metrics namespaces, log
  groups, X-Ray services, Application Signals services).
- You want to wire Amazon Managed Grafana to query cross-account
  data via the OAM sink.
- You want to attach an AMP workspace for cross-account
  Prometheus queries.
- You want cross-account Application Signals service maps.
- You want to deploy org-wide via CloudFormation StackSets.
- You want to check for enablement blockers (sink policy missing
  source principal, source IAM lacks oam:CreateLink, Application
  Signals not enabled in source).

## How to invoke

### Slash command

```
/aws:deploy-cloudwatch-cross-account-observability
```

Then provide: monitoring account ID, source account IDs, sink
Region, sharing scopes (metrics namespaces, log group patterns,
X-Ray services, Application Signals services), Managed Grafana
workspace ID (optional), AMP workspace ID (optional), and
Application Signals enablement status per source.

### Natural language

Any of these routes to the same skill:

- "set up cloudwatch cross-account observability"
- "create an oam sink in the monitoring account"
- "attach source accounts to the oam sink"
- "wire managed grafana for cross-account queries"
- "enable cross-account application signals"
- "deploy oam links via stacksets"

### CLI routing

```bash
node cli/bin/cli.js route "deploy cloudwatch cross-account observability"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps
pipeline. The output checklist feeds into verification pipelines
and downstream auditor skills (e.g., a cloudwatch-alarm auditor
for cross-account error spikes, and the
`cloudwatch-application-signals-deployer` skill which completes
the per-source Application Signals enablement).

## Example

```
You: /aws:deploy-cloudwatch-cross-account-observability

     Set up CloudWatch cross-account observability in
     us-east-1. Monitoring account 111122223333 hosts the
     sink. Source accounts 444455556666 (checkout) and
     777788889999 (payments) share CloudWatch metrics
     (AWS/EC2, AWS/ECS, AWS/Lambda, AWS/ApplicationSignals),
     log groups (/aws/ecs/prod-app, /aws/lambda/payments-api),
     X-Ray traces (checkout, payments), and Application Signals.
     Wire Managed Grafana workspace g-abcdef1234 and AMP
     workspace prod-prometheus in source 444455556666.

Skill:
  MONITORING_ACCOUNT: 111122223333
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓]      Monitoring account sink — arn:aws:oam:us-east-1:111122223333:sink/ProdObservabilitySink
    [✓]      Sink policy — allows source accounts 444455556666, 777788889999 to attach
    [✓]      Source link (444455556666) — link/prod-app-link attached to sink
    [✓]      Source link (777788889999) — link/payments-app-link attached to sink
    [✓]      Sharing — MetricConfiguration: AWS/EC2, AWS/ECS, AWS/Lambda, AWS/ApplicationSignals
    [✓]      Sharing — LogGroupConfiguration: /aws/ecs/prod-app, /aws/lambda/payments-api
    [✓]      Sharing — TraceConfiguration: X-Ray services checkout, payments
    [✓]      Sharing — ApplicationSignals services checkout, payments
    [✓]      IAM — source accounts hold oam:CreateLink on sink ARN
    [✓]      Managed Grafana — workspace g-abcdef1234 with CloudWatch data source via GrafanaCrossAccountReadRole
    [✓]      AMP workspace — prod-prometheus attached as cross-account data source via AMPQueryRole
    [✓]      Cross-account Application Signals — service map aggregates across both source accounts
  VERIFICATION_COMMANDS:
    aws oam list-sinks --region us-east-1
    aws oam get-sink --identifier arn:aws:oam:us-east-1:111122223333:sink/ProdObservabilitySink
    aws oam list-attached-links --sink-identifier arn:aws:oam:us-east-1:111122223333:sink/ProdObservabilitySink
    aws oam list-links --region us-east-1
    aws cloudwatch list-metrics --namespace AWS/ApplicationSignals --region us-east-1
    aws logs describe-log-groups --log-group-name-prefix /aws/ecs --region us-east-1
    aws grafana list-workspaces --region us-east-1
    aws amp list-workspaces --region us-east-1
```

## References

- Skill definition: `skills/cloudwatch-cross-account-observability-deployer/SKILL.md`
- Deployment CLI commands: `skills/cloudwatch-cross-account-observability-deployer/references/deployment-cli-commands.md`
- Sharing scopes and IAM guide: `skills/cloudwatch-cross-account-observability-deployer/references/sharing-scopes-and-iam-guide.md`
- Eval suite: `skills/cloudwatch-cross-account-observability-deployer/evals/evals.json`
