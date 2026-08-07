# Eval prompt: aurora-backtrack-in-window

Plan the following Aurora MySQL backtrack operation and emit the standard
VERDICT block.

Operation: backtrack
Source cluster: aurora-prod-cluster
Backtrack to: 2026-08-07T09:00:00Z (about 2 hours ago)
Reason: bad bulk UPDATE that needs to be reversed

```json
{
  "SourceCluster": {
    "DBClusterIdentifier": "aurora-prod-cluster",
    "DBClusterStatus": "available",
    "Engine": "aurora-mysql",
    "EngineVersion": "8.0.mysql_aurora.3.05.2",
    "BacktrackWindow": 86400,
    "AllocatedStorage": 2000,
    "StorageEncrypted": true,
    "GlobalClusterMember": false,
    "ActivityStreamStatus": "stopped"
  },
  "ExistingBacktracks": []
}
```
