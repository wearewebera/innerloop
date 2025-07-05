"""Time awareness and temporal tools for InnerLoop agents."""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from tools.base_tool import BaseTool, ToolParameter
import structlog
import calendar

logger = structlog.get_logger()


class TimeAwarenessTool(BaseTool):
    """Tool for time awareness and temporal reasoning."""
    
    def __init__(self, agent_id: str = None):
        super().__init__(agent_id)
        
    @property
    def name(self) -> str:
        return "time_awareness"
    
    @property
    def description(self) -> str:
        return (
            "Get current time, date, or perform temporal calculations. "
            "Can provide time context, calculate durations, or schedule reminders."
        )
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="query_type",
                type="string",
                description="Type of time query: 'current', 'duration', 'relative', 'schedule'",
                required=True
            ),
            ToolParameter(
                name="format",
                type="string",
                description="Output format: 'full', 'date', 'time', 'timestamp', 'human'",
                required=False,
                default="human"
            ),
            ToolParameter(
                name="reference_time",
                type="string",
                description="Reference time for calculations (ISO format)",
                required=False,
                default=None
            ),
            ToolParameter(
                name="duration",
                type="string",
                description="Duration for calculations (e.g., '2 hours', '3 days')",
                required=False,
                default=None
            )
        ]
    
    async def execute(self, query_type: str, format: str = "human",
                     reference_time: Optional[str] = None, 
                     duration: Optional[str] = None) -> Dict[str, Any]:
        """Execute time-related queries."""
        try:
            if query_type == "current":
                return await self._get_current_time(format)
            elif query_type == "duration":
                return await self._calculate_duration(reference_time, duration)
            elif query_type == "relative":
                return await self._get_relative_time(reference_time, format)
            elif query_type == "schedule":
                return await self._schedule_info(duration)
            else:
                return {
                    "error": f"Unknown query type: {query_type}",
                    "valid_types": ["current", "duration", "relative", "schedule"]
                }
                
        except Exception as e:
            self.logger.error("Time query failed", error=str(e))
            return {
                "error": f"Time query failed: {str(e)}"
            }
    
    async def _get_current_time(self, format: str) -> Dict[str, Any]:
        """Get current time in requested format."""
        now = datetime.now()
        
        formatted_time = {
            "full": now.isoformat(),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "timestamp": int(now.timestamp()),
            "human": now.strftime("%B %d, %Y at %I:%M %p")
        }
        
        result = {
            "current_time": formatted_time.get(format, formatted_time["human"]),
            "timezone": "local",
            "day_of_week": calendar.day_name[now.weekday()],
            "is_weekend": now.weekday() >= 5
        }
        
        # Add contextual information
        hour = now.hour
        if hour < 6:
            result["time_of_day"] = "night"
        elif hour < 12:
            result["time_of_day"] = "morning"
        elif hour < 18:
            result["time_of_day"] = "afternoon"
        else:
            result["time_of_day"] = "evening"
        
        return result
    
    async def _calculate_duration(self, reference_time: Optional[str], duration: Optional[str]) -> Dict[str, Any]:
        """Calculate duration between times or parse duration strings."""
        if reference_time:
            try:
                ref_time = datetime.fromisoformat(reference_time)
                now = datetime.now()
                delta = now - ref_time
                
                # Convert to human-readable
                days = delta.days
                hours, remainder = divmod(delta.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                
                human_duration = ""
                if days > 0:
                    human_duration += f"{days} day{'s' if days != 1 else ''}"
                if hours > 0:
                    if human_duration:
                        human_duration += ", "
                    human_duration += f"{hours} hour{'s' if hours != 1 else ''}"
                if minutes > 0 and days == 0:
                    if human_duration:
                        human_duration += ", "
                    human_duration += f"{minutes} minute{'s' if minutes != 1 else ''}"
                
                if not human_duration:
                    human_duration = "less than a minute"
                
                return {
                    "duration": human_duration,
                    "total_seconds": int(delta.total_seconds()),
                    "is_past": delta.total_seconds() > 0,
                    "reference": reference_time,
                    "current": now.isoformat()
                }
                
            except ValueError as e:
                return {"error": f"Invalid reference time format: {str(e)}"}
        
        elif duration:
            # Parse duration string
            parsed = self._parse_duration_string(duration)
            if parsed:
                return {
                    "parsed_duration": parsed,
                    "seconds": parsed["total_seconds"],
                    "human_format": duration
                }
            else:
                return {"error": f"Could not parse duration: {duration}"}
        
        else:
            return {"error": "Either reference_time or duration must be provided"}
    
    async def _get_relative_time(self, reference_time: Optional[str], format: str) -> Dict[str, Any]:
        """Get time relative to now or a reference."""
        now = datetime.now()
        
        if reference_time:
            try:
                ref_time = datetime.fromisoformat(reference_time)
            except ValueError:
                # Try parsing common relative terms
                if reference_time == "yesterday":
                    ref_time = now - timedelta(days=1)
                elif reference_time == "tomorrow":
                    ref_time = now + timedelta(days=1)
                elif reference_time == "last week":
                    ref_time = now - timedelta(weeks=1)
                elif reference_time == "next week":
                    ref_time = now + timedelta(weeks=1)
                else:
                    return {"error": f"Invalid reference time: {reference_time}"}
        else:
            ref_time = now
        
        # Calculate relative descriptions
        delta = ref_time - now
        abs_delta = abs(delta.total_seconds())
        
        if abs_delta < 60:
            relative = "just now"
        elif abs_delta < 3600:
            minutes = int(abs_delta / 60)
            relative = f"{minutes} minute{'s' if minutes != 1 else ''} {'ago' if delta.total_seconds() < 0 else 'from now'}"
        elif abs_delta < 86400:
            hours = int(abs_delta / 3600)
            relative = f"{hours} hour{'s' if hours != 1 else ''} {'ago' if delta.total_seconds() < 0 else 'from now'}"
        elif abs_delta < 604800:
            days = int(abs_delta / 86400)
            relative = f"{days} day{'s' if days != 1 else ''} {'ago' if delta.total_seconds() < 0 else 'from now'}"
        else:
            weeks = int(abs_delta / 604800)
            relative = f"{weeks} week{'s' if weeks != 1 else ''} {'ago' if delta.total_seconds() < 0 else 'from now'}"
        
        formatted_time = {
            "full": ref_time.isoformat(),
            "date": ref_time.strftime("%Y-%m-%d"),
            "time": ref_time.strftime("%H:%M:%S"),
            "timestamp": int(ref_time.timestamp()),
            "human": ref_time.strftime("%B %d, %Y at %I:%M %p")
        }
        
        return {
            "time": formatted_time.get(format, formatted_time["human"]),
            "relative": relative,
            "is_past": delta.total_seconds() < 0,
            "is_future": delta.total_seconds() > 0,
            "day_of_week": calendar.day_name[ref_time.weekday()]
        }
    
    async def _schedule_info(self, duration: Optional[str]) -> Dict[str, Any]:
        """Provide scheduling information."""
        now = datetime.now()
        
        if duration:
            parsed = self._parse_duration_string(duration)
            if parsed:
                future_time = now + timedelta(seconds=parsed["total_seconds"])
                
                return {
                    "scheduled_for": future_time.strftime("%B %d, %Y at %I:%M %p"),
                    "duration_from_now": duration,
                    "exact_time": future_time.isoformat(),
                    "day_of_week": calendar.day_name[future_time.weekday()],
                    "is_same_day": future_time.date() == now.date()
                }
            else:
                return {"error": f"Could not parse duration: {duration}"}
        else:
            # Provide general scheduling context
            return {
                "current_time": now.strftime("%I:%M %p"),
                "suggestions": {
                    "in_5_minutes": (now + timedelta(minutes=5)).strftime("%I:%M %p"),
                    "in_30_minutes": (now + timedelta(minutes=30)).strftime("%I:%M %p"),
                    "in_1_hour": (now + timedelta(hours=1)).strftime("%I:%M %p"),
                    "tomorrow_same_time": (now + timedelta(days=1)).strftime("%B %d at %I:%M %p")
                }
            }
    
    def _parse_duration_string(self, duration: str) -> Optional[Dict[str, Any]]:
        """Parse duration strings like '2 hours', '30 minutes'."""
        duration = duration.lower().strip()
        
        # Simple parsing for common patterns
        import re
        
        patterns = {
            r'(\d+)\s*seconds?': lambda x: int(x),
            r'(\d+)\s*minutes?': lambda x: int(x) * 60,
            r'(\d+)\s*hours?': lambda x: int(x) * 3600,
            r'(\d+)\s*days?': lambda x: int(x) * 86400,
            r'(\d+)\s*weeks?': lambda x: int(x) * 604800,
        }
        
        total_seconds = 0
        components = {}
        
        for pattern, converter in patterns.items():
            match = re.search(pattern, duration)
            if match:
                value = int(match.group(1))
                seconds = converter(value)
                total_seconds += seconds
                
                unit = pattern.split('\\s*')[1].replace('?', '')
                components[unit] = value
        
        if total_seconds > 0:
            return {
                "total_seconds": total_seconds,
                "components": components
            }
        
        return None