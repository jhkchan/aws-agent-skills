# Baseline (no-skill) — unregistered-ou-prerequisite

> This is the response a model produces **without** the skill
> definition. It provisions the account into the unregistered OU without
> flagging that the OU is not registered with Control Tower, resulting
> in an account with no Guardrails, no baseline, and no SSO. Does not
> emit a PREREQUISITES_MISSING verdict. Generated for
> with-skill-vs-baseline comparison.

---

Provision the account:

```bash
aws servicecatalog provision-product \
  --product-id prod-xxx \
  --provisioning-artifact-id pa-xxx \
  --provisioned-product-name legacy-app \
  --provisioning-parameters \
    Key=AccountEmail,Value=aws+legacy-app@company.com \
    Key=AccountName,Value=legacy-app \
    Key=ManagedOrganizationalUnit,Value=LegacyApps
```

The account will be created in the OU.
