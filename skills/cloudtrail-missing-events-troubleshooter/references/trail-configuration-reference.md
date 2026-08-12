# Trail Configuration Reference

## Management Events
- ReadOnly=True: only read operations
- ReadOnly=False: only write operations
- ReadOnly=All: both (default)

## Data Events
- Must explicitly configure AdvancedEventSelectors
- S3: s3:GetObject, s3:PutObject (not management events)
- Lambda: Invoke API
- DynamoDB: CRUD

## Organization Trails
- Created in management account
- Member accounts CANNOT disable org trail
- Member account trail is SHADOWED by org trail
- Events may appear duplicated

## S3 Bucket Policy
Must include:
- cloudtrail.amazonaws.com:PutObject
- cloudtrail.amazonaws.com:GetBucketAcl
