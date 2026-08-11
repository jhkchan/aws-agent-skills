# Managed Workflows and AS2 — Transfer Family Deployer

Deep reference on Transfer Family managed workflows (Step Functions-
based file processing pipelines) and AS2 connectors (B2B EDI file
exchange). Includes workflow step types, on-exception handling,
certificate exchange for AS2, and MDN configuration. Loaded on demand
by the skill — kept out of the main SKILL.md body so the provisioning
procedure stays scannable.

## Managed workflows

Managed workflows automate file processing via AWS Step Functions.
When a file is uploaded via SFTP/FTPS/FTP, Transfer Family triggers
the attached workflow, which executes a series of steps.

### Workflow step types

| Step type | Description | Use case |
|---|---|---|
| `COPY` | Copy the file to another S3 location | Distribute to data lake |
| `TAG` | Add tags to the file | Mark as processed/failed |
| `DELETE` | Delete the file | Remove after processing |
| `CUSTOM` | Invoke a Lambda function | Virus scan, validation, ETL |

### Workflow definition structure

```json
{
  "Steps": [
    {
      "Type": "COPY",
      "CopyStepDetails": {
        "Name": "CopyToDataLake",
        "DestinationFileLocation": {
          "S3FileLocation": {
            "Bucket": "processed-data",
            "Key": "landing/"
          }
        },
        "OverwriteExisting": "TRUE"
      }
    },
    {
      "Type": "TAG",
      "TagStepDetails": {
        "Name": "TagProcessed",
        "Tags": [
          {"Key": "Status", "Value": "Processed"},
          {"Key": "ProcessedAt", "Value": "${Transfer:UploadDate}"}
        ]
      }
    },
    {
      "Type": "CUSTOM",
      "CustomStepDetails": {
        "Name": "VirusScan",
        "Target": "arn:aws:lambda:us-east-1:xxx:function:virus-scan",
        "TimeoutSeconds": 60
      }
    }
  ],
  "OnExceptionSteps": [
    {
      "Type": "TAG",
      "TagStepDetails": {
        "Name": "TagFailed",
        "Tags": [{"Key": "Status", "Value": "Failed"}]
      }
    }
  ]
}
```

### Creating and attaching a workflow

```bash
# Create the workflow
WORKFLOW_ID=$(aws transfer create-workflow \
  --description "File landing zone pipeline" \
  --steps file://workflow-steps.json \
  --on-exception-steps file://exception-steps.json \
  --query 'WorkflowId' --output text)

# Attach to the Transfer Family server
aws transfer update-server \
  --server-id s-abc123 \
  --workflow-id "$WORKFLOW_ID"
```

### Workflow execution monitoring

Each file upload triggers a separate Step Functions execution. Monitor
via CloudWatch or the Transfer Family console:

```bash
# List recent workflow executions
aws transfer list-workflows

# Describe a specific workflow
aws transfer describe-workflow --workflow-id w-xxx

# View Step Functions execution history
aws stepfunctions list-executions \
  --state-machine-arn arn:aws:states:us-east-1:xxx:stateMachine:TransferWorkflow-xxx
```

### Common workflow patterns

**Virus scan pipeline:**
1. COPY to quarantine bucket
2. CUSTOM Lambda virus scan
3. On success: COPY to clean bucket, TAG Status=Clean
4. On failure: DELETE from quarantine, TAG Status=Infected, SNS alert

**Data lake landing:**
1. COPY to raw zone
2. CUSTOM Lambda validate schema
3. On success: COPY to processed zone, TAG Status=Validated
4. On failure: TAG Status=Invalid, SNS notify data team

**Partner file distribution:**
1. COPY to distribution bucket
2. TAG with partner name and timestamp
3. CUSTOM Lambda trigger downstream webhook

## AS2 connectors

AS2 (Applicability Statement 2) is a B2B file transfer protocol for
EDI (Electronic Data Interchange). It provides message-level
encryption, signing, and delivery confirmation via MDN (Message
Disposition Notification).

### AS2 architecture

```text
Your Organization (Local AS2 Profile)          Partner (AS2 Profile)
  ├── Private key (for signing)                  ├── Public cert (you have)
  ├── Public certificate (shared with partner)   ├── Private key (their side)
  └── AS2 connector → sends to partner URL       └── AS2 server receives
```

### Certificate exchange

AS2 requires mutual certificate exchange:
1. Generate a key pair (RSA 2048+) for your local profile
2. Export the public certificate and share it with the partner
3. Receive the partner's public certificate
4. Import the partner's certificate into Transfer Family

```bash
# Create a local AS2 profile (generates key pair)
aws transfer create-profile \
  --as2-id "MYORG" \
  --certificate-ids cert-xxx

# Import partner's public certificate
aws transfer import-certificate \
  --usage ENCRYPTION \
  --certificate file://partner-public-cert.pem \
  --private-key file://my-private-key.pem \
  --certificate-chain file://cert-chain.pem
```

### Creating an AS2 connector

```bash
aws transfer create-connector \
  --url "https://as2.acme.com" \
  --as2-config '{
    "Compression": "ZLIB",
    "EncryptionAlgorithm": "AES256_CBC",
    "SigningAlgorithm": "SHA256",
    "MdnResponse": "SYNC",
    "MdnSigningAlgorithm": "SHA256",
    "LocalProfileId": "local-profile-xxx",
    "PartnerProfileId": "partner-profile-yyy"
  }' \
  --tags Key=Partner,Value=acme Key=Environment,Value=production
```

### AS2 configuration options

| Parameter | Options | Default | Description |
|---|---|---|---|
| `Compression` | ZLIB, NONE | NONE | Compress message payload |
| `EncryptionAlgorithm` | AES128_CBC, AES192_CBC, AES256_CBC, NONE | NONE | Encrypt payload |
| `SigningAlgorithm` | SHA256, SHA384, SHA512, SHA1, NONE | NONE | Sign the message |
| `MdnResponse` | SYNC, NONE | NONE | Request delivery confirmation |
| `MdnSigningAlgorithm` | SHA256, SHA384, SHA512, SHA1, NONE | NONE | Sign the MDN response |

**Best practice:** use AES256_CBC encryption and SHA256 signing for
production AS2 exchanges. Always request SYNC MDN for delivery
confirmation.

### Sending files via AS2

```bash
# Start a file transfer via AS2 connector
aws transfer start-file-transfer \
  --connector-id c-xxx \
  --send-file-paths '["/s3-bucket/outbound/edi-850.txt"]'
```

The connector encrypts, signs, and sends the file to the partner's
AS2 URL. The MDN response confirms successful delivery.

## Terraform examples

```hcl
# Managed workflow
resource "aws_transfer_workflow" "landing_zone" {
  description = "File landing zone pipeline"

  step {
    type = "COPY"
    copy_step_details {
      name = "CopyToDataLake"
      destination_file_location {
        s3_file_location {
          bucket = "processed-data"
          key    = "landing/"
        }
      }
      overwrite_existing = "TRUE"
    }
  }

  step {
    type = "TAG"
    tag_step_details {
      name = "TagProcessed"
      tags {
        key   = "Status"
        value = "Processed"
      }
    }
  }

  on_exception_step {
    type = "TAG"
    tag_step_details {
      name = "TagFailed"
      tags {
        key   = "Status"
        value = "Failed"
      }
    }
  }
}

# AS2 connector
resource "aws_transfer_connector" "acme" {
  url = "https://as2.acme.com"
  as2_config {
    compression             = "ZLIB"
    encryption_algorithm    = "AES256_CBC"
    signing_algorithm       = "SHA256"
    mdn_response            = "SYNC"
    mdn_signing_algorithm   = "SHA256"
    local_profile_id        = aws_transfer_profile.local.id
    partner_profile_id      = aws_transfer_profile.partner.id
  }

  tags = {
    Partner     = "acme"
    Environment = "production"
  }
}
```
