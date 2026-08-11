# Eval prompt: deploy-sftp-vpc-custom-idp-ready

Plan the following Transfer Family server creation (SFTP+FTPS on VPC
endpoint with custom API Gateway Lambda IdP) and emit the standard
VERDICT block.

Operation: create
Server description: prod-sftp-vpc-custom-idp
Region: us-east-1
Account: 111111111111
Protocols: ["SFTP", "FTPS"]
EndpointType: VPC_ENDPOINT
IdentityProviderType: API_GATEWAY
IdentityProviderDetails:
  Url: https://abc123.execute-api.us-east-1.amazonaws.com/prod/
  InvocationRole: arn:aws:iam::111111111111:role/TransferIdPInvocationRole
Certificate (FTPS): arn:aws:acm:us-east-1:111111111111:certificate/abc-123
VpcId: vpc-abc123
SubnetIds: [subnet-aaa, subnet-bbb]
SecurityGroupIds: [sg-ssh, sg-ftps]
LoggingRole: arn:aws:iam::111111111111:role/TransferLoggingRole

```json
{
  "PreFlight": {
    "acm.describe-certificate": "OK (status ISSUED, subject prod-sftp.example.com)",
    "apigateway.get-rest-api.abc123": "OK (REST API exists, stage prod deployed)",
    "iam.get-role.TransferIdPInvocationRole": "OK (trusts transfer.amazonaws.com with apigateway:Invoke)",
    "curl.idp-lambda.POST.test": "200 OK {Role,HomeDirectory,Policy}",
    "ec2.describe-security-groups.sg-ssh.sg-ftps": "OK (inbound port 22 and 990)"
  }
}
```
