# Eval prompt: deploy-ftp-public-endpoint-blocked

Plan the following Transfer Family server creation and emit the standard
VERDICT block. The server requests plain FTP on a PUBLIC endpoint.

Operation: create
Server description: legacy-ftp-public
Region: us-east-1
Account: 111111111111
Protocols: ["FTP"]
EndpointType: PUBLIC
IdentityProviderType: SERVICE_MANAGED
Storage backend: S3 bucket "legacy-ftp-inbox"
LoggingRole: arn:aws:iam::111111111111:role/TransferLoggingRole

```json
{
  "PreFlight": {
    "s3api.head-bucket.legacy-ftp-inbox": "OK",
    "iam.get-role.TransferUserS3Role": "OK",
    "iam.get-role.TransferLoggingRole": "OK",
    "transfer.list-servers": "no collision"
  }
}
```
