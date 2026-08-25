# Diagnostic Commands — S3 Access Points Deployer

Load-on-demand pre-flight and verification command listings moved
verbatim from SKILL.md.

## Step 1 — bucket baseline verification commands

```bash
aws s3api get-public-access-block --bucket <BUCKET>
aws s3api get-bucket-encryption --bucket <BUCKET>
aws s3api get-bucket-versioning --bucket <BUCKET>
```

## Step 9 — verification commands

```bash
aws s3control get-access-point --account-id <ACCOUNT_ID> --name <AP_NAME>
aws s3control get-access-point-policy --account-id <ACCOUNT_ID> --name <AP_NAME>
aws s3control get-access-point-public-access-block --account-id <ACCOUNT_ID> --name <AP_NAME>
aws s3api get-bucket-policy --bucket <BUCKET>     # confirm through-AP Deny
aws ec2 describe-vpc-endpoints --filters Name=service-name,Values=com.amazonaws.<REGION>.s3
aws s3control get-access-point-configuration-for-object-lambda --account-id <ACCOUNT_ID> --name <OLAP_NAME>  # OLAP only
aws s3control get-multi-region-access-point --account-id <ACCOUNT_ID> --name <MRAP_NAME>                       # MRAP only
```
