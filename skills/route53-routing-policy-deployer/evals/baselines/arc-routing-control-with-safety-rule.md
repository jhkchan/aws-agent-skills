# Baseline (no-skill) — arc-routing-control-with-safety-rule

> This is the response a model produces **without** the skill definition.
> It creates routing controls without a safety rule — both controls can
> be flipped OFF simultaneously, taking the workload to zero with no
> DNS recourse. It also omits the readiness check, so cutover risks
> overloading the secondary. Generated for with-skill-vs-baseline
> comparison.

---

To set up ARC:

```bash
aws route53-recovery-control-config create-cluster --cluster-name api-dr-cluster
aws route53-recovery-control-config create-control-panel \
  --cluster-arn <CLUSTER_ARN> --control-panel-name api-dr-panel

aws route53-recovery-control-config create-routing-control \
  --cluster-arn <CLUSTER_ARN> --control-panel-arn <PANEL_ARN> \
  --routing-control-name us-east-1-routing

aws route53-recovery-control-config create-routing-control \
  --cluster-arn <CLUSTER_ARN> --control-panel-arn <PANEL_ARN> \
  --routing-control-name us-west-2-routing
```

Now you can flip routing controls to direct traffic between regions.
