# Eval prompt: deploy-sftp-service-managed-ready

Plan the following Transfer Family server creation and emit the standard
VERDICT block (SERVER, VERDICT, TARGET, PRE_CHECKS, STEPS, POST_VERIFY,
PROTOCOLS, ENDPOINT, IDP, STORAGE, SESSION_POLICY_SCOPE, WORKFLOWS,
NOTES).

Operation: create
Server description: prod-sftp-inbox
Region: us-east-1
Account: 111111111111
Protocols: ["SFTP"]
EndpointType: PUBLIC
IdentityProviderType: SERVICE_MANAGED
Storage backend: S3 bucket "prod-sftp-inbox"
LoggingRole: arn:aws:iam::111111111111:role/TransferLoggingRole
Tags: Environment=prod, Name=prod-sftp-inbox
Users:
  - UserName: alice
    SSHPublicKey: ssh-rsa AAAAB3...
    Role: arn:aws:iam::111111111111:role/TransferUserS3Role
    HomeDirectory: /prod-sftp-inbox/alice
    SessionPolicy: scope to s3://prod-sftp-inbox/alice/*
  - UserName: bob
    SSHPublicKey: ssh-rsa AAAAB3...
    Role: arn:aws:iam::111111111111:role/TransferUserS3Role
    HomeDirectory: /prod-sftp-inbox/bob
    SessionPolicy: scope to s3://prod-sftp-inbox/bob/*

```json
{
  "PreFlight": {
    "s3api.head-bucket.prod-sftp-inbox": "OK (us-east-1)",
    "iam.get-role.TransferUserS3Role": "OK (trusts transfer.amazonaws.com with SourceAccount=111111111111)",
    "iam.get-role.TransferLoggingRole": "OK (logs:CreateLogStream, logs:PutLogEvents)",
    "transfer.list-servers": "no collision"
  }
}
```
