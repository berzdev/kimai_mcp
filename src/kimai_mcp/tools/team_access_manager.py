"""Consolidated Team Access Manager tool for all team operations."""

from typing import List, Optional
from mcp.types import Tool, TextContent
from ..client import KimaiClient


def team_access_tool() -> Tool:
    """Define the consolidated team access management tool."""
    return Tool(
        name="team_access",
        description="""Manage team membership and grant/revoke team access to customers, projects, and activities.

Two distinct use cases:
1. MEMBER MANAGEMENT — who is in the team (requires: team_id, action, user_id)
2. ACCESS CONTROL — which entities the team can see (requires: team_id, action, target, target_id)

COMMON TASKS:
- Add user to team:         action="add_member",    team_id=ID, user_id=USER_ID
- Remove user from team:    action="remove_member", team_id=ID, user_id=USER_ID
- Grant project access:     action="grant",  team_id=ID, target="project",  target_id=PROJECT_ID
- Revoke customer access:   action="revoke", team_id=ID, target="customer", target_id=CUSTOMER_ID

NOTE: To list teams or create/delete a team, use the entity tool with type="team".""",
        inputSchema={
            "type": "object",
            "required": ["team_id", "action"],
            "properties": {
                "team_id": {
                    "type": "integer",
                    "description": "The team ID to operate on (use entity tool with type=team, action=list to find IDs)"
                },
                "action": {
                    "type": "string",
                    "enum": ["add_member", "remove_member", "grant", "revoke"],
                    "description": """Action to perform:
- add_member: Add a user to the team. Requires: user_id
- remove_member: Remove a user from the team. Requires: user_id
- grant: Grant the team access to an entity. Requires: target, target_id
- revoke: Revoke the team's access to an entity. Requires: target, target_id"""
                },
                "user_id": {
                    "type": "integer",
                    "description": "User ID — required for add_member and remove_member actions"
                },
                "target": {
                    "type": "string",
                    "enum": ["customer", "project", "activity"],
                    "description": "Entity type to grant/revoke access to — required for grant and revoke actions"
                },
                "target_id": {
                    "type": "integer",
                    "description": "ID of the customer, project, or activity — required for grant and revoke actions"
                }
            }
        }
    )


async def handle_team_access(client: KimaiClient, **params) -> List[TextContent]:
    """Handle consolidated team access operations."""
    team_id = params.get("team_id")
    action = params.get("action")
    target = params.get("target")
    user_id = params.get("user_id")
    target_id = params.get("target_id")
    
    if not team_id:
        return [TextContent(type="text", text="Error: 'team_id' parameter is required")]
    
    try:
        if action == "add_member":
            return await _handle_add_member(client, team_id, user_id)
        elif action == "remove_member":
            return await _handle_remove_member(client, team_id, user_id)
        elif action == "grant":
            return await _handle_grant_access(client, team_id, target, target_id)
        elif action == "revoke":
            return await _handle_revoke_access(client, team_id, target, target_id)
        else:
            return [TextContent(
                type="text",
                text=f"Error: Unknown action '{action}'. Valid actions: add_member, remove_member, grant, revoke"
            )]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def _handle_add_member(client: KimaiClient, team_id: int, user_id: Optional[int]) -> List[TextContent]:
    """Handle adding a member to a team."""
    if not user_id:
        return [TextContent(type="text", text="Error: 'user_id' parameter is required for add_member action")]
    
    await client.add_team_member(team_id, user_id)
    
    return [TextContent(
        type="text",
        text=f"Added user ID {user_id} as member to team ID {team_id}"
    )]


async def _handle_remove_member(client: KimaiClient, team_id: int, user_id: Optional[int]) -> List[TextContent]:
    """Handle removing a member from a team."""
    if not user_id:
        return [TextContent(type="text", text="Error: 'user_id' parameter is required for remove_member action")]
    
    await client.remove_team_member(team_id, user_id)
    
    return [TextContent(
        type="text",
        text=f"Removed user ID {user_id} from team ID {team_id}"
    )]


async def _handle_grant_access(client: KimaiClient, team_id: int, target: Optional[str], target_id: Optional[int]) -> List[TextContent]:
    """Handle granting access to a team."""
    if not target:
        return [TextContent(type="text", text="Error: 'target' parameter is required for grant action")]
    if not target_id:
        return [TextContent(type="text", text="Error: 'target_id' parameter is required for grant action")]
    
    if target == "customer":
        await client.grant_team_customer_access(team_id, target_id)
        entity_type = "customer"
    elif target == "project":
        await client.grant_team_project_access(team_id, target_id)
        entity_type = "project"
    elif target == "activity":
        await client.grant_team_activity_access(team_id, target_id)
        entity_type = "activity"
    else:
        return [TextContent(
            type="text",
            text=f"Error: Unknown target type '{target}'. Valid types: customer, project, activity"
        )]
    
    return [TextContent(
        type="text",
        text=f"Granted team ID {team_id} access to {entity_type} ID {target_id}"
    )]


async def _handle_revoke_access(client: KimaiClient, team_id: int, target: Optional[str], target_id: Optional[int]) -> List[TextContent]:
    """Handle revoking access from a team."""
    if not target:
        return [TextContent(type="text", text="Error: 'target' parameter is required for revoke action")]
    if not target_id:
        return [TextContent(type="text", text="Error: 'target_id' parameter is required for revoke action")]
    
    if target == "customer":
        await client.revoke_team_customer_access(team_id, target_id)
        entity_type = "customer"
    elif target == "project":
        await client.revoke_team_project_access(team_id, target_id)
        entity_type = "project"
    elif target == "activity":
        await client.revoke_team_activity_access(team_id, target_id)
        entity_type = "activity"
    else:
        return [TextContent(
            type="text",
            text=f"Error: Unknown target type '{target}'. Valid types: customer, project, activity"
        )]
    
    return [TextContent(
        type="text",
        text=f"Revoked team ID {team_id} access to {entity_type} ID {target_id}"
    )]