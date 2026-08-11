# Eval prompt: deploy-sftp-missing-iam-role

Plan the following Transfer Family server creation and emit the standard
VERDICT block. The IAM execution role (TransferUserS3Role) does not
exist in the account.

Operation: create
Server description: prod-sftp-inbox
Region: us-east-1
Account: 111111111111
Protocols: ["SFTP"]
EndpointType: PUBLIC
IdentityProviderType: SERVICE_MANAGED
Storage backend: S3 bucket "prod-sftp-inbox"
LoggingRole: arn:aws:iam::111111111111:role/TransferLoggingRole
Users:
  - UserName: alice
    Role: arn:aws:iam::111111111111:role/TransferUserS3Role
    HomeDirectory: /prod-sftp-inbox/alice

```json
{
  "PreFlight": {
    "s3api.head-bucket.prod-sftp-inbox": "OK",
    "iam.get-role.TransferUserS3Role": "NoSuchEntity (role does not exist)",
    "iam.get-role.TransferLoggingRole": "OK",
    "transfer.list-servers": "no collision"
  }
}
```
