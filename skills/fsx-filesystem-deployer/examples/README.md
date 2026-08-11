# Example: Deploy Amazon FSx File System

## Scenario
Deploy a Multi-AZ FSx for Windows File Server with deduplication and DNS alias for production use.

## Steps

### 1. Verify AD Prerequisites
```bash
aws ds describe-directories --query Directories[0].DirectoryId
# Must return a valid directory ID for FSx for Windows
```

### 2. Create File System (Multi-AZ)
```bash
aws fsx create-file-system \
  --file-system-type WINDOWS \
  --storage-capacity 2048 \
  --storage-type SSD \
  --windows-configuration DeploymentType=MULTI_AZ_1,\
ThroughputCapacity=256,\
ActiveDirectoryId=d-1234567890,\
PreferredSubnetId=subnet-aaa11122,\
SubnetIds=subnet-aaa11122,subnet-bbb22233,\
AutomaticBackupRetentionDays=7,\
CopyTagsToBackups=true \
  --security-group-ids sg-fsx-prod \
  --kms-key-id alias/aws/fsx
```

### 3. Configure DNS Alias (for failover)
```bash
aws fsx associate-file-system-aliases \
  --file-system-id fs-1234567890 \
  --aliases fileshare.prod.example.com
```

### 4. Enable Data Deduplication
```bash
# Connect via Remote Desktop and configure:
# Server Manager > Tools > Data Deduplication
# Set dedup on volume D: with GeneralPurpose policy
```

## Key Decisions
- Multi-AZ for 99.99% availability and automatic failover
- 256 MB/s throughput for 500+ concurrent users
- DNS alias enables seamless client reconnection on failover
- Dedup expected to save ~60% for general-purpose file shares
- 7-day backup retention with CopyTagsToBackups for tagging compliance
