# Eval prompt: schema-mismatch-action-not-declared

Audit the following Amazon Verified Permissions policy store configuration
for security exposure. Emit the standard VERDICT block (POLICY, VERDICT,
REASON, FINDINGS, REMEDIATION).

Policy store ID: ps-schema-mismatch-action-not-declared
Policy store description: Policy references action removed from schema
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
      "UploadPhoto": { "appliesTo": { "principalTypes": ["User"], "resourceTypes": ["Photo"] } }
    }
  }
}
```

Note: The schema declares only ViewPhoto and UploadPhoto. DeletePhoto was
removed in a prior schema update but the policy referencing it still exists.

Policy ID: pol-schema-mismatch-action-not-declared
Policy type: STATIC
Policy text:

```cedar
permit (
  principal: PhotoApp::User,
  action: PhotoApp::Action::"DeletePhoto",
  resource: PhotoApp::Photo
)
when { principal.role == "admin" };
```
