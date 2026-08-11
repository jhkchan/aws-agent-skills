# Baseline (no-skill) — xray-sampling-zero

> This is the response a model produces **without** the skill definition.
> It proceeds with deployment without flagging that the X-Ray sampling
> FixedRate=0 blanks RED metrics entirely — the SLO would never fire
> and the service map would never populate.

---

To enable Application Signals on notifications-api, attach the ADOT
Java agent to your ECS task and the agent will start publishing.

```bash
aws application-signals list-services --region us-east-1
```

Since the task role has both managed policies and X-Ray is enabled,
you can create your SLO via CloudFormation. Sampling at FixedRate=0
keeps your X-Ray costs minimal.

Set up a CloudWatch alarm on the SLO burn-rate metric to page on
fast burn.
