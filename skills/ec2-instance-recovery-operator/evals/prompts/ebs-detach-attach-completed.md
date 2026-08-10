# Eval prompt: ebs-detach-attach-completed

Plan and verify the following EC2 EBS detach/attach data salvage
operation (post-execution form) and emit the standard VERDICT block
(OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS, POST_VERIFY, NOTES).
The operation has already executed; produce the post-verification
COMPLETED form.

Operation: detach-attach-ebs (post-verification)
Instance: i-0abcdef1234567890
Volume: vol-0abc (root, /dev/xvda)
Rescue instance: i-0rescue9999 (same AZ: us-east-1a)

```json
{
  "PreExecution": {
    "SourceInstanceUnreachable": true,
    "VolumeAttached": true,
    "DeleteOnTermination": false,
    "RescueInSameAZ": true,
    "DeviceFree": true
  },
  "Execution": {
    "Steps": [
      "detach-volume vol-0abc from i-0abcdef1234567890 --force",
      "attach-volume vol-0abc to i-0rescue9999 /dev/sdf",
      "operator reverted bad config in /mnt/recovery/etc/nginx/nginx.conf",
      "detach-volume vol-0abc from i-0rescue9999",
      "attach-volume vol-0abc to i-0abcdef1234567890 /dev/xvda"
    ]
  },
  "PostExecutionVerification": {
    "DescribeVolumes": "vol-0abc in-use on i-0abcdef1234567890 at /dev/xvda",
    "InstanceBoot": "successful",
    "NginxConfig": "valid",
    "ApplicationHealth": "HTTP 200"
  }
}
```
