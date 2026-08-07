# Baseline (no-skill) response: ec2-passrole-missing

This file captures what a generic assistant produces WITHOUT the
iam-permission-troubleshooter skill loaded.

---

`Client.UnauthorizedOperation` on EC2 means you are missing IAM
permissions for the call. Even though you have `ec2:RunInstances`,
launching an instance with an instance profile also requires
permission to pass the role.

Add `iam:PassRole` to your caller's policy. You can scope it to the
specific instance profile role to keep it tight, or grant it on `*`
if you want the caller to be able to launch with any role.

Make sure you also have permissions on the subnet, security group,
AMI, and any EBS volumes you are using. EC2 evaluates resource-level
permissions for all of these at launch time.
