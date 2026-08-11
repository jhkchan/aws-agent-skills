# End-to-end usage scenario: cloudwatch-cross-account-observability-deployer

A walkthrough showing the skill provisioning CloudWatch
cross-account observability with two source accounts, then
extending to an org-wide fleet with Managed Grafana and AMP
cross-account wiring. This exercises Step 1 (sink creation),
Step 2 (sink policy), Step 3 (source IAM role), Step 4 (link
creation), Step 6 (Managed Grafana), and Step 7 (AMP workspace).

## Input (user prompt)

> Set up CloudWatch cross-account observability in us-east-1.
> Monitoring account 111122223333 hosts the sink. Source accounts
> 444455556666 (checkout) and 777788889999 (payments) share
> CloudWatch metrics (AWS/EC2, AWS/ECS, AWS/Lambda,
> AWS/ApplicationSignals), log groups (/aws/ecs/prod-app,
> /aws/lambda/payments-api), X-Ray traces (checkout, payments),
> and Application Signals service data. Wire Managed Grafana
> workspace g-abcdef1234 and AMP workspace prod-prometheus in
> source 444455556666 for cross-account queries.

## Skill output

```text
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
  [OPTIONAL] AWS Organizations managed link — org-wide sink policy for fleet scale-out
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

## What the skill caught that a generic assistant misses

1. **Link is created in the source account, not monitoring.** A
   generic assistant runs `oam create-link` from the monitoring
   account and gets `InvalidParameterException`. The skill
   identifies the source account as the link creator.
2. **Sink policy gates the attachment.** A generic assistant
   omits the sink policy step. The skill enumerates each source
   account principal in the policy with the
   `ForAllValues:StringEquals oam:ResourceTypes` condition.
3. **Filter syntax is case-sensitive.** A generic assistant uses
   `aws/ecs` (lowercase). The skill enforces `AWS/ECS` (canonical
   form) — the lowercase variant matches nothing.
4. **Application Signals is a two-step enable.** A generic
   assistant assumes OAM enables Application Signals. The skill
   verifies `list-services` returns the workload in each source
   before claiming correlation.
5. **AMP bypasses OAM.** A generic assistant tries to attach the
   AMP workspace as an OAM resource type. The skill uses the AMP
   workspace role trust policy instead.
6. **Managed Grafana queries via monitoring role.** A generic
   assistant configures per-source-account data sources in
   Grafana. The skill configures ONE data source per Region
   pointing at the monitoring account role.
7. **Org-wide scaling.** A generic assistant enumerates accounts
   manually. The skill uses `aws:PrincipalOrgID` and StackSets
   for fleets.

## Slash-command invocation

```
/aws:deploy-cloudwatch-cross-account-observability
```

Or via the orchestrator:

```
/aws:pipeline
You: "set up cloudwatch cross-account observability with two source accounts"
```

The orchestrator emits `[Phase: Deploy | Skills routed:
cloudwatch-cross-account-observability-deployer]` and hands off
to this skill for the VERDICT.

## Related scenarios

The same skill handles:

- **Single monitoring account + N source accounts** — sink,
  policy, link per source.
- **Org-wide fleet via StackSets** — `aws:PrincipalOrgID` +
  `SERVICE_MANAGED` permission model.
- **Cross-account Application Signals** — link + Application
  Signals enabled per source workload.
- **Managed Grafana unified dashboards** — one CloudWatch data
  source per Region pointing at the monitoring account role.
- **AMP cross-account query** — workspace role trust policy,
  Grafana Prometheus data source.
- **Cross-Region observability** — per-Region sinks, per-Region
  Grafana data sources.
- **Decommissioning a source account** — delete the link first,
  then remove from sink policy.
