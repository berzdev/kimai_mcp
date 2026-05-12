"""Calendar and Meta tools for additional functionality."""

from typing import List, Dict
from mcp.types import Tool, TextContent
from ..client import KimaiClient
from ..models import MetaFieldForm


def calendar_tool() -> Tool:
    """Define the consolidated calendar tool."""
    return Tool(
        name="calendar",
        description="""Calendar view of absences and public holidays as calendar events (title, start, end, color).

WHEN TO USE THIS vs absence tool:
- Use calendar for visual/date-range overview (e.g., "show me who is off in December")
- Use absence tool for managing absences (create, approve, list with status filters)

COMMON TASKS:
- Team absence overview: type="absences", filters={begin:"2024-12-01", end:"2024-12-31"}
- Public holidays for a period: type="holidays", filters={begin:"2025-01-01", end:"2025-12-31"}
- One user's absences: type="absences", filters={user:ID, begin:"2025-01-01", end:"2025-06-30"}""",
        inputSchema={
            "type": "object",
            "required": ["type"],
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["absences", "holidays"],
                    "description": "absences: absence events for users. holidays: public/national holidays configured in Kimai."
                },
                "filters": {
                    "type": "object",
                    "description": "Date range and user filters. begin/end are strongly recommended to limit results.",
                    "properties": {
                        "user": {
                            "type": "integer",
                            "description": "Filter by user ID (absences only). Omit to get all users."
                        },
                        "begin": {
                            "type": "string",
                            "format": "date",
                            "description": "Start of date range (YYYY-MM-DD, e.g. 2025-01-01)"
                        },
                        "end": {
                            "type": "string",
                            "format": "date",
                            "description": "End of date range (YYYY-MM-DD, e.g. 2025-12-31)"
                        }
                    }
                }
            }
        }
    )


def meta_tool() -> Tool:
    """Define the consolidated meta fields tool."""
    return Tool(
        name="meta",
        description="""Update custom meta fields on existing entities (customer, project, activity, timesheet).

WHEN TO USE THIS vs entity tool:
- Use meta tool to update meta fields on an EXISTING entity (by ID)
- Use entity tool (action=create/update, data.metaFields=[...]) to set meta fields when creating or updating an entity in the same call

NOTE: Each meta field is sent as a separate API call. Multiple fields in data[] are processed one by one.

COMMON TASKS:
- Update project meta field: entity="project", entity_id=ID, action="update", data=[{name:"field_name", value:"field_value"}]
- Update multiple fields: data=[{name:"cost_center", value:"CC-123"}, {name:"client_ref", value:"REF-456"}]""",
        inputSchema={
            "type": "object",
            "required": ["entity", "entity_id", "action", "data"],
            "properties": {
                "entity": {
                    "type": "string",
                    "enum": ["customer", "project", "activity", "timesheet"],
                    "description": "The entity type whose meta fields to update"
                },
                "entity_id": {
                    "type": "integer",
                    "description": "The ID of the existing entity to update"
                },
                "action": {
                    "type": "string",
                    "enum": ["update"],
                    "description": "Action to perform. Only 'update' is supported — meta fields cannot be deleted via API."
                },
                "data": {
                    "type": "array",
                    "description": "List of meta fields to update. The meta field must already be defined in Kimai admin settings.",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "required": ["name", "value"],
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Meta field name as configured in Kimai (case-sensitive)"
                            },
                            "value": {
                                "type": "string",
                                "description": "New value for the meta field"
                            }
                        }
                    }
                }
            }
        }
    )


def user_current_tool() -> Tool:
    """Define the current user tool."""
    return Tool(
        name="user_current",
        description="""Get the currently authenticated user's profile.

Returns: username, ID, display name (alias), title, active status, language, timezone, and assigned roles (e.g. ROLE_ADMIN, ROLE_TEAMLEAD, ROLE_USER).

WHEN TO USE: Use this to find out your own user ID (needed for timesheet filters with user_scope=specific), confirm which account is connected, or check your roles/permissions.""",
        inputSchema={
            "type": "object",
            "properties": {}
        }
    )


async def handle_calendar(client: KimaiClient, **params) -> List[TextContent]:
    """Handle calendar operations."""
    calendar_type = params.get("type")
    filters = params.get("filters", {})
    
    try:
        if calendar_type == "absences":
            return await _handle_calendar_absences(client, filters)
        elif calendar_type == "holidays":
            return await _handle_calendar_holidays(client, filters)
        else:
            return [TextContent(
                type="text",
                text=f"Error: Unknown calendar type '{calendar_type}'. Valid types: absences, holidays"
            )]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_meta(client: KimaiClient, **params) -> List[TextContent]:
    """Handle meta field operations."""
    entity = params.get("entity")
    entity_id = params.get("entity_id")
    action = params.get("action")
    data = params.get("data", [])
    
    if not entity_id:
        return [TextContent(type="text", text="Error: 'entity_id' parameter is required")]
    
    if action != "update":
        return [TextContent(
            type="text",
            text=f"Error: Unknown action '{action}'. Currently only 'update' is supported"
        )]
    
    if not data:
        return [TextContent(type="text", text="Error: 'data' parameter is required for update action")]
    
    try:
        # Route to appropriate meta handler
        handlers = {
            "customer": client.update_customer_meta,
            "project": client.update_project_meta,
            "activity": client.update_activity_meta,
            "timesheet": client.update_timesheet_meta
        }
        
        handler = handlers.get(entity)
        if not handler:
            return [TextContent(
                type="text",
                text=f"Error: Unknown entity type '{entity}'. Valid types: customer, project, activity, timesheet"
            )]
        
        # Convert data to MetaFieldForm objects
        meta_fields = [MetaFieldForm(name=field["name"], value=field["value"]) for field in data]
        
        # Execute meta update
        await handler(entity_id, meta_fields)
        
        return [TextContent(
            type="text",
            text=f"Updated {len(meta_fields)} meta field(s) for {entity} ID {entity_id}"
        )]
        
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_user_current(client: KimaiClient, **params) -> List[TextContent]:
    """Handle current user request."""
    try:
        user = await client.get_current_user()
        
        result = f"Current User: {user.username} (ID: {user.id})\\n"
        result += f"Name: {user.alias or 'Not set'}\\n"
        result += f"Title: {user.title or 'Not set'}\\n"
        result += f"Status: {'Active' if user.enabled else 'Inactive'}\\n"
        
        if hasattr(user, 'language') and user.language:
            result += f"Language: {user.language}\\n"
        if hasattr(user, 'timezone') and user.timezone:
            result += f"Timezone: {user.timezone}\\n"
        if hasattr(user, 'roles') and user.roles:
            result += f"Roles: {', '.join(user.roles)}\\n"
        
        if hasattr(user, "supervisor") and user.supervisor:
            result += f"Supervisor: {user.supervisor.username}\\n"
        
        return [TextContent(type="text", text=result)]
        
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def _handle_calendar_absences(client: KimaiClient, filters: Dict) -> List[TextContent]:
    """Handle calendar absences request."""
    # Build filter object - API doesn't support year/month, only begin/end dates
    # Convert date formats to ISO with time like in absence manager
    filter_params = {}
    if filters.get("user"):
        filter_params["user"] = str(filters["user"])
    if filters.get("begin"):
        from datetime import datetime
        try:
            parsed_date = datetime.strptime(filters["begin"], "%Y-%m-%d")
            filter_params["begin"] = parsed_date.strftime("%Y-%m-%dT00:00:00")
        except ValueError:
            filter_params["begin"] = filters["begin"]  # Use as-is if not in expected format
    if filters.get("end"):
        from datetime import datetime
        try:
            parsed_date = datetime.strptime(filters["end"], "%Y-%m-%d")
            filter_params["end"] = parsed_date.strftime("%Y-%m-%dT23:59:59")
        except ValueError:
            filter_params["end"] = filters["end"]  # Use as-is if not in expected format
    
    from ..models import AbsenceFilter
    absence_filter = AbsenceFilter(**filter_params) if filter_params else None
    
    absences = await client.get_absences_calendar(absence_filter)
    
    if not absences:
        result = "No absences found for the specified calendar period"
    else:
        result = f"Found {len(absences)} absence event(s) in calendar:\\n\\n"
        
        for event in absences:
            result += f"Title: {event.title}\\n"
            result += f"  Start: {event.start}\\n"
            
            if event.end:
                result += f"  End: {event.end}\\n"
            
            if event.all_day:
                result += "  All Day: Yes\\n"
            
            if event.color:
                result += f"  Color: {event.color}\\n"
            
            result += "\\n"
    
    return [TextContent(type="text", text=result)]


async def _handle_calendar_holidays(client: KimaiClient, filters: Dict) -> List[TextContent]:
    """Handle calendar holidays request."""
    # Build filter object - API doesn't support year/month, only begin/end dates
    filter_params = {}
    if filters.get("begin"):
        filter_params["begin"] = filters["begin"]
    if filters.get("end"):
        filter_params["end"] = filters["end"]
    
    from ..models import PublicHolidayFilter
    holiday_filter = PublicHolidayFilter(**filter_params) if filter_params else None
    
    holidays = await client.get_public_holidays_calendar(holiday_filter)
    
    if not holidays:
        result = "No holidays found for the specified calendar period"
    else:
        result = f"Found {len(holidays)} holiday event(s) in calendar:\\n\\n"
        
        for event in holidays:
            result += f"Title: {event.title}\\n"
            result += f"  Start: {event.start}\\n"
            
            if event.end:
                result += f"  End: {event.end}\\n"
            
            if event.all_day:
                result += "  All Day: Yes\\n"
            
            if event.color:
                result += f"  Color: {event.color}\\n"
            
            result += "\\n"
    
    return [TextContent(type="text", text=result)]