# Baseline (no-skill) — network-connectivity-disruption

> This is the response a model produces **without** the skill
> definition. It suggests the network disruption action but misses
> that aws:network:disrupt-connectivity requires the FIS network
> agent IAM pass-role and additional ec2:CreateNetworkInterface
> permissions beyond standard EC2. Does not cite the stop condition
> safety net or emit the READY_TO_DEPLOY checklist. Generated for
> with-skill-vs-baseline comparison.

---

You can disrupt network between AZs like this:

```bash
aws fis create-experiment-template \
  --description "Network disruption" \
  --role-arn arn:aws:iam::123456789012:role/FISExperimentRole \
  --actions file://actions.json
```

Just include the aws:network:disrupt-connectivity action.
