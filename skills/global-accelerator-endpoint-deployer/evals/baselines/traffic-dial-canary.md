# Baseline (no-skill) — traffic-dial-canary

> This is the response a model produces **without** the skill
> definition. It creates the accelerator but confuses traffic dial with
> endpoint weight, does not normalize the traffic dial percentages, and
> misses the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Create the accelerator with two NLB endpoints:

```bash
aws globalaccelerator create-accelerator --name "canary-accelerator"
```

Set the weights and you should be good.
