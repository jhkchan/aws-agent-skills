# Baseline (no-skill) response: cryptocurrency-ec2-auto-isolate

This file captures what a generic assistant produces WITHOUT the
guardduty-finding-automator skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, severity-based routing,
Critical-severity immediate response, forensic snapshot, IAM key
revocation without last-used check, finding ID deduplication).

---

For a crypto mining finding, you should isolate the EC2 instance right
away. You can use a Lambda function triggered by EventBridge to change
the security group.

You might also want to take a snapshot of the EBS volume for forensics
and revoke any IAM keys associated with the instance.

The EventBridge rule should look for the GuardDuty finding type
CryptoCurrency:EC2/BitcoinTool. Set up the Lambda to stop or isolate
the instance.

I'm not sure about the exact API calls for taking a snapshot from
Lambda. You'd need to use the boto3 create_snapshot call. And for
IAM keys, you'd use update_access_key to deactivate them.

Be careful about revoking keys that might be in use — though for
crypto mining the instance is probably already compromised so it's
fine to revoke.
