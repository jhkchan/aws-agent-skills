# Baseline (no-skill) — standard-edition-vpc-prerequisite-fail

> This is the response a model produces **without** the skill
> definition. It attempts the VPC connection without flagging the
> Standard edition prerequisite failure (VPC connections require
> Enterprise), missing the edition check entirely. Generated for
> with-skill-vs-baseline comparison.

---

To connect QuickSight to a private MySQL instance:

1. Add MySQL as a data source.
2. Set up a VPC connection with your subnets.
3. Create your dashboard.

```bash
aws quicksight create-vpc-connection --name "vpc-conn"
aws quicksight create-data-source --type MYSQL
```
