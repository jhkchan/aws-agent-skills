# Channels, Segments, and Templates Reference

Supplementary reference for the Pinpoint Campaign Deployer skill. Use when
configuring channels (email, SMS, push, voice), creating segments
(demographic, dynamic, imported), or designing message templates.

## Channel configuration

### Email channel

The email channel uses Amazon SES under the hood. The SES identity (domain
or email address) MUST be verified in the same AWS region as the Pinpoint
project.

```bash
aws pinpoint update-email-channel \
  --application-id <id> \
  --email-channel-request '{
    "FromAddress": "noreply@example.com",
    "Identity": "arn:aws:ses:us-east-1:111111111111:identity/example.com",
    "RoleArn": "arn:aws:iam::111111111111:role/PinpointEmailRole"
  }'
```

**Prerequisites:**
- SES identity verified: `aws sesv2 get-email-identity --email-identity example.com`
- If using a domain identity, the domain's DNS must have the SES
  verification TXT and DKIM CNAME records.
- If sending from a dedicated IP, configure a SES configuration set with
  the IP pool and reference it via the `RoleArn` or message configuration.

**Common issues:**
- Identity not verified: campaign sends 0 messages silently.
- Identity in wrong region: Pinpoint and SES MUST be in the same region.
- SES in sandbox mode: can only send to verified email addresses. Request
  production access via the SES console before production campaigns.

### SMS channel

The SMS channel requires a provisioned origination number (short code, long
code, or toll-free number).

```bash
aws pinpoint update-sms-channel \
  --application-id <id> \
  --sms-channel-request '{"ShortCode":"12345","SenderId":"MYBRAND"}'
```

**Prerequisites:**
- Origination number provisioned via Pinpoint SMS and Voice: `aws
  pinpoint-phone-number describe-phone-numbers`
- Monthly spend limit configured (default: $1/month; raise via AWS support
  or the Pinpoint console).
- For US sending: 10DLC (10-digit long code) or toll-free registration
  required for A2P (Application-to-Person) compliance. Short codes require
  a campaign registration.

**Cost:** $0.00645 per message (US). International rates are higher. A
campaign to 100K US recipients costs $645 per send.

### Push channel (APNs - iOS)

```bash
aws pinpoint update-apns-channel \
  --application-id <id> \
  --apns-channel-request '{
    "BundleId": "com.example.app",
    "TeamId": "ABCDE12345",
    "TokenKey": "-----BEGIN PRIVATE KEY-----\nMIGTAg...\n-----END PRIVATE KEY-----",
    "TokenKeyId": "ABC1234567"
  }'
```

**Prerequisites:**
- Apple Developer account with an Apple Push Notification service (APNs)
  key (`.p8` file).
- `TokenKeyId`: the key ID from the Apple Developer portal.
- `TeamId`: the Apple Developer team ID (found in Membership details).
- `BundleId`: the iOS app bundle identifier.

**Common issues:**
- Expired APNs certificate: if using certificate-based auth (legacy), the
  certificate expires annually. Token-based auth (`.p8`) does not expire.
- Wrong BundleId: push sends silently fail. Verify the BundleId matches the
  iOS app exactly.

### Push channel (FCM - Android)

```bash
aws pinpoint update-gcm-channel \
  --application-id <id> \
  --gcm-channel-request '{"ApiKey": "AAAA..."}'
```

**Prerequisites:**
- Firebase project with Cloud Messaging enabled.
- Legacy API key (server key) from Firebase Console > Project Settings >
  Cloud Messaging.
- For newer setups: service account JSON (recommended by Google).

**Common issues:**
- Legacy API key deprecated: Google is phasing out legacy server keys in
  favor of service account JSON. If the legacy key does not work, use the
  service account JSON approach.
- Wrong project: verify the Firebase project matches the Android app.

### Voice channel

```bash
aws pinpoint update-voice-channel \
  --application-id <id> \
  --voice-channel-request '{"Enabled": true}'
```

Voice uses the same origination number pool as SMS. Cost: ~$0.012-0.06 per
minute depending on destination. Use only for critical alerts (fraud,
security) — not for marketing.

## Segment types

### Demographic segment (dimension-based)

```json
{
  "Name": "premium-ios-active",
  "SegmentGroups": {
    "Groups": [{
      "Dimensions": [
        {"DeviceType": {"DimensionType": "IN", "Values": ["ios"]}},
        {"Attributes": {"tier": {"DimensionType": "IN", "Values": ["premium"]}}},
        {"UserAttributes": {"lifecycle": {"DimensionType": "IN", "Values": ["active"]}}}
      ],
      "SourceType": "ANY"
    }]
  }
}
```

**`SourceType`:**
- `ANY`: endpoint matches if ANY dimension matches (OR).
- `ALL`: endpoint matches if ALL dimensions match (AND).

**Dimension types:**
| Field | Description |
|---|---|
| `DeviceType` | iOS, Android, web |
| `Platform` | APNS, GCM, ADM |
| `Attributes` | Custom endpoint attributes |
| `UserAttributes` | Custom user attributes |
| `Behavior` | Event-based (recency, frequency) |
| `Demographic` | App version, channel type, model |

### Dynamic segment (event-based)

```json
{
  "Name": "recent-purchasers",
  "SegmentGroups": {
    "Groups": [{
      "Dimensions": [{
        "Behavior": {
          "Recency": {"DimensionType": "AFTER", "Amount": "7"},
          "Events": [{"EventType": "purchase", "DimensionType": "IN"}]
        }
      }],
      "SourceType": "ANY"
    }]
  }
}
```

Dynamic segments update as endpoint attributes and events change. A segment
defined by `purchase event in last 7 days` includes different endpoints each
day.

### Imported segment (CSV or S3)

```bash
aws pinpoint create-import-job \
  --application-id <id> \
  --import-job-request '{
    "DefineSegment": true,
    "SegmentName": "imported-list",
    "Format": "CSV",
    "RoleArn": "arn:aws:iam::111111111111:role/PinpointImport",
    "S3Url": "s3://my-bucket/segments/list.csv"
  }'
```

**CSV format:**
```csv
Id,Address,ChannelType,User.UserAttributes.FirstName
1,user1@example.com,EMAIL,Alice
2,+12025550100,SMS,Bob
3,device-token-xyz,GCM,Charlie
```

**S3 bucket requirements:**
- Bucket MUST grant `s3:GetObject` to the Pinpoint service principal.
- Bucket MUST be in the same region as the Pinpoint project.
- CSV file size limit: 5 GB.

Imported segments are static — they do not update as endpoint attributes
change. Re-import to refresh.

### Segment resolution verification

```bash
aws pinpoint get-segment-estimate \
  --application-id <id> --segment-id <seg-id>
```

ALWAYS verify segment resolution before campaign creation. A segment
resolving to 0 endpoints produces a campaign that sends nothing — silently.

## Message templates

### Email template

```json
{
  "TemplateName": "welcome-email",
  "Subject": "Welcome {{UserAttributes.FirstName|default:'there'}}",
  "HtmlPart": "<html><body><h1>Hi {{UserAttributes.FirstName}}</h1><p>Welcome!</p></body></html>",
  "TextPart": "Hi {{UserAttributes.FirstName}}, welcome!"
}
```

### SMS template

```json
{
  "TemplateName": "otp-sms",
  "Body": "Your code: {{Attributes.code}}. Expires in 10 min. Do not share."
}
```

### Push template

```json
{
  "TemplateName": "promo-push",
  "APNS": {
    "Title": "{{UserAttributes.FirstName}}, 20% off!",
    "Body": "Shop now -> {{Attributes.url}}",
    "Action": "DEEP_LINK",
    "Url": "{{Attributes.deep_link}}"
  },
  "GCM": {
    "Title": "{{UserAttributes.FirstName}}, 20% off!",
    "Body": "Shop now -> {{Attributes.url}}"
  }
}
```

### Liquid personalization

| Variable | Source |
|---|---|
| `{{UserAttributes.X}}` | User-level custom attributes |
| `{{Attributes.X}}` | Endpoint-level custom attributes |
| `{{Location.X}}` | Endpoint location (City, Country, etc.) |
| `{{Demographic.X}}` | Demographic (AppVersion, Platform, etc.) |
| `{{X\|default:'fallback'}}` | Default value if attribute missing |

Invalid Liquid syntax causes send failure at the individual endpoint level.
Pinpoint skips the endpoint and continues with others — verify templates in
a test segment first.
