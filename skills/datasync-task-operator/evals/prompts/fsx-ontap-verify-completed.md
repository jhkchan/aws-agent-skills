# Eval prompt: fsx-ontap-verify-completed

Produce the COMPLETED post-verification form for an SMB-to-FSx for
NetApp ONTAP DataSync task that has reached Status: SUCCESS with
zero verification failures. Emit the standard VERDICT block.

Operation: transfer-to-fsx-ontap
Task: arn:aws:datasync:us-east-1:111111111111:task/task-042
  (name: smb-to-fsxn-finance)
Source: smb://10.0.20.30/share/finance
Destination: fsxn://fs-0abc123/vol1/finance (FSx for NetApp ONTAP)

```json
{
  "FsxOntap": {
    "FileSystemId": "fs-0abc123",
    "Lifecycle": "AVAILABLE",
    "Svm": {
      "SvmId": "svm-0456",
      "InterClusterEndpoint": "reachable from 10.0.30.0/24"
    }
  },
  "LatestExecution": {
    "Status": "SUCCESS",
    "StartTime": "2026-08-10T01:00:00Z",
    "BytesTransferred": 1840000000000,
    "BytesWritten": 1820000000000,
    "EstimatedFilesToTransfer": 48231,
    "FilesTransferred": 48231,
    "VerificationFilesTransferred": 48231,
    "VerificationFilesFailed": 0
  },
  "Options": {
    "SecurityDescriptorCopyFlags": "OWNER_DACL",
    "VerifyMode": "POINT_IN_TIME_CONSISTENT",
    "Acl": "PRESERVE"
  },
  "SpotCheck": {
    "File": "\\\\fsx\\vol1\\finance\\2026\\Q3.xlsx",
    "SourceSize": 4404019,
    "DestinationSize": 4404019,
    "SourceMtime": "2026-07-15T10:30:00Z",
    "DestinationMtime": "2026-07-15T10:30:00Z",
    "AclPreserved": "OWNER_DACL"
  },
  "TaskReports": {
    "Configured": true,
    "ReportObject": "s3://datasync-reports-111111111111/task-042/exec-001/reports/SUCCESSES_AND_ERRORS/"
  }
}
```
