"""
agent.py - Single AI Agent Orchestrator.
Exclusively uses openai/gpt-oss-120b via Groq API.
Dispatches deterministic Python tools, enforces the 12-call loop limit,
and guarantees zero model fallback.
"""
import json
import time
from typing import Dict, List, Any, Optional

from config import GROQ_MODEL, MAX_TOOL_CALLS, GROQ_API_KEY
import database
from tools.maintenance import calculate_service_status
from tools.location import geocode_location, search_service_centers
from tools.booking import check_availability, book_appointment, cancel_appointment, get_appointment
from tools.notification import send_notification, format_confirmation_message

# System prompt giving strict instructions to GPT-OSS 120B
SYSTEM_PROMPT = """You are the Vehicle Service & Maintenance Management Agent.
You assist vehicle owners with maintenance status checks, finding service centers, and booking appointments.

CRITICAL RULES:
1. Never perform arithmetic or maintenance calculations yourself. Always call calculate_service_status.
2. Never invent vehicle data, service centers, availability, or booking references.
3. Finding a service center or checking availability DOES NOT mean an appointment is booked.
4. Only call book_appointment if the user explicitly requests booking and date/time are specified.
5. NEVER claim that an appointment is booked unless book_appointment returns status: SUCCESS.
6. When booking succeeds, use send_notification with the returned appointment_id.
7. Be polite, concise, and structured in your final response.
"""

# JSON Schemas for all 9 deterministic tools
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_vehicle_info",
            "description": "Retrieve vehicle information by user_id and optional vehicle name/model.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "The user ID (default 1)"},
                    "vehicle_name": {"type": "string", "description": "Optional make or model (e.g. 'Tata Nexon')"}
                },
                "required": ["user_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_service_history",
            "description": "Retrieve past service history records for a vehicle.",
            "parameters": {
                "type": "object",
                "properties": {
                    "vehicle_id": {"type": "integer", "description": "The vehicle ID"}
                },
                "required": ["vehicle_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_service_status",
            "description": "Calculate deterministic vehicle maintenance status (NOT_DUE, APPROACHING, DUE, OVERDUE).",
            "parameters": {
                "type": "object",
                "properties": {
                    "current_mileage": {"type": "integer", "description": "Current odometer reading in km"},
                    "last_service_mileage": {"type": "integer", "description": "Mileage at last service in km"},
                    "interval_km": {"type": "integer", "description": "Service interval in km (e.g. 5000)"},
                    "last_service_date": {"type": "string", "description": "Date of last service in YYYY-MM-DD format"},
                    "interval_months": {"type": "integer", "description": "Service interval in months (e.g. 6)"}
                },
                "required": ["current_mileage", "last_service_mileage", "interval_km", "last_service_date", "interval_months"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "geocode_location",
            "description": "Convert address, city, or neighborhood name into latitude and longitude coordinates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "address_or_city": {"type": "string", "description": "Address, area, or city name"}
                },
                "required": ["address_or_city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_service_centers",
            "description": "Search for nearby automotive service centers using coordinates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "latitude": {"type": "number", "description": "Latitude coordinate"},
                    "longitude": {"type": "number", "description": "Longitude coordinate"},
                    "radius_km": {"type": "integer", "description": "Search radius in km (default 10)"}
                },
                "required": ["latitude", "longitude"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": "Check available appointment time slots for a service center on a specific date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "center_id": {"type": "string", "description": "Stable service center ID (e.g. 'osm_101')"},
                    "date": {"type": "string", "description": "Appointment date in YYYY-MM-DD format"}
                },
                "required": ["center_id", "date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": "Book a service appointment. Requires explicit user request.",
            "parameters": {
                "type": "object",
                "properties": {
                    "vehicle_id": {"type": "integer", "description": "Vehicle ID"},
                    "center_id": {"type": "string", "description": "Stable service center ID"},
                    "date": {"type": "string", "description": "Appointment date in YYYY-MM-DD format"},
                    "time": {"type": "string", "description": "Time slot (e.g. '10:00 AM')"},
                    "service_type": {"type": "string", "description": "Type of service (default 'Periodic Maintenance Service')"}
                },
                "required": ["vehicle_id", "center_id", "date", "time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_appointment",
            "description": "Cancel an existing appointment by booking reference.",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_reference": {"type": "string", "description": "Booking reference code (e.g. 'BK10001')"}
                },
                "required": ["booking_reference"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_notification",
            "description": "Send and record appointment confirmation notification.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "User ID"},
                    "appointment_id": {"type": "integer", "description": "Confirmed appointment ID from booking"},
                    "message": {"type": "string", "description": "Notification message text"},
                    "channel": {"type": "string", "description": "Channel: 'EMAIL' or 'IN_APP' (default 'EMAIL')"}
                },
                "required": ["user_id", "appointment_id", "message"]
            }
        }
    }
]


def execute_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic dispatcher mapping tool call requests to Python functions."""
    try:
        if name == "get_vehicle_info":
            res = database.get_vehicle_info(
                user_id=arguments.get("user_id", 1),
                vehicle_name=arguments.get("vehicle_name")
            )
            return {"vehicle": res} if res else {"error": "Vehicle not found"}

        elif name == "get_service_history":
            res = database.get_service_history(vehicle_id=arguments.get("vehicle_id", 1))
            return {"service_history": res}

        elif name == "calculate_service_status":
            return calculate_service_status(
                current_mileage=arguments["current_mileage"],
                last_service_mileage=arguments["last_service_mileage"],
                interval_km=arguments["interval_km"],
                last_service_date=arguments["last_service_date"],
                interval_months=arguments["interval_months"],
                reference_date=arguments.get("reference_date")
            )

        elif name == "geocode_location":
            return geocode_location(address_or_city=arguments["address_or_city"])

        elif name == "search_service_centers":
            res = search_service_centers(
                latitude=arguments["latitude"],
                longitude=arguments["longitude"],
                radius_km=arguments.get("radius_km", 10)
            )
            return {"service_centers": res}

        elif name == "check_availability":
            return check_availability(
                center_id=arguments["center_id"],
                date=arguments["date"]
            )

        elif name == "book_appointment":
            return book_appointment(
                vehicle_id=arguments["vehicle_id"],
                center_id=arguments["center_id"],
                date=arguments["date"],
                time=arguments["time"],
                service_type=arguments.get("service_type", "Periodic Maintenance Service")
            )

        elif name == "cancel_appointment":
            return cancel_appointment(booking_reference=arguments["booking_reference"])

        elif name == "send_notification":
            return send_notification(
                user_id=arguments["user_id"],
                appointment_id=arguments.get("appointment_id"),
                message=arguments["message"],
                channel=arguments.get("channel", "EMAIL")
            )

        else:
            return {"error": f"Unknown tool: {name}"}

    except Exception as e:
        return {"error": f"Tool execution failed: {str(e)}"}


class VehicleMaintenanceAgent:
    """
    Single AI Agent orchestrating vehicle maintenance workflows.
    Uses ONLY openai/gpt-oss-120b through Groq.
    Capped strictly at MAX_TOOL_CALLS (12) iterations.
    """

    def __init__(self):
        self.model = GROQ_MODEL
        self.max_tool_calls = MAX_TOOL_CALLS
        self.api_key = GROQ_API_KEY
        self.client = None

        if self.api_key:
            try:
                from groq import Groq
                self.client = Groq(api_key=self.api_key)
            except Exception as e:
                print(f"Notice: Failed to initialize Groq client: {e}")
                self.client = None

    def is_configured(self) -> bool:
        """Check if Groq client is configured."""
        return self.client is not None

    def run(self, user_message: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Execute agent reasoning and tool calling loop.
        Loop limit capped strictly at 12 iterations.
        """
        if not self.is_configured():
            return (
                "Groq API is not yet configured. Please set your GROQ_API_KEY in .env "
                f"to enable live agent reasoning with `{self.model}`."
            )

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Append previous conversation history
        if history:
            for item in history:
                messages.append({"role": item["role"], "content": item["content"]})

        messages.append({"role": "user", "content": user_message})

        tool_calls_count = 0

        # Multi-turn tool execution loop
        while tool_calls_count < self.max_tool_calls:
            try:
                # Call Groq with exponential backoff on transient errors
                response = self._call_llm_with_retry(messages)
            except Exception as e:
                return f"Groq API Error ({self.model}): {str(e)}. No model fallback configured."

            choice = response.choices[0]
            message = choice.message

            # Check if LLM requested tool calls
            if message.tool_calls:
                messages.append(message)

                for tool_call in message.tool_calls:
                    tool_calls_count += 1
                    func_name = tool_call.function.name

                    try:
                        args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        args = {}

                    # Execute deterministic Python tool
                    result = execute_tool(func_name, args)

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": func_name,
                        "content": json.dumps(result)
                    })

                    # Break early if tool call ceiling reached inside batch
                    if tool_calls_count >= self.max_tool_calls:
                        break
            else:
                # LLM finished reasoning and returned final natural-language response
                return message.content or "Workflow completed."

        return (
            f"The workflow reached the maximum allowed limit of {self.max_tool_calls} tool calls. "
            "Please refine your request with specific vehicle or location details."
        )

    def _call_llm_with_retry(self, messages: List[Dict[str, Any]], max_retries: int = 3) -> Any:
        """
        Call Groq API with retries for transient connection errors.
        CRITICAL RULE: Never switches models. Only retries openai/gpt-oss-120b.
        """
        last_exception = None
        for attempt in range(max_retries):
            try:
                return self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=TOOL_SCHEMAS,
                    tool_choice="auto"
                )
            except Exception as e:
                last_exception = e
                # Wait with backoff before retrying the SAME model
                time.sleep(1.0 * (attempt + 1))

        raise last_exception


if __name__ == "__main__":
    agent = VehicleMaintenanceAgent()
    print("--- AI Agent Initialization Check ---")
    print(f"Model: {agent.model}")
    print(f"Configured: {agent.is_configured()}")
    print(f"Registered Tool Schemas: {len(TOOL_SCHEMAS)}")
    for t in TOOL_SCHEMAS:
        print(f"  - {t['function']['name']}")
