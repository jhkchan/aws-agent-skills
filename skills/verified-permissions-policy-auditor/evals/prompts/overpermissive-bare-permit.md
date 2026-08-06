# Eval prompt: overpermissive-bare-permit

Audit the following Amazon Verified Permissions policy store configuration
for security exposure. Emit the standard VERDICT block (POLICY, VERDICT,
REASON, FINDINGS, REMEDIATION).

Policy store ID: ps-overpermissive-bare-permit
Policy store description: Bare permit authorizes all requests
Validation settings: { mode: STRICT }

Schema (JSON):

```json
{
  "PhotoApp": {
    "entityTypes": {
      "User": {
        "shape": {
          "type": "Record",
          "attributes": {
            "userId": { "type": "String" },
            "role": { "type": "String" },
            "age": { "type": "Long" },
            "accountStatus": { "type": "String" }
          }
        },
        "memberOfTypes": ["UserGroup"]
      },
      "UserGroup": {
        "shape": { "type": "Record", "attributes": { "name": { "type": "String" } } }
      },
      "Photo": {
        "shape": {
          "type": "Record",
          "attributes": {
            "photoId": { "type": "String" },
            "owner": { "type": "String" },
            "isPrivate": { "type": "Boolean" }
          }
        }
      }
    },
    "actions": {
      "ViewPhoto": { "appliesTo": { "principalTypes": ["User"], "resourceTypes": ["Photo"] } },
      "UploadPhoto": { "appliesTo": { "principalTypes": ["User"], "resourceTypes": ["Photo"] } },
      "DeletePhoto": { "appliesTo": { "principalTypes": ["User"], "resourceTypes": ["Photo"] } }
    }
  }
}
```

Policy ID: pol-overpermissive-bare-permit
Policy type: STATIC
Policy text:

```cedar
permit (principal, action, resource);
```
