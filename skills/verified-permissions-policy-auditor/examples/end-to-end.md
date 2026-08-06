# End-to-end usage scenario: verified-permissions-policy-auditor

A walkthrough showing the skill auditing a Verified Permissions policy store
that has both a bare permit (OVERPERMISSIVE) and validation mode OFF
(CONFIG_GAP), demonstrating verdict aggregation, the bare-permit concept, and
the scoped-remediation workflow.

## Input (user prompt)

> Review this Verified Permissions policy store before we go to production.
> The app is a photo-sharing platform with user-uploaded content.

Policy store ID: ps-prod-photoapp
Validation settings: { mode: OFF }

Schema:

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

Policy 1:

```cedar
permit (principal, action, resource);
```

Policy 2:

```cedar
forbid (
  principal: PhotoApp::User,
  action: PhotoApp::Action::"DeletePhoto",
  resource: PhotoApp::Photo
)
unless { principal.role == "admin" };
```

## Skill output

```text
POLICY: pol-bare-permit (Policy 1)
VERDICT: OVERPERMISSIVE
REASON: Policy is a bare permit(principal, action, resource) with no scope
constraints and no conditions — authorizes every request (Rule 2a). The
forbid clause in Policy 2 blocks non-admin deletion but does NOT compensate
for the bare permit on all other actions and resources.
FINDINGS:
  - [OVERPERMISSIVE] Bare permit matches all principals, actions, and
    resources with no conditions (Rule 2a)
  - [CONFIG_GAP] validationSettings.mode is OFF — schema validation disabled,
    allowing non-existent entities to persist silently (Config 3a)
REMEDIATION:
  1. OVERPERMISSIVE — Replace the bare permit with scoped policies:
     permit(principal: PhotoApp::User,
       action: PhotoApp::Action::"ViewPhoto",
       resource: PhotoApp::Photo)
     when { principal.userId == resource.owner };
  2. OVERPERMISSIVE — Add scoped permits for UploadPhoto and DeletePhoto
     with appropriate conditions (e.g., upload requires active account,
     delete requires admin role).
  3. CONFIG_GAP — Enable validation:
     aws verifiedpermissions update-policy-store
       --policy-store-id ps-prod-photoapp
       --validation-settings mode=STRICT
  4. Back up all policies before changes (policies are not versioned):
     aws verifiedpermissions list-policies
       --policy-store-id ps-prod-photoapp --output json > /tmp/backup.json
```

## What the skill caught that a generic assistant misses

1. **The bare permit blast radius.** A generic assistant says "this policy is
   too permissive." The skill explains that `permit(principal, action,
   resource)` is the Cedar equivalent of IAM `Principal:"*", Action:"*",
   Resource:"*"` — it matches EVERY authorization request. One policy, total
   access across the entire policy store.

2. **The forbid does NOT compensate for the bare permit.** A naive auditor
   might think "there's a forbid on DeletePhoto, so deletes are protected."
   The skill recognizes that the bare permit still covers ViewPhoto,
   UploadPhoto, and any future action added to the schema. The forbid is a
   deny-list — it has an unbounded gap.

3. **Validation mode OFF compounds the risk.** The skill flags the OFF mode
   as a separate CONFIG_GAP finding. Even after fixing the bare permit,
   future policies will not be schema-validated until validation is enabled.
   This is the "silent divergence" pattern unique to AVP.

4. **Non-versioned policy warning.** The skill reminds the operator that AVP
   policies are not versioned — there is no automatic rollback. The remediation
   includes backing up all policies before any modification.

## Slash-command invocation

```
/aws:audit-verified-permissions-policy
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit this Verified Permissions policy store before production"
```

The orchestrator emits
`[Phase: Audit | Skills routed: verified-permissions-policy-auditor]` and hands
off to this skill for the VERDICT.

## Live-account follow-up (optional, requires AWS CLI)

After remediating the policies, validate the store posture:

```bash
# Verify validation mode is now STRICT
aws verifiedpermissions get-policy-store \
  --policy-store-id ps-prod-photoapp --profile default

# Confirm the bare permit was replaced
aws verifiedpermissions list-policies \
  --policy-store-id ps-prod-photoapp --profile default \
  | jq '.policies[] | .definition.static'

# Test authorization with a scoped request
aws verifiedpermissions is-authorized \
  --policy-store-id ps-prod-photoapp \
  --principal '{"entityType":"PhotoApp::User","entityId":"alice"}' \
  --action '{"actionType":"PhotoApp::Action","actionId":"ViewPhoto"}' \
  --resource '{"entityType":"PhotoApp::Photo","entityId":"vacation-snap"}' \
  --profile default
```

Then monitor CloudTrail for `verifiedpermissions:IsAuthorized` events to
confirm the remediated policies produce the expected decisions.
