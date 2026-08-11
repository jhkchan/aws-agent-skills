---
description: Enable CloudWatch Application Signals on ECS / EKS / EC2 / Lambda with auto-instrumentation (Java, Python), service discovery (CloudMap, Kubernetes), SLO creation (availability, latency, custom), service map visualization, ServiceLevelObjective CloudFormation (period, target, alarm), and RED metrics extraction from X-Ray traces. Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "application signals"
  - "enable application signals"
  - "cloudwatch application signals"
  - "service map"
  - "service-level objective"
  - "slo cloudwatch"
  - "cloudwatch slo"
  - "red metrics"
  - "x-ray red metrics"
  - "auto-instrument application signals"
  - "cloudmap service discovery"
  - "eks service map"
  - "ecs application signals"
  - "ec2 application signals"
  - "lambda application signals"
  - "opentelemetry aws distro"
  - "adot java agent"
  - "adot python"
  - "application signals ecs"
  - "application signals eks"
  - "application signals ec2"
  - "application signals lambda"
  - "java application signals"
  - "python application signals"
  - "burn rate alarm"
  - "cloudwatch service level objective"
routes_to: cloudwatch-application-signals-deployer
---

# /aws:deploy-cloudwatch-application-signals

Activate the `cloudwatch-application-signals-deployer` skill and
enable CloudWatch Application Signals on a workload with
production-grade configuration.

## What it does

The skill walks a 10-step enablement procedure and emits a
READY_TO_DEPLOY checklist:

1. Opt in the account for Application Signals (Region-scoped)
2. Attach IAM policies to the workload role
3. Inject the OpenTelemetry auto-instrumentation agent (Java / Python)
4. Set service name + environment labels
5. Configure X-Ray sampling
6. Wire service discovery (CloudMap / Kubernetes)
7. Verify RED metrics (Rate, Errors, Duration) flow to CloudWatch
8. Create a ServiceLevelObjective (availability / latency / custom)
9. Configure the SLO burn-rate alarm
10. Tag, verify, and watch service map

## When to use

- You want to enable Application Signals on an ECS / EKS / EC2 / Lambda
  workload with auto-instrumentation.
- You are creating a CloudWatch ServiceLevelObjective (period, target,
  alarm) bound to a discovered service.
- You want to wire service discovery from CloudMap or Kubernetes.
- You are setting up multi-window burn-rate alarms on an SLO.
- You want to check for enablement blockers (missing IAM policies,
  X-Ray sampling disabled, unsupported runtime, SLO before service
  discovery).

## How to invoke

### Slash command

```
/aws:deploy-cloudwatch-application-signals
```

Then provide: service name, platform (ECS / EKS / EC2 / Lambda),
runtime (Java / Python / other), workload IAM role, X-Ray sampling
status, service discovery source, SLO type (availability / latency /
custom) with target and interval, and burn-rate alarm preferences.

### Natural language

Any of these routes to the same skill:

- "enable application signals on payments-api"
- "create an SLO for the auth service"
- "wire cloudmap service discovery for application signals"
- "set up burn-rate alarms on the orders-api SLO"
- "instrument a lambda function for application signals"

### CLI routing

```bash
node cli/bin/cli.js route "deploy cloudwatch application signals"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The output checklist feeds into verification pipelines and downstream
auditor skills (e.g., a CloudWatch alarm auditor for SLO coverage,
and the `cloudwatch-dashboard-deployer` skill which surfaces SLO
widgets).

## Example

```
You: /aws:deploy-cloudwatch-application-signals

     Enable CloudWatch Application Signals on the payments-api
     ECS Fargate service in us-east-1. Runtime: Java 17. Task
     role payments-api-task has both managed policies attached.
     X-Ray sampling FixedRate=0.05. ADOT sidecar pattern. Create
     a 99.9% availability SLO over 28 days rolling with burn-rate
     alarms. Account: 123456789012.

Skill:
  SERVICE: payments-api
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓]      Platform — ECS Fargate
    [✓]      Runtime — Java 17 (Corretto)
    [✓]      Auto-instrumentation — ADOT Java agent + collector sidecar
    [✓]      Application Signals role — arn:aws:iam::123456789012:role/payments-api-task
    [✓]      Service name override — AWS_SERVICE_NAME=payments-api
    [✓]      X-Ray tracing — Default sampling FixedRate=0.05
    [✓]      Service discovery — CloudMap namespace payments.local
    [✓]      RED metrics — AWS/ApplicationSignals namespace
    [✓]      SLO — 99.9% availability over 28 days rolling
    [✓]      Burn-rate alarm — fast (5m, 14.4x), medium (1h, 6x), slow (6h, 3x)
  VERIFICATION_COMMANDS:
    aws application-signals list-services --region us-east-1
    aws application-signals list-service-level-objectives --region us-east-1
    aws xray get-sampling-rules --region us-east-1
    aws iam list-attached-role-policies --role-name payments-api-task
    aws cloudwatch describe-alarms --alarm-name-prefix payments-api-slo
    aws cloudwatch list-metrics --namespace AWS/ApplicationSignals
```

## References

- Skill definition: `skills/cloudwatch-application-signals-deployer/SKILL.md`
- Deployment CLI commands: `skills/cloudwatch-application-signals-deployer/references/deployment-cli-commands.md`
- SLO and service discovery guide: `skills/cloudwatch-application-signals-deployer/references/slo-and-service-discovery-guide.md`
- Eval suite: `skills/cloudwatch-application-signals-deployer/evals/evals.json`
