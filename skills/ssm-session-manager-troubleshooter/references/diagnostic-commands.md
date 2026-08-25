# Diagnostic Commands — ssm-session-manager-troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Step 4 — port-forwarding diagnostic commands

```bash
# Verify the document exists and the caller can use it
aws ssm describe-document --name AWS-StartPortForwardingSession \
  --query 'Document.[DefaultVersion,PlatformTypes]' --output table
aws iam simulate-principal-policy --policy-source-arn <caller-arn> \
  --action-names ssm:StartSession \
  --resource-arns "arn:aws:ssm:<region>:<account>:document/AWS-StartPortForwardingSession" \
  --query 'EvaluationResults[*].EvalDecision' --output text
# Probe the local port before binding
lsof -i :<local-port-number>
```

## Step 8 — latest-feature diagnostic commands (key pair, cross-account)

```bash
# Key pair: verify the EC2 key pair exists and the instance was launched with it
aws ec2 describe-key-pairs --key-names <key-name> \
  --query 'KeyPairs[*].[KeyName,KeyType]' --output table
aws ec2 describe-instances --instance-ids <instance-id> \
  --query 'Reservations[*].Instances[*].KeyName' --output text
# Cross-account: verify the target-account role trust + KMS key policy
aws iam simulate-principal-policy --policy-source-arn <caller-arn-in-source-account> \
  --action-names ssm:StartSession ssm:GetConnectionStatus \
  --query 'EvaluationResults[*].[EvalActionName,EvalDecision]' --output table
aws kms describe-key --key-id <key-id> --query 'KeyMetadata.[KeyState,MultiRegion]' --output table
aws kms get-key-policy --key-id <key-id> --policy-name default --output text
```

## Appendix A - Symptom-to-cause map (quick reference)

| Symptom | Most common root cause | Verify via |
|---|---|---|
| TargetNotReachable - EC2 | No instance profile / wrong policy / agent down | `describe-instance-information` + `describe-instances` |
| TargetNotReachable - private subnet | `ssmmessages.` endpoint missing | `describe-vpc-endpoints` |
| TargetNotReachable - hybrid `mi-*` | Activation expired | `describe-activations` |
| TargetNotReachable - fresh launch | Agent still bootstrapping (< 5 min) | `LaunchTime` vs current time |
| SessionFailsToStart - AccessDenied | Caller lacks `ssm:StartSession` | `simulate-principal-policy` |
| SessionFailsToStart - console greyed out | Console user lacks `ssm-sessionmanager-console-perm` | Identity policy check |
| SessionFailsToStart - plugin not found | Client missing `session-manager-plugin` | `session-manager-plugin --version` |
| SessionFailsToStart - KMS | Key policy blocks `kms:GenerateDataKey` | `get-key-policy` |
| PortForwardingFails - bind error | Local port in use | `lsof -i :<port>` |
| PortForwardingFails - double route | `~/.ssh/config` ProxyCommand conflict | Inspect SSH config |
| PortForwardingFails - AccessDenied | `ssm:StartSession` not scoped to `AWS-StartPortForwardingSession` | `simulate-principal-policy` |
| ShellAccessFails - agent too old | `AgentVersion` < 2.3.12.0 | `describe-instance-information` |
| ShellAccessFails - shell missing | `/bin/bash` not present; `/etc/passwd` shell is `/sbin/nologin` | `send-command` with `ls /bin/bash` |
| VpcConnectivity - endpoint missing | `ssmmessages.` or `ec2messages.` not in VPC | `describe-vpc-endpoints` |
| VpcConnectivity - SG blocks 443 | Endpoint SG ingress lacks instance subnet CIDR | `describe-security-groups` |
| VpcConnectivity - private DNS off | `PrivateDnsEnabled: false` on endpoint | `describe-vpc-endpoints` |
| SessionDisconnects - idle | `Duration` matches `IdleDisconnectTimeout` | `describe-sessions` |
| SessionDisconnects - NAT 350s | Drop at ~5m50s of idle; NAT idle timeout | Network path audit |
| SessionDisconnects - SSO token | Caller session expired | `aws sts get-caller-identity` failure |
| LatestFeature - SSH key | Instance launched without key pair; or ProxyCommand missing | `describe-instances KeyName` + SSH config |
| LatestFeature - cross-account | Target-account KMS key policy or role trust gap | `get-key-policy` + trust policy |
