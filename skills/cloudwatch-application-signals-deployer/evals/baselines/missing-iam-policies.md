# Baseline (no-skill) — missing-iam-policies

> This is the response a model produces **without** the skill definition.
> It misses the silent-failure trap entirely — without
> CloudWatchApplicationSignalsReportServiceAccess the ADOT agent
> starts but produces zero RED metrics and no service-map nodes. The
> baseline proceeds as if deployment were healthy.

---

To enable Application Signals on orders-api:

1. Install the ADOT collector sidecar in your ECS task definition.
2. Set `JAVA_TOOL_OPTIONS=-javaagent:/opt/aws-opentelemetry-agent/aws-opentelemetry-agent.jar`.
3. Confirm X-Ray sampling is configured (you said FixedRate=0.05, that's good).
4. Create your SLO via CloudFormation.

Since your task role already has AWSXrayWriteOnlyAccess, you should
be good to go. The agent will start publishing metrics to CloudWatch
once traces flow.
