# Baseline (no-skill) — basic-component-deploy

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the lifecycle hooks
> requirement (install/startup/shutdown must all be defined), the
> thing group targeting recommendation (not individual devices),
> the configuration merge deep-merge semantics, the token exchange
> role s3:GetObject requirement, and the READY_TO_DEPLOY checklist
> format. Generated for with-skill-vs-baseline comparison.

---

Create the component:

```bash
aws greengrassv2 create-component-version \
  --inline-recipe fileb://recipe.yaml
```

Then deploy it:

```bash
aws greengrassv2 create-deployment \
  --target-arn "arn:aws:iot:us-east-1:123456789012:thing/MyFactoryGateway" \
  --components '{"com.example.TemperatureSensor": {"componentVersion": "1.0.0"}}'
```

Upload the artifact and you should be good.
