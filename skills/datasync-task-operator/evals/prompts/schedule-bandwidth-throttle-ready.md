# Eval prompt: schedule-bandwidth-throttle-ready

Plan the following schedule + bandwidth throttle addition for an
existing DataSync task and emit the standard VERDICT block.

Operation: create-schedule
Task: arn:aws:datasync:us-east-1:111111111111:task/task-001
  (name: nfs-to-s3-archive, Status: AVAILABLE)
Schedule: rate(1 day)
Bandwidth throttle: 1000 Mb/s

```json
{
  "Task": {
    "TaskArn": "arn:aws:datasync:us-east-1:111111111111:task/task-001",
    "Name": "nfs-to-s3-archive",
    "Status": "AVAILABLE",
    "CurrentTaskExecutionArn": null,
    "Schedule": null
  },
  "AgentUlinkMbps": 10000,
  "IamRole": {
    "Verified": true,
    "SourceRead": "s3:GetObject + s3:ListBucket",
    "DestinationWrite": "s3:PutObject + s3:AbortMultipartUpload"
  }
}
```
