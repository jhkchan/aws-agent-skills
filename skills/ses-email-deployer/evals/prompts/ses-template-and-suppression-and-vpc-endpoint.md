# Eval prompt: ses-template-and-suppression-and-vpc-endpoint

Create an email template with Handlebars variables, configure
account-level suppression on BOUNCE + COMPLAINT, and wire an SES
VPC endpoint. Walk the pre-flight checks and emit the standard
VERDICT block.

## Scenario

An operator in `us-east-1` wants to create an email template,
configure the suppression list, and create a VPC endpoint for
private SES API access.

## Known facts

- **Domain identity:** `example.com` (verified).
- **Configuration set:** `transactional-cs` (exists).
- **Template name:** `OrderConfirmation`.
- **Template variables:** `{{orderNumber}}`, `{{total}}`,
  `{{#each items}}{{this.name}} x{{this.qty}}{{/each}}`.
- **Template parts:** HTML + text fallback.
- **Suppression:** account-level, suppress on `BOUNCE` and
  `COMPLAINT`.
- **VPC:** `vpc-abcdef1234`, subnets `subnet-aaa`, `subnet-bbb`,
  security group `sg-mail-sender`.
- **VPC endpoint type:** Interface, private DNS enabled.

## Symptom

The operator needs the `create-email-template`,
`put-suppression-attributes`, and `create-vpc-endpoint` CLI
sequence, plus verification.
