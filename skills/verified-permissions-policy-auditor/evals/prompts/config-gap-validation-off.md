# Eval prompt: config-gap-validation-off

Audit the following Amazon Verified Permissions policy store configuration
for security exposure. Emit the standard VERDICT block (POLICY, VERDICT,
REASON, FINDINGS, REMEDIATION).

Policy store ID: ps-config-gap-validation-off
Policy store description: Validation disabled on policy store
Validation settings: { mode: OFF }

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

Policy ID: pol-config-gap-validation-off
Policy type: STATIC
Policy text:

```cedar
permit (
  principal: PhotoApp::User,
  action: PhotoApp::Action::"ViewPhoto",
  resource: PhotoApp::Photo
)
when { principal.userId == resource.owner };
```
