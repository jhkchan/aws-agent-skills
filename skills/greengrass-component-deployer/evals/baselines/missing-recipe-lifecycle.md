# Baseline (no-skill) — missing-recipe-lifecycle

> This is the response a model produces **without** the skill
> definition. It proceeds to create and deploy the component without
> flagging that the recipe is missing lifecycle hooks (install,
> startup, shutdown). Without lifecycle hooks the component is a
> no-op — it installs but does nothing. Generated for with-skill-vs-
> baseline comparison.

---

Create the component:

```bash
aws greengrassv2 create-component-version \
  --inline-recipe fileb://recipe.yaml
```

Deploy:

```bash
aws greengrassv2 create-deployment \
  --target-arn "arn:aws:iot:us-east-1:123456789012:thinggroup/TestDevices" \
  --components '{"com.example.BrokenComponent": {"componentVersion": "1.0.0"}}'
```

The component should deploy fine.
