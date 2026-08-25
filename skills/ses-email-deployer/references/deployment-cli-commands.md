# Deployment CLI commands — deep reference

This reference expands the SKILL.md deployment steps with the
full copy-pasteable CLI command sequence, Terraform equivalents,
CloudFormation snippets, and per-Region MX record endpoints. Load
when wiring SES email infrastructure end-to-end.

## Domain identity lifecycle

### Create the domain identity with DKIM

```bash
aws sesv2 create-email-identity \
  --email-identity example.com \
  --dkim-signing-attributes '{"SigningEnabled": true}' \
  --region us-east-1
```

Response returns `DkimTokens` (3 tokens) and `IdentityType:
DOMAIN`.

### Read the identity

```bash
aws sesv2 get-email-identity \
  --email-identity example.com \
  --region us-east-1

aws sesv2 list-email-identities --region us-east-1
```

`VerificationStatus` cycles: `PENDING` → `SUCCESS` (or
`FAILED`). `DkimSigningAttributes.Status` cycles the same.

### Delete the identity

```bash
aws sesv2 delete-email-identity \
  --email-identity example.com \
  --region us-east-1
```

## DNS records (Route 53)

### Capture the hosted zone ID

```bash
HOSTED_ZONE_ID=$(aws route53 list-hosted-zones \
  --query "HostedZones[?Name=='example.com.'].Id" \
  --output text | cut -d'/' -f2)
```

### Publish DKIM CNAME records

```bash
cat > /tmp/dkim-change.json <<'EOF'
{
  "Changes": [
    {"Action": "CREATE", "ResourceRecordSet": {"Name": "abc123._domainkey.example.com", "Type": "CNAME", "TTL": 1800, "ResourceRecords": [{"Value": "abc123.dkim.amazonses.com"}]}},
    {"Action": "CREATE", "ResourceRecordSet": {"Name": "def456._domainkey.example.com", "Type": "CNAME", "TTL": 1800, "ResourceRecords": [{"Value": "def456.dkim.amazonses.com"}]}},
    {"Action": "CREATE", "ResourceRecordSet": {"Name": "ghi789._domainkey.example.com", "Type": "CNAME", "TTL": 1800, "ResourceRecords": [{"Value": "ghi789.dkim.amazonses.com"}]}}
  ]
}
EOF

aws route53 change-resource-record-sets \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --change-batch file:///tmp/dkim-change.json
```

### Publish MAIL FROM MX + SPF TXT

```bash
cat > /tmp/mailfrom-change.json <<'EOF'
{
  "Changes": [
    {"Action": "CREATE", "ResourceRecordSet": {"Name": "mail.example.com", "Type": "MX", "TTL": 600, "ResourceRecords": [{"Value": "10 feedback-smtp.us-east-1.amazonses.com"}]}},
    {"Action": "CREATE", "ResourceRecordSet": {"Name": "mail.example.com", "Type": "TXT", "TTL": 600, "ResourceRecords": [{"Value": "\"v=spf1 include:amazonses.com ~all\""}]}}
  ]
}
EOF

aws route53 change-resource-record-sets \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --change-batch file:///tmp/mailfrom-change.json
```

### Publish DMARC TXT

```bash
cat > /tmp/dmarc-change.json <<'EOF'
{
  "Changes": [
    {"Action": "CREATE", "ResourceRecordSet": {"Name": "_dmarc.example.com", "Type": "TXT", "TTL": 600, "ResourceRecords": [{"Value": "\"v=DMARC1; p=quarantine; rua=mailto:dmarc@example.com; pct=100; adkim=s; aspf=s\""}]}}
  ]
}
EOF

aws route53 change-resource-record-sets \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --change-batch file:///tmp/dmarc-change.json
```

## Per-Region MAIL FROM MX endpoints

| Region | MX endpoint |
|---|---|
| us-east-1 | `feedback-smtp.us-east-1.amazonses.com` |
| us-west-2 | `feedback-smtp.us-west-2.amazonses.com` |
| eu-west-1 | `feedback-smtp.eu-west-1.amazonses.com` |
| eu-central-1 | `feedback-smtp.eu-central-1.amazonses.com` |
| ap-south-1 | `feedback-smtp.ap-south-1.amazonses.com` |
| ap-southeast-1 | `feedback-smtp.ap-southeast-1.amazonses.com` |
| ap-southeast-2 | `feedback-smtp.ap-southeast-2.amazonses.com` |
| ap-northeast-1 | `feedback-smtp.ap-northeast-1.amazonses.com` |

## MAIL FROM domain lifecycle

### Set the MAIL FROM domain

```bash
aws sesv2 put-email-identity-mail-from-domain \
  --email-identity example.com \
  --mail-from-domain mail.example.com \
  --behavior-on-mx-failure UseDefaultValue \
  --region us-east-1
```

`BehaviorOnMxFailure`: `UseDefaultValue` (fall back to
amazonses.com) or `RejectMessage` (reject if MX not found).

### Read MAIL FROM status

```bash
aws sesv2 get-email-identity \
  --email-identity example.com \
  --query 'MailFromDomainAttributes' \
  --region us-east-1
```

`MailFromDomainStatus` cycles `PENDING` → `SUCCESS` (or
`FAILED`).

## Configuration set lifecycle

### Create the configuration set

```bash
aws sesv2 create-configuration-set \
  --configuration-set-name transactional-cs \
  --tracking-options '{"CustomRedirectDomain": "click.example.com"}' \
  --delivery-options '{"SendingPoolName": "transactional-pool", "TlsPolicy": "REQUIRE"}' \
  --region us-east-1
```

### Attach CloudWatch event destination

```bash
cat > /tmp/cw-destination.json <<'EOF'
{
  "ConfigurationSetName": "transactional-cs",
  "EventDestinationName": "cloudwatch-events",
  "EventDestination": {
    "Enabled": true,
    "MatchingEventTypes": ["SEND", "DELIVERY", "BOUNCE", "COMPLAINT", "OPEN", "CLICK"],
    "CloudWatchDestination": {
      "DimensionConfigurations": [
        {"DimensionName": "Campaign", "DimensionValueSource": "EMAIL_HEADER", "DefaultDimensionValue": "transactional"}
      ]
    }
  }
}
EOF

aws sesv2 create-configuration-set-event-destination \
  --cli-input-json file:///tmp/cw-destination.json \
  --region us-east-1
```

### Attach SNS destination for bounce / complaint

```bash
cat > /tmp/sns-destination.json <<'EOF'
{
  "ConfigurationSetName": "transactional-cs",
  "EventDestinationName": "sns-feedback",
  "EventDestination": {
    "Enabled": true,
    "MatchingEventTypes": ["BOUNCE", "COMPLAINT"],
    "SnsDestination": {"TopicArn": "arn:aws:sns:us-east-1:111122223333:ses-feedback"}
  }
}
EOF

aws sesv2 create-configuration-set-event-destination \
  --cli-input-json file:///tmp/sns-destination.json \
  --region us-east-1
```

### Attach Firehose destination

```bash
cat > /tmp/firehose-destination.json <<'EOF'
{
  "ConfigurationSetName": "transactional-cs",
  "EventDestinationName": "firehose-events",
  "EventDestination": {
    "Enabled": true,
    "MatchingEventTypes": ["SEND", "DELIVERY", "BOUNCE", "COMPLAINT", "OPEN", "CLICK"],
    "KinesisFirehoseDestination": {
      "DeliveryStreamArn": "arn:aws:firehose:us-east-1:111122223333:deliverystream/ses-events",
      "IamRoleArn": "arn:aws:iam::111122223333:role/SESFirehoseRole"
    }
  }
}
EOF

aws sesv2 create-configuration-set-event-destination \
  --cli-input-json file:///tmp/firehose-destination.json \
  --region us-east-1
```

### Attach EventBridge destination

```bash
cat > /tmp/eb-destination.json <<'EOF'
{
  "ConfigurationSetName": "transactional-cs",
  "EventDestinationName": "eventbridge-events",
  "EventDestination": {
    "Enabled": true,
    "MatchingEventTypes": ["SEND", "DELIVERY", "BOUNCE", "COMPLAINT"],
    "EventBridgeDestination": {
      "EventBusArn": "arn:aws:events:us-east-1:111122223333:event-bus/default"
    }
  }
}
EOF

aws sesv2 create-configuration-set-event-destination \
  --cli-input-json file:///tmp/eb-destination.json \
  --region us-east-1
```

## Dedicated IP pool lifecycle

### Create the pool

```bash
aws sesv2 create-dedicated-ip-pool \
  --pool-name transactional-pool \
  --region us-east-1
```

### Allocate dedicated IPs

Requires service quota approval. Once allocated, the IPs appear
in `list-dedicated-ips`:

```bash
aws sesv2 list-dedicated-ips \
  --pool-name transactional-pool \
  --region us-east-1
```

### Enable warmup on each IP

```bash
aws sesv2 put-dedicated-ip-warmup-attributes \
  --ip 10.0.0.1 \
  --warmup-enabled \
  --region us-east-1

aws sesv2 get-dedicated-ip \
  --ip 10.0.0.1 \
  --region us-east-1
```

`WarmupStatus`: `IN_PROGRESS` → `DONE`. `WarmupPercentage` ramps
0 → 100 over ~45 days.

### Assign pool to configuration set

```bash
aws sesv2 put-configuration-set-delivery-options \
  --configuration-set-name transactional-cs \
  --sending-pool-name transactional-pool \
  --region us-east-1
```

## Email template lifecycle

### Create the template

```bash
cat > /tmp/template.json <<'EOF'
{
  "TemplateName": "OrderConfirmation",
  "TemplateContent": {
    "Subject": "Your order #{{orderNumber}} is confirmed",
    "Html": "<html><body><h1>Order {{orderNumber}}</h1><p>Total: {{total}}</p><p>Items:</p><ul>{{#each items}}<li>{{this.name}} x{{this.qty}}</li>{{/each}}</ul></body></html>",
    "Text": "Order {{orderNumber}}\nTotal: {{total}}\nItems:\n{{#each items}}- {{this.name}} x{{this.qty}}\n{{/each}}"
  }
}
EOF

aws sesv2 create-email-template \
  --cli-input-json file:///tmp/template.json \
  --region us-east-1
```

### List / get / update / delete templates

```bash
aws sesv2 list-email-templates --region us-east-1

aws sesv2 get-email-template \
  --template-name OrderConfirmation \
  --region us-east-1

aws sesv2 update-email-template \
  --template-name OrderConfirmation \
  --template-content '{"Subject": "Updated subject", "Html": "...", "Text": "..."}' \
  --region us-east-1

aws sesv2 delete-email-template \
  --template-name OrderConfirmation \
  --region us-east-1
```

## Suppression list lifecycle

### Set account-level suppression attributes

```bash
aws sesv2 put-suppression-attributes \
  --suppressed-attributes BOUNCE COMPLAINT \
  --region us-east-1

aws sesv2 get-suppression-attributes --region us-east-1
```

### Add / list / delete specific addresses

```bash
aws sesv2 put-suppressed-destination \
  --email-address spamtrap@example.com \
  --reason COMPLAINT \
  --region us-east-1

aws sesv2 list-suppressed-destinations \
  --start-date 2026-01-01 \
  --end-date 2026-12-31 \
  --region us-east-1

aws sesv2 delete-suppressed-destination \
  --email-address spamtrap@example.com \
  --region us-east-1
```

## Send a test email

```bash
aws sesv2 send-email \
  --from-email-address noreply@example.com \
  --destination '{"ToAddresses": ["recipient@example.com"]}' \
  --content '{"Template": {"TemplateName": "OrderConfirmation", "TemplateData": "{\"orderNumber\": \"12345\", \"total\": \"$99.00\", \"items\": [{\"name\": \"Widget\", \"qty\": 2}]}"}}' \
  --configuration-set-name transactional-cs \
  --region us-east-1
```

## VPC endpoint

```bash
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-abcdef1234 \
  --service-name com.amazonaws.us-east-1.sesv2 \
  --subnet-ids subnet-aaa subnet-bbb \
  --security-group-ids sg-mail-sender \
  --vpc-endpoint-type Interface \
  --private-dns-enabled \
  --region us-east-1
```

## Terraform equivalents

### Domain identity + DKIM

```hcl
resource "aws_sesv2_email_identity" "domain" {
  email_identity = "example.com"
}

resource "aws_sesv2_email_identity_dkim_signing_attributes" "dkim" {
  email_identity   = aws_sesv2_email_identity.domain.email_identity
  signing_enabled  = true
}

resource "aws_route53_record" "dkim" {
  count   = 3
  zone_id = aws_route53_zone.main.zone_id
  name    = "${aws_sesv2_email_identity_dkim_signing_attributes.dkim.dkim_signing_attributes.tokens[count.index]}._domainkey.example.com"
  type    = "CNAME"
  ttl     = 1800
  records = ["${aws_sesv2_email_identity_dkim_signing_attributes.dkim.dkim_signing_attributes.tokens[count.index]}.dkim.amazonses.com"]
}
```

### Configuration set + event destination

```hcl
resource "aws_sesv2_configuration_set" "transactional" {
  configuration_set_name = "transactional-cs"
  delivery_options {
    sending_pool_name = "transactional-pool"
    tls_policy        = "REQUIRE"
  }
}

resource "aws_sesv2_configuration_set_event_destination" "cw" {
  configuration_set_name = aws_sesv2_configuration_set.transactional.configuration_set_name
  event_destination_name = "cloudwatch-events"
  event_destination {
    enabled               = true
    matching_event_types  = ["SEND", "DELIVERY", "BOUNCE", "COMPLAINT", "OPEN", "CLICK"]
    cloud_watch_destination {
      dimension_configuration {
        dimension_name          = "Campaign"
        dimension_value_source  = "EMAIL_HEADER"
        default_dimension_value = "transactional"
      }
    }
  }
}
```

### Dedicated IP pool

```hcl
resource "aws_sesv2_dedicated_ip_pool" "transactional" {
  pool_name = "transactional-pool"
}
```

## Verification

```bash
aws sesv2 get-account --region us-east-1
aws sesv2 get-email-identity --email-identity example.com --region us-east-1
aws sesv2 get-configuration-set --configuration-set-name transactional-cs --region us-east-1
aws sesv2 get-dedicated-ip-pool --pool-name transactional-pool --region us-east-1
aws sesv2 list-email-templates --region us-east-1
aws sesv2 get-suppression-attributes --region us-east-1
aws ec2 describe-vpc-endpoints --service-name com.amazonaws.us-east-1.sesv2 --region us-east-1
```

---

### Step 3: Configure the MAIL FROM domain (SPF alignment)

The custom MAIL FROM domain (`mail.example.com`) replaces the
default `amazonses.com` envelope sender, enabling SPF alignment.

```bash
aws sesv2 put-email-identity-mail-from-domain \
  --email-identity example.com \
  --mail-from-domain mail.example.com \
  --behavior-on-mx-failure UseDefaultValue \
  --region us-east-1
```

Publish the MX and SPF TXT records:

```bash
cat > /tmp/mailfrom-change.json <<'EOF'
{
  "Changes": [
    {
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "mail.example.com",
        "Type": "MX",
        "TTL": 600,
        "ResourceRecords": [{ "Value": "10 feedback-smtp.us-east-1.amazonses.com" }]
      }
    },
    {
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "mail.example.com",
        "Type": "TXT",
        "TTL": 600,
        "ResourceRecords": [{ "Value": "\"v=spf1 include:amazonses.com ~all\"" }]
      }
    }
  ]
}
EOF

aws route53 change-resource-record-sets \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --change-batch file:///tmp/mailfrom-change.json
```

The MX record Region endpoint varies: `feedback-smtp.us-east-1.
amazonses.com` for us-east-1; check the SES docs for other
Regions.


### Step 4: Publish the DMARC record

DMARC is published by the domain owner as a TXT record at
`_dmarc.example.com`. SES does not manage DMARC; the operator
publishes it.

```bash
cat > /tmp/dmarc-change.json <<'EOF'
{
  "Changes": [
    {
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "_dmarc.example.com",
        "Type": "TXT",
        "TTL": 600,
        "ResourceRecords": [{ "Value": "\"v=DMARC1; p=quarantine; rua=mailto:dmarc@example.com; pct=100; adkim=s; aspf=s\"" }]
      }
    }
  ]
}
EOF

aws route53 change-resource-record-sets \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --change-batch file:///tmp/dmarc-change.json
```

Start with `p=quarantine`; escalate to `p=reject` once alignment
is verified. `adkim=s` / `aspf=s` enforce strict alignment.


### Step 5: Create the configuration set with event publishing

The configuration set is the unit of event publishing. Create it
with the event destinations (CloudWatch, SNS, Firehose,
EventBridge).

```bash
aws sesv2 create-configuration-set \
  --configuration-set-name transactional-cs \
  --tracking-options '{"CustomRedirectDomain": "click.example.com"}' \
  --region us-east-1

# Attach CloudWatch event destination
cat > /tmp/cw-destination.json <<'EOF'
{
  "ConfigurationSetName": "transactional-cs",
  "EventDestinationName": "cloudwatch-events",
  "EventDestination": {
    "Enabled": true,
    "MatchingEventTypes": ["SEND", "DELIVERY", "BOUNCE", "COMPLAINT", "OPEN", "CLICK"],
    "CloudWatchDestination": {
      "DimensionConfigurations": [
        {
          "DimensionName": "Campaign",
          "DimensionValueSource": "EMAIL_HEADER",
          "DefaultDimensionValue": "transactional"
        }
      ]
    }
  }
}
EOF

aws sesv2 create-configuration-set-event-destination \
  --cli-input-json file:///tmp/cw-destination.json \
  --region us-east-1

# Attach SNS destination for bounce / complaint
cat > /tmp/sns-destination.json <<'EOF'
{
  "ConfigurationSetName": "transactional-cs",
  "EventDestinationName": "sns-feedback",
  "EventDestination": {
    "Enabled": true,
    "MatchingEventTypes": ["BOUNCE", "COMPLAINT"],
    "SnsDestination": {
      "TopicArn": "arn:aws:sns:us-east-1:111122223333:ses-feedback"
    }
  }
}
EOF

aws sesv2 create-configuration-set-event-destination \
  --cli-input-json file:///tmp/sns-destination.json \
  --region us-east-1
```

`MatchingEventTypes` controls which events publish: `SEND`,
`DELIVERY`, `BOUNCE`, `COMPLAINT`, `OPEN`, `CLICK`,
`REJECT`, `RENDERING_FAILURE`, `DELIVERYDELAY`, `SUBSCRIPTION`.
For bounce / complaint processing, always include `BOUNCE` and
`COMPLAINT`.

