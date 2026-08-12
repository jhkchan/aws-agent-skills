# Eval prompt: session-document-s3-bucket-empty

Diagnose the SSM Session Manager audit-log gap. Walk the symptom-
driven diagnostic tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: Session Manager sessions to `i-app-server-3` work (the
session opens and the operator gets a shell) but the compliance
team reports no JSON audit output in the
`ssm-session-output-useast1` bucket. There are zero objects under
the expected prefix.

```text
InstanceId: i-app-server-3
PlatformName: Amazon Linux 2023
AgentVersion: 3.2.1546.0
PingStatus: Online

InstanceProfile role: EC2-SSM-Role with
  AmazonSSMManagedInstanceCore attached AND an inline policy
  granting s3:PutObject on
  arn:aws:s3:::ssm-session-output-useast1/*
simulate-principal-policy for s3:PutObject on
  arn:aws:s3:::ssm-session-output-useast1/*: allowed

Session document in use (default):
  get-document SSM-SessionManagerRunShell returns:
    {
      "schemaVersion": "1.0",
      "sessionType": "Standard_Stream",
      "inputs": {
        "s3BucketName": "",
        "s3KeyPrefix": "",
        "s3EncryptionEnabled": false,
        "cloudWatchLogGroupName": "ssm-session-logs",
        "cloudWatchStreamingEnabled": true,
        "kmsKeyId": "",
        "shellProfile": {"linux": "bash"}
      }
    }
  Note: s3BucketName is empty — no S3 audit output configured in
  the document.

Bucket ssm-session-output-useast1 exists, has a bucket policy
  granting EC2-SSM-Role s3:PutObject on the bucket ARN.
  CloudWatch Logs group ssm-session-logs IS receiving streamed
  session output (so the session itself is healthy).

describe-sessions --state History shows completed sessions with
  Status: Terminated normally. No Output field set.
```

The session is healthy (CloudWatch Logs streaming works) and the
bucket policy grants the role. Identify the document-layer
configuration gap and the field to set.
