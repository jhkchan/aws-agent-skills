---
name: deploy-fsx-filesystem
description: Deploy Amazon FSx file systems (Windows, Lustre, ONTAP, OpenZFS)
---

# Deploy Amazon FSx File System

Routes to the `fsx-filesystem-deployer` skill.

## Usage
```
/deploy-fsx-filesystem <description of what to deploy>
```

## Examples
- `/deploy-fsx-filesystem Multi-AZ Windows file server with AD, 2TB SSD, dedup`
- `/deploy-fsx-filesystem Lustre PERSISTENT_1 with S3 export for ML training`
- `/deploy-fsx-filesystem ONTAP Multi-AZ with volume tiering`

## Triggers
- amazon fsx
- fsx for windows
- fsx for lustre
- fsx for ontap
- fsx for openzfs
- s3 export
- data deduplication
- svm
- throughput capacity
- multi-az deployment
