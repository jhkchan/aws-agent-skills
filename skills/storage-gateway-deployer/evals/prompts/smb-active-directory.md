# Eval: smb-active-directory

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — S3 File Gateway, SMB file share, Active Directory domain join, authenticated access, audit logging

## Prompt

Deploy an S3 File Gateway in us-east-1 with an SMB file share.
Gateway name: prod-smb-gateway. Activation key:
ABCDE-11111-FGHIJ-22222-KLMNO. S3 bucket: smb-share-bucket
(us-east-1). Join Active Directory: domain corp.example.com, OU
OU=Servers,DC=corp,DC=example,DC=com, username sgw-service.
Create an authenticated SMB file share with admin user
corp\sgw-admins. Enable audit logging to CloudWatch. Tags:
Environment=production, Protocol=smb.
