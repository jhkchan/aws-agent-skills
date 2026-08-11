# Eval prompt: deploy-sftp-directory-service-ready

Plan the following Transfer Family server creation (SFTP federated with
AWS Directory Service on VPC_ENDPOINT) and emit the standard VERDICT
block.

Operation: create
Server description: prod-sftp-ad
Region: us-east-1
Account: 111111111111
Protocols: ["SFTP"]
EndpointType: VPC_ENDPOINT
IdentityProviderType: AWS_DIRECTORY_SERVICE
IdentityProviderDetails:
  DirectoryId: d-abc123
Domain: example.com
VpcId: vpc-abc123
SubnetIds: [subnet-aaa, subnet-bbb]
SecurityGroupIds: [sg-ssh]
LoggingRole: arn:aws:iam::111111111111:role/TransferLoggingRole

```json
{
  "PreFlight": {
    "ds.describe-directories.d-abc123": "OK (status ACTIVE, VPC matches vpc-abc123)",
    "ec2.describe-security-groups.sg-ssh": "OK (inbound port 22)",
    "iam.get-role.TransferLoggingRole": "OK"
  }
}
```
