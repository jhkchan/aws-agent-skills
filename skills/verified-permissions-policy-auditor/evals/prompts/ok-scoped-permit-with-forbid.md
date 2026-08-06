# Eval prompt: ok-scoped-permit-with-forbid

Audit the following Amazon Verified Permissions policy store configuration
for security exposure. Emit the standard VERDICT block (POLICY, VERDICT,
REASON, FINDINGS, REMEDIATION).

Policy store ID: ps-ok-scoped-permit-with-forbid
Policy store description: Properly scoped Cedar policies with validation ON
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

Policy ID: pol-ok-scoped-permit-with-forbid
Policy type: STATIC
Policy text:

```cedar
permit (
  principal: PhotoApp::User,
  action: PhotoApp::Action::"ViewPhoto",
  resource: PhotoApp::Photo
)
when { principal.userId == resource.owner }
when { principal.accountStatus == "active" };

forbid (
  principal: PhotoApp::User,
  action: PhotoApp::Action::"DeletePhoto",
  resource: PhotoApp::Photo
)
unless { principal.role == "admin" };
```
