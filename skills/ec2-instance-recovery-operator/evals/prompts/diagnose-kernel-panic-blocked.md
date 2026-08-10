# Eval prompt: diagnose-kernel-panic-blocked

Plan the following EC2 instance diagnosis and emit the standard
VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, NOTES).

Operation: diagnose-impaired
Instance: i-0abcdef1234567890

```json
{
  "InstanceStatus": {
    "State": "running",
    "SystemStatus": {"Status": "ok"},
    "InstanceStatus": {"Status": "impaired"},
    "Events": []
  },
  "SsmStatus": {
    "PingStatus": "ConnectionLost"
  },
  "ConsoleOutput": "kernel panic - not syncing: Fatal module load error in xyz-driver. CPU: 0 PID: 456 Comm: modprobe. Call Trace: [...]",
  "InstanceDetails": {
    "RootDeviceType": "ebs",
    "Placement": {"Tenancy": "default"}
  }
}
```
