"""
agent.py - AI Agent Orchestrator using Groq (openai/gpt-oss-120b).
Runs multi-turn reasoning with deterministic Python tools (capped at 12 calls).
"""
import json
import re
import time
from typing import Dict, List, Any, Optional
from config import GROQ_MODEL, MAX_TOOL_CALLS, GROQ_API_KEY
import database
from tools.maintenance import calculate_service_status
from tools.location import geocode_location, search_service_centers, detect_current_location
from tools.booking import check_availability, book_appointment, cancel_appointment, get_appointment
from tools.notification import send_notification, format_confirmation_message

# System Prompt with clear instructions for the AI model
SYSTEM_PROMPT = """You are the Vehicle Maintenance AI Assistant for Rahul in Bengaluru (email: jaxiver377@gmail.com).
Follow these rules strictly:
1. SERVICE UPDATES & ODOMETER:
   - When user provides a new odometer reading or says they drove X km, call `update_vehicle_mileage` to update current mileage.
   - When user mentions completing a service or updating service date:
     Call `update_service_after_completion` or `update_vehicle_service_details`. If next service interval is not mentioned, default to 5000 km.
2. LOCATION & SERVICE CENTERS:
   - If user asks for nearby/nearest workshops without a specific city, call `geocode_location` with "current location".
   - Always filter by the active vehicle's brand (e.g. brand="Tata" for Tata Nexon). Show ONLY authorized centers for that brand.
3. BOOKING & SERVICE COST:
   - Only book an appointment if the user explicitly specifies date and time.
   - After successful booking, call `send_notification`.
   - Ask the user: "Once your service is completed, please let me know the final invoice cost so I can update your maintenance records."
   - When user states the service cost (e.g. "service cost was 3500", "I paid 4200", "cost 2500"), call `update_service_cost` to save it in the database.
4. Always use tools for math, calculations, and data lookups. Never make up vehicle data or booking numbers.
"""

# Tool schemas available to the AI model
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_vehicle_info",
            "description": "Get vehicle details by user_id and optional name or label.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "User ID (default 1)"},
                    "vehicle_name": {"type": "string", "description": "Vehicle name or label"}
                },
                "required": ["user_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_service_history",
            "description": "Get past service history for a vehicle.",
            "parameters": {
                "type": "object",
                "properties": {"vehicle_id": {"type": "integer"}},
                "required": ["vehicle_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_service_status",
            "description": "Calculate service due status (OVERDUE, DUE, APPROACHING, NOT_DUE).",
            "parameters": {
                "type": "object",
                "properties": {
                    "current_mileage": {"type": "integer"},
                    "last_service_mileage": {"type": "integer"},
                    "interval_km": {"type": "integer"},
                    "last_service_date": {"type": "string"},
                    "interval_months": {"type": "integer"},
                    "reference_date": {"type": "string"}
                },
                "required": ["current_mileage", "last_service_mileage", "interval_km", "last_service_date", "interval_months"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "geocode_location",
            "description": "Convert address to GPS coordinates or detect current location.",
            "parameters": {
                "type": "object",
                "properties": {"address_or_city": {"type": "string"}},
                "required": ["address_or_city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_service_centers",
            "description": "Find nearby authorized service centers by GPS coordinates and brand.",
            "parameters": {
                "type": "object",
                "properties": {
                    "latitude": {"type": "number"},
                    "longitude": {"type": "number"},
                    "radius_km": {"type": "integer"},
                    "brand": {"type": "string"}
                },
                "required": ["latitude", "longitude"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": "Check available booking slots for a service center and date.",
            "parameters": {
                "type": "object",
                "properties": {"center_id": {"type": "string"}, "date": {"type": "string"}},
                "required": ["center_id", "date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": "Book a service appointment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "vehicle_id": {"type": "integer"},
                    "center_id": {"type": "string"},
                    "date": {"type": "string"},
                    "time": {"type": "string"},
                    "service_type": {"type": "string"}
                },
                "required": ["vehicle_id", "center_id", "date", "time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_appointment",
            "description": "Cancel a booking by booking reference.",
            "parameters": {
                "type": "object",
                "properties": {"booking_reference": {"type": "string"}},
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
                    "user_id": {"type": "integer"},
                    "appointment_id": {"type": "integer"},
                    "message": {"type": "string"},
                    "channel": {"type": "string"}
                },
                "required": ["user_id", "appointment_id", "message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_vehicle",
            "description": "Add a new vehicle to the user's garage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer"},
                    "make": {"type": "string"},
                    "model": {"type": "string"},
                    "registration_number": {"type": "string"},
                    "current_mileage": {"type": "integer"},
                    "label": {"type": "string"}
                },
                "required": ["make", "model"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_vehicle",
            "description": "Remove a vehicle from garage.",
            "parameters": {
                "type": "object",
                "properties": {"user_id": {"type": "integer"}, "vehicle_identifier": {"type": "string"}},
                "required": ["vehicle_identifier"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_vehicle_mileage",
            "description": "Update current odometer mileage for a vehicle.",
            "parameters": {
                "type": "object",
                "properties": {
                    "vehicle_id": {"type": "integer"},
                    "new_mileage": {"type": "integer"}
                },
                "required": ["vehicle_id", "new_mileage"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_vehicle_service_details",
            "description": "Update last service date and last service mileage for a vehicle.",
            "parameters": {
                "type": "object",
                "properties": {
                    "vehicle_id": {"type": "integer"},
                    "last_service_date": {"type": "string"},
                    "last_service_mileage": {"type": "integer"},
                    "current_mileage": {"type": "integer"}
                },
                "required": ["vehicle_id", "last_service_date", "last_service_mileage"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_service_after_completion",
            "description": "Update vehicle mileage, schedule, and history after completing service.",
            "parameters": {
                "type": "object",
                "properties": {
                    "vehicle_id": {"type": "integer"},
                    "service_date": {"type": "string"},
                    "next_service_interval_km": {"type": "integer"},
                    "service_mileage": {"type": "integer"},
                    "service_type": {"type": "string"}
                },
                "required": ["vehicle_id", "service_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_service_cost",
            "description": "Record or update the expense/cost of a completed service in the database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "vehicle_id": {"type": "integer", "description": "Vehicle ID"},
                    "cost": {"type": "number", "description": "Total service bill/cost in INR"},
                    "service_history_id": {"type": "integer", "description": "Optional specific service history ID"}
                },
                "required": ["vehicle_id", "cost"]
            }
        }
    }
]


def execute_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute Python tools requested by the AI agent."""
    try:
        if name == "get_vehicle_info":
            v = database.get_vehicle_info(args.get("user_id", 1), args.get("vehicle_name"))
            all_v = database.get_user_vehicles(args.get("user_id", 1))
            return {"vehicle": v, "user_vehicles": [{"id": x["id"], "name": f"{x['make']} {x['model']}"} for x in all_v]}
        elif name == "get_service_history":
            return {"service_history": database.get_service_history(int(args.get("vehicle_id", 1)))}
        elif name == "calculate_service_status":
            return calculate_service_status(int(args["current_mileage"]), int(args["last_service_mileage"]), int(args["interval_km"]), str(args["last_service_date"]), int(args["interval_months"]), args.get("reference_date"))
        elif name == "geocode_location":
            return geocode_location(str(args.get("address_or_city", "current location")))
        elif name == "search_service_centers":
            return {"service_centers": search_service_centers(float(args["latitude"]), float(args["longitude"]), int(args.get("radius_km", 10)), args.get("brand"))}
        elif name == "check_availability":
            return check_availability(str(args["center_id"]), str(args["date"]))
        elif name == "book_appointment":
            return book_appointment(int(args["vehicle_id"]), str(args["center_id"]), str(args["date"]), str(args["time"]), str(args.get("service_type", "Periodic Maintenance Service")))
        elif name == "cancel_appointment":
            return cancel_appointment(str(args["booking_reference"]))
        elif name == "send_notification":
            appt_id = int(args["appointment_id"]) if args.get("appointment_id") else None
            return send_notification(int(args.get("user_id", 1)), appt_id, str(args["message"]), str(args.get("channel", "EMAIL")))
        elif name == "add_vehicle":
            return database.add_vehicle(args.get("user_id", 1), args.get("make", "Tata"), args.get("model", "Harrier"), args.get("registration_number"), args.get("current_mileage", 0), label=args.get("label"))
        elif name == "delete_vehicle":
            return database.delete_vehicle(args.get("vehicle_identifier"), args.get("user_id", 1))
        elif name == "update_vehicle_mileage":
            return database.update_vehicle_mileage(int(args["vehicle_id"]), int(args["new_mileage"]))
        elif name == "update_vehicle_service_details":
            return database.update_vehicle_service_details(int(args["vehicle_id"]), str(args["last_service_date"]), int(args["last_service_mileage"]), args.get("current_mileage"))
        elif name == "update_service_after_completion":
            interval = int(args["next_service_interval_km"]) if args.get("next_service_interval_km") else None
            return database.update_service_after_completion(int(args["vehicle_id"]), str(args["service_date"]), interval, args.get("service_mileage"), args.get("service_type", "Periodic Maintenance Service"))
        elif name == "update_service_cost":
            return database.update_service_cost(int(args["vehicle_id"]), float(args["cost"]), args.get("service_history_id"))
        return {"error": f"Unknown tool: {name}"}
    except Exception as e:
        return {"error": f"Tool execution error: {e}"}


def sanitize_api_error(err: Any) -> str:
    """Format API error messages cleanly without exposing sensitive info."""
    err_str = str(err)
    if "429" in err_str or "rate limit" in err_str.lower():
        return "AI rate limit reached. Please wait a moment and try again."
    if "401" in err_str or "invalid_api_key" in err_str.lower():
        return "Authentication error: Invalid GROQ_API_KEY."
    return re.sub(r"(gsk_[a-zA-Z0-9]+|sk-[a-zA-Z0-9]+)", "[REDACTED]", err_str)


class VehicleMaintenanceAgent:
    """Agent that handles vehicle maintenance reasoning using Groq API."""

    def __init__(self):
        self.model = GROQ_MODEL
        self.max_tool_calls = MAX_TOOL_CALLS
        self.client = None
        if GROQ_API_KEY:
            try:
                from groq import Groq
                self.client = Groq(api_key=GROQ_API_KEY)
            except Exception as e:
                print(f"Notice: Groq init error: {e}")

    def is_configured(self) -> bool:
        """Check if Groq API is ready."""
        return self.client is not None

    def run(self, user_message: str, history: Optional[List[Dict[str, str]]] = None, selected_vehicle_id: Optional[int] = None) -> str:
        """Execute reasoning loop capped at 12 tool calls."""
        if not self.is_configured():
            return f"Please set GROQ_API_KEY in .env to enable the AI assistant with `{self.model}`."

        # Prepare system prompt with active vehicle context
        prompt = SYSTEM_PROMPT
        if selected_vehicle_id:
            v = database.get_vehicle_by_id(selected_vehicle_id)
            if v:
                prompt += f"\nACTIVE VEHICLE IN UI: ID {v['id']}, {v['make']} {v['model']} ({v['registration_number']}), Odometer: {v['current_mileage']} km."

        messages = [{"role": "system", "content": prompt}]
        if history:
            for item in history:
                messages.append({"role": item["role"], "content": item["content"]})
        messages.append({"role": "user", "content": user_message})

        tool_calls_count = 0
        while tool_calls_count < self.max_tool_calls:
            try:
                response = self.client.chat.completions.create(model=self.model, messages=messages, tools=TOOL_SCHEMAS, tool_choice="auto")
            except Exception as e:
                return f"Groq API Error ({self.model}): {sanitize_api_error(e)}. No model fallback configured."

            choice = response.choices[0]
            msg = choice.message

            # If tool calls were requested, execute them
            if msg.tool_calls:
                messages.append(msg)
                for tc in msg.tool_calls:
                    tool_calls_count += 1
                    try:
                        args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        args = {}
                    result = execute_tool(tc.function.name, args)
                    messages.append({"role": "tool", "tool_call_id": tc.id, "name": tc.function.name, "content": json.dumps(result)})
                    if tool_calls_count >= self.max_tool_calls:
                        break
            else:
                return msg.content or "Done."

        return f"The workflow reached the maximum allowed limit of {self.max_tool_calls} tool calls. Please refine your request with specific vehicle or location details."


if __name__ == "__main__":
    agent = VehicleMaintenanceAgent()
    print(f"Agent ready ({agent.model}): {agent.is_configured()}")
