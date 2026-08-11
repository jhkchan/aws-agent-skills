# Baseline (no-skill) — terraform-account-factory-baseline

> This is the response a model produces **without** the skill
> definition. It misses the Account Factory custom baseline concept
> (StackSet applied at vending), the SCP/tag policy OU inheritance,
> the Identity Center permission set assignment requirement, the org
> trail inheritance constraint, and the READY_TO_DEPLOY checklist
> format. Generated for with-skill-vs-baseline comparison.

---

Here's some Terraform to create the account:

```hcl
resource "aws_organizations_account" "payments" {
  name  = "payments-prod-use1"
  email = "aws+payments@yourdomain.com"
}
```

Apply with `terraform apply`. The account should appear in the org.
