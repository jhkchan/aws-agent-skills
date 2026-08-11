# Certificate, Policy, and Thing Binding — IoT Core Thing Deployer

Deep reference on X.509 certificate provisioning (AWS-generated key
pair vs CSR), IoT policy syntax (connect, publish, subscribe, receive,
resource ARN patterns), and the critical triple binding (thing +
certificate + policy). Loaded on demand by the skill — kept out of the
main SKILL.md body so the provisioning procedure stays scannable.

## X.509 certificate provisioning

### Option A: AWS-generated key pair

Use when the device does not have its own key generation capability.
AWS generates the key pair and returns the private key ONCE.

```bash
RESULT=$(aws iot create-keys-and-certificate \
  --set-as-active \
  --query 'certificateArn' --output text \
  --public-key-outfile public.key \
  --private-key-outfile private.key \
  --certificate-pem-outfile certificate.pem \
  --region us-east-1)

CERT_ARN=$(echo "$RESULT" | head -1)
```

**Security warning:** the private key file (`private.key`) is the
device's secret. Store it securely (AWS Secrets Manager, parameter
store). It is NEVER retrievable again after this call.

### Option B: Certificate Signing Request (CSR)

Use when the device generates its own key pair (more secure — private
key never leaves the device).

```bash
# On the device:
openssl genrsa -out device.key 2048
openssl req -new -key device.key -out device.csr -subj "/CN=sensor-001"

# In the cloud:
CERT_ARN=$(aws iot create-certificate-from-csr \
  --certificate-signing-request file://device.csr \
  --set-as-active \
  --query 'certificateArn' --output text \
  --region us-east-1)
```

### Certificate lifecycle

```text
Certificate states:
  ACTIVE   → device can connect (if policy is attached)
  INACTIVE → device cannot connect
  REVOKED  → certificate is permanently disabled (cannot be reactivated)

Rotation:
  1. Create new certificate
  2. Attach to thing + attach policy
  3. Deploy new cert to device (via IoT job or OTA)
  4. Verify device connects with new cert
  5. Set old certificate to INACTIVE
  6. Detach old cert from thing and policy
  7. Delete old certificate
```

## IoT policy syntax

### Policy structure

An IoT policy is a JSON document with `Statement` entries, similar to
IAM policies but with IoT-specific actions and resource ARNs.

### Actions

| Action | Description | Resource |
|---|---|---|
| `iot:Connect` | MQTT connect | `client/<clientId>` |
| `iot:Publish` | Publish to a topic | `topic/<topicName>` |
| `iot:Subscribe` | Subscribe to a topic filter | `topicfilter/<filter>` |
| `iot:Receive` | Receive messages on subscribed topics | `topic/<topicName>` |
| `iot:RetainPublish` | Publish retained messages | `topic/<topicName>` |
| `iot:GetThingShadow` | Read device shadow | `thing/<thingName>` |
| `iot:UpdateThingShadow` | Update device shadow | `thing/<thingName>` |
| `iot:DeleteThingShadow` | Delete device shadow | `thing/<thingName>` |

### Resource ARN patterns

```text
arn:aws:iot:<region>:<account>:client/sensor-*        (connect)
arn:aws:iot:<region>:<account>:topic/device/+/telemetry  (publish)
arn:aws:iot:<region>:<account>:topicfilter/device/+/commands (subscribe)
arn:aws:iot:<region>:<account>:thing/sensor-001        (shadow)
```

**Wildcard matching:**
- `+` matches exactly one topic level
- `*` matches any character sequence within a level
- `#` matches multiple topic levels (only in topicfilter resources)

### Example production policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["iot:Connect"],
      "Resource": "arn:aws:iot:us-east-1:123456789012:client/sensor-${iot:connection.clientId}",
      "Condition": {
        "Bool": { "iot:Connection.Secure": "true" }
      }
    },
    {
      "Effect": "Allow",
      "Action": ["iot:Publish"],
      "Resource": "arn:aws:iot:us-east-1:123456789012:topic/device/${iot:connection.clientId}/telemetry"
    },
    {
      "Effect": "Allow",
      "Action": ["iot:Subscribe"],
      "Resource": "arn:aws:iot:us-east-1:123456789012:topicfilter/device/${iot:connection.clientId}/commands"
    },
    {
      "Effect": "Allow",
      "Action": ["iot:Receive"],
      "Resource": "arn:aws:iot:us-east-1:123456789012:topic/device/${iot:connection.clientId}/commands"
    },
    {
      "Effect": "Allow",
      "Action": ["iot:GetThingShadow", "iot:UpdateThingShadow"],
      "Resource": "arn:aws:iot:us-east-1:123456789012:thing/sensor-*"
    }
  ]
}
```

### Policy variables

IoT policies support dynamic policy variables that resolve at
connection time:

| Variable | Resolves to |
|---|---|
| `${iot:connection.clientId}` | The MQTT client ID |
| `${iot:certificateId}` | The certificate ID |
| `${iot:thingName}` | The thing name (when using thing principal) |

**Best practice:** use `${iot:connection.clientId}` in resource ARNs
to ensure a device can only publish to its own topics.

## The triple binding

The #1 cause of "device can't connect" is a missing binding. Three
artifacts must be created and two bindings must be established.

```text
  Thing                Certificate              Policy
  (where)              (who)                    (what)
    |                      |                       |
    |                      |                       |
    +--- attach-principal -+                       |
    |              (binds cert to thing)           |
    |                                              |
    +-------------- attach-policy -----------------+
                   (binds policy to cert)

  Verify:
    aws iot list-thing-principals --thing-name <thing>    → cert ARN
    aws iot list-principal-policies --principal <certArn> → policy name
    aws iot describe-certificate --certificate-id <id>    → status: ACTIVE
```

### Binding commands

```bash
# Bind certificate to thing
aws iot attach-thing-principal \
  --thing-name "sensor-001" \
  --principal "$CERT_ARN"

# Bind policy to certificate
aws iot attach-policy \
  --policy-name "sensor-publish-policy" \
  --target "$CERT_ARN"
```

### Unbinding (for cert rotation or device decommission)

```bash
# Detach policy from cert
aws iot detach-policy \
  --policy-name "sensor-publish-policy" \
  --target "$CERT_ARN"

# Detach cert from thing
aws iot detach-thing-principal \
  --thing-name "sensor-001" \
  --principal "$CERT_ARN"

# Delete certificate (must be detached first)
aws iot update-certificate --certificate-id "<id>" --new-status REVOKED
aws iot delete-certificate --certificate-id "<id>"
```

## Mutual TLS (mTLS)

IoT Core uses mutual TLS by default. The device presents its X.509
certificate during the TLS handshake. IoT Core verifies the certificate
chain and checks that the certificate is ACTIVE and has a policy
attached.

```text
mTLS handshake:
  Device → ServerHello + Certificate (device cert)
  Server → ServerHello + Certificate (AWS IoT CA cert)
  Both   → verify each other's certificates
  Result → if device cert is ACTIVE + has policy → MQTT session established
           if cert is INACTIVE or no policy → connection refused
```

**Custom CA:** for devices with custom CA-issued certificates, register
the CA certificate with IoT Core. Each device certificate must be
signed by the registered CA.

## Terraform examples

```hcl
# Create the thing
resource "aws_iot_thing" "sensor" {
  name = "sensor-001"
  thing_type_name = aws_iot_thing_type.sensor_type.name
}

# Create the certificate
resource "aws_iot_certificate" "cert" {
  active = true
}

# Create the policy
resource "aws_iot_policy" "pub_sub" {
  name = "sensor-publish-policy"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["iot:Connect"]
        Resource = "arn:aws:iot:us-east-1:123456789012:client/sensor-*"
      },
      {
        Effect = "Allow"
        Action = ["iot:Publish"]
        Resource = "arn:aws:iot:us-east-1:123456789012:topic/device/+/telemetry"
      }
    ]
  })
}

# Attach cert to thing
resource "aws_iot_thing_principal_attachment" "att" {
  thing    = aws_iot_thing.sensor.name
  principal = aws_iot_certificate.cert.arn
}

# Attach policy to cert
resource "aws_iot_policy_attachment" "att" {
  policy = aws_iot_policy.pub_sub.name
  target = aws_iot_certificate.cert.arn
}
```
