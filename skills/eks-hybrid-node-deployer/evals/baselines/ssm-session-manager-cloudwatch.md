# Baseline (no-skill) — ssm-session-manager-cloudwatch

> This is the response a model produces **without** the skill
> definition. It suggests SSH access instead of SSM Session Manager
> (wrong — SSM is recommended for audited keyless access), assumes
> CloudWatch metrics are automatic (wrong — the agent must be manually
> installed on hybrid nodes), and does not emit the READY_TO_DEPLOY
> checklist format. Generated for with-skill-vs-baseline comparison.

---

Set up SSH access to the nodes via a bastion host. CloudWatch should
pick up metrics automatically since the nodes are registered with EKS.
