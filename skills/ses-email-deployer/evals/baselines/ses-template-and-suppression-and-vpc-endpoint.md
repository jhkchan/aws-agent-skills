# Baseline (no-skill) response: ses-template-and-suppression-and-vpc-endpoint

This file captures what a generic assistant produces WITHOUT the
ses-email-deployer skill loaded.

---

To create a template:

```
aws sesv2 create-email-template --template-name OrderConfirmation
```

For suppression, you can manage it in the SES console. VPC
endpoints can be created via the EC2 console or CLI. Make sure
your VPC has the right settings.
