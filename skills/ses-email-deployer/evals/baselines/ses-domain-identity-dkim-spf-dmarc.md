# Baseline (no-skill) response: ses-domain-identity-dkim-spf-dmarc

This file captures what a generic assistant produces WITHOUT the
ses-email-deployer skill loaded.

---

To set up SES for your domain, first verify it:

```
aws sesv2 create-email-identity --email-identity example.com
```

Then add the DKIM records to your DNS. You'll also want to set up
SPF and DMARC records. DMARC helps with deliverability. Use
p=reject for the strongest protection.

After the records are in place, SES will verify the domain and
you can start sending email.
