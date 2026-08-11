# Baseline (no-skill) — ecs-java-service-ready

> This is the response a model produces **without** the skill definition.
> It produces a generic "enable Application Signals" snippet but misses
> the structured READY_TO_DEPLOY checklist, the explicit verification
> of the CloudWatchApplicationSignalsReportServiceAccess IAM policy,
> the AWS_SERVICE_NAME / AWS_APPLICATION_ENVIRONMENT env var pair,
> and the burn-rate alarm thresholds.

---

To enable Application Signals, you can use the console or run the CLI:

```bash
aws application-signals list-services --region us-east-1
```

For your ECS Java service, install the ADOT Java agent via the
JAVA_TOOL_OPTIONS env var and add the OTel collector sidecar.
Attach the AWSXrayWriteOnlyAccess policy to your task role.

You can then create an SLO for availability via CloudFormation
with the AWS::ApplicationSignals::ServiceLevelObjective resource.

Set up a CloudWatch alarm on the SLO burn rate.
