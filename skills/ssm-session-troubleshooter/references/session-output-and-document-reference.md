# SSM Session Output & Document Reference Guide

Supplementary reference for the SSM Session Troubleshooter skill.
Loaded on-demand when a diagnostic needs the session document schema,
audit-log bucket policy templates, CloudWatch Logs delivery config,
shell-profile guidance, or port forwarding document variants.

## SSM-SessionManagerRunShell default document

The default session document carries the S3 audit bucket, CloudWatch
Logs group, KMS key, and shell profile. It is region-scoped (one per
Region per account).

### Schema

```json
{
  "schemaVersion": "1.0",
  "description": "Document to hold regional settings for Session Manager",
  "sessionType": "Standard_Stream",
  "inputs": {
    "s3BucketName": "",
    "s3KeyPrefix": "",
    "s3EncryptionEnabled": false,
    "cloudWatchLogGroupName": "",
    "cloudWatchStreamingEnabled": false,
    "kmsKeyId": "",
    "runAsEnabled": false,
    "runAsDefaultUser": "",
    "shellProfile": {
      "linux": "bash",
      "windows": "PowerShell",
      "macos": "zsh"
    }
  }
}
```

Empty `s3BucketName` / `cloudWatchLogGroupName` disable those output
paths. Sessions work but produce no audit trail.

### Updating the default document

```bash
# Read the current document
aws ssm get-document --name SSM-SessionManagerRunShell --query 'DocumentContent' --output json > session-doc.json

# Edit session-doc.json to set s3BucketName, cloudWatchLogGroupName, etc.

# Update
aws ssm update-document --name SSM-SessionManagerRunShell \
  --content file://session-doc.json --document-format JSON

# Verify
aws ssm get-document --name SSM-SessionManagerRunShell --output json
```

`update-document` on the default document affects every session
using it. Test changes on a custom document first.

### Custom session document

```bash
aws ssm create-document \
  --name Custom-Session-With-Audit \
  --document-type Session \
  --content file://custom-session.json \
  --document-format JSON
```

The caller invokes with `--document-name Custom-Session-With-Audit`.

## S3 audit-log bucket policy

The session-output bucket must grant the instance role `s3:PutObject`.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "SSMSessionOutputWrite",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::<account>:role/<instance-role>"},
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::<session-bucket>/<prefix>/*"
    }
  ]
}
```

For SSE-KMS buckets, the instance role also needs
`kms:GenerateDataKey` on the KMS key ARN, and the key policy must
grant the role `kms:GenerateDataKey`.

## CloudWatch Logs delivery

Set `cloudWatchLogGroupName` and `cloudWatchStreamingEnabled: true`
in the document. The instance role needs:

| Action | Resource |
|---|---|
| `logs:CreateLogStream` | `arn:aws:logs:<region>:<account>:log-group:<group>*` |
| `logs:PutLogEvents` | `arn:aws:logs:<region>:<account>:log-group:<group>*` |

For cross-account log groups, add a resource policy on the
destination account granting `logs:PutLogEvents` to the source-
account role or the SSM service principal.

## Session recording (shell scrollback)

Session recording captures the full shell scrollback to S3 as a
separate object from the JSON audit log. The recording uses the
same `s3BucketName` but a distinct `s3KeyPrefix` suffix.

To enable recording, set in the document:

```json
{
  "inputs": {
    "s3BucketName": "<session-bucket>",
    "s3KeyPrefix": "recording/",
    "cloudWatchLogGroupName": "<log-group>",
    "cloudWatchStreamingEnabled": true
  }
}
```

If scrollback is truncated, check:
- The document `s3KeyPrefix` is distinct from the JSON audit prefix.
- The instance role has `s3:PutObject` on the recording prefix.
- SSE-KMS bucket: role has `kms:GenerateDataKey`.

## Shell profile guidance

The `shellProfile` field sets the shell launched by Session Manager.

| Platform | Default | Custom example |
|---|---|---|
| Linux | `bash` | `/bin/zsh -l` |
| Windows | `PowerShell` | `pwsh -NoProfile` |
| macOS | `zsh` | `/bin/bash --noprofile` |

### Common shell-profile failure modes

| Failure | Symptom | Cause |
|---|---|---|
| `.bashrc` contains `exit` or `logout` | Session opens, closes in < 1s | Shell exits immediately |
| `.bash_profile` syntax error | Session opens, closes | Shell fails to spawn |
| Custom `shellProfile` binary missing | Session opens, closes | Binary path does not exist on instance |
| Prompt does not terminate (no newline) | Session appears to hang | Shell waits for input |
| `runAsDefaultUser` does not exist on instance | Session fails to open | OS user missing |

### Diagnosing shell-profile failures

On the instance, check the agent log:

```bash
tail -n 200 /var/log/amazon/ssm/amazon-ssm-agent.log | grep -iE "SessionTypeHandler|shell|profile|exit"
```

A `SessionTypeHandler` error with a non-zero exit code within
milliseconds of session start is the shell-profile signature.

## Port forwarding document variants

| Document name | Use case |
|---|---|
| `AWS-StartPortForwardingSession` | Forward to a port on the SSM instance itself (e.g., the instance's SSH on 22) |
| `AWS-StartPortForwardingSessionToRemoteHost` | Forward to a remote host reached from the SSM instance (e.g., an RDS instance) |
| `AWS-StartPortForwardingSessionToRemotePort` | Forward to a remote host on a custom port |

### Parameters

```json
{
  "portNumber": ["22"],
  "hostName": ["10.0.1.50"]
}
```

- For `AWS-StartPortForwardingSession`, `hostName` is optional
  (defaults to `localhost` on the instance).
- For `ToRemoteHost`, `hostName` is required and resolved from the
  instance, NOT the caller.
- `localPortNumber` is optional (defaults to an ephemeral port on
  the caller).

### Port forwarding requirements

- Agent version >= 3.0.196.
- Instance role: same `ssmmessages:*` as interactive sessions.
- Caller role: `ssm:StartSession` on the document and instance.
- Target host reachable from the instance's network perspective.

## macOS-specific notes

- macOS session support requires agent 3.1.x or higher.
- The agent on macOS is installed via the AWS-provided PKG or
  Homebrew (`brew install amazon-ssm-agent`).
- The agent runs as a launchd service:
  `sudo launchctl list | grep amazon-ssm-agent`.
- EC2 macOS instances require the Apple-specific VPP (Volume
  Purchase Program) licence; non-licensed macOS instances cannot
  run the SSM Agent.

## Hybrid (non-EC2) enrollment

Non-EC2 instances (on-premises servers, other-cloud VMs) enroll
via an activation code:

```bash
aws ssm create-activation \
  --iam-role <service-role-for-hybrid> \
  --registration-limit 10 \
  --expiration-date 2026-12-31
```

The activation returns a code and ID; the agent on the instance
registers with:

```bash
sudo amazon-ssm-agent -register -code "<activation-code>" -id "<activation-id>" -region <region>
```

Activation codes are SINGLE-USE per instance and expire on the
`expiration-date`. After expiration, a restarted agent cannot re-
register — the instance disappears from
`describe-instance-information`.

## Patch-baseline interaction with sessions

Patch baseline associations (`ScanOnly` or `Install`) do not
directly block sessions, but a large patch Install in `Running`
state can make the agent slow to respond to the session data
channel open. Check `describe-instance-associations-status` if
sessions fail during a known maintenance window.

```bash
aws ssm describe-instance-associations-status --instance-id <i-id> --output json
```

An association in `Running` state during the session failure window
is the signature. Wait for the patch to complete, or reschedule the
maintenance window outside session hours.



### Session document schema (SSM-SessionManagerRunShell)

```json
{
  "schemaVersion": "1.0",
  "sessionType": "Standard_Stream",
  "inputs": {
    "s3BucketName": "",
    "s3KeyPrefix": "",
    "s3EncryptionEnabled": false,
    "cloudWatchLogGroupName": "",
    "cloudWatchStreamingEnabled": false,
    "kmsKeyId": "",
    "runAsEnabled": false,
    "runAsDefaultUser": "",
    "shellProfile": {"linux": "bash", "windows": "PowerShell"}
  }
}
```

Empty `s3BucketName` / `cloudWatchLogGroupName` disable those
output paths. Sessions work but produce no audit trail.
