# Baseline (no-skill) response: cfn-drift-addition-import-bucket

This file captures what a generic assistant produces WITHOUT the
cloudformation-drift-troubleshooter skill loaded.

---

You can bring the `app-uploads-2026` bucket under CloudFormation
management by adding it to your `app-storage` stack template. Just
declare an `AWS::S3::Bucket` resource with the bucket name and run
`aws cloudformation update-stack`.

Make sure the configuration in your template matches the existing
bucket (versioning, encryption, lifecycle) so CloudFormation doesn't
try to recreate it.

If you want to keep the existing objects, you should look into
CloudFormation resource import.
