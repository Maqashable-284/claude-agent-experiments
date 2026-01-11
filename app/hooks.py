"""
Security Hooks for Scoop AI Agent.
Intercepts tool usage and user prompts for security validation.
"""

import logging
from typing import Any, Dict, Optional

from claude_agent_sdk import HookContext

logger = logging.getLogger("scoop_ai.hooks")


# ==================== Security Constants ====================

# Blocked dangerous keywords
BLOCKED_KEYWORDS = {
    # Illegal substances
    "steroid", "სტეროიდ", "anabolic", "ანაბოლიკ",
    "testosterone", "ტესტოსტერონ", "hgh", "sarm",
    # Hacking/Abuse
    "hack", "inject", "exploit", "bypass", "jailbreak",
    "ignore previous", "ignore instructions", "disregard",
    # Medical danger
    "overdose", "suicide", "kill", "die",
}

# Prompt injection patterns
INJECTION_PATTERNS = [
    # English patterns
    "ignore all previous",
    "forget your instructions",
    "you are now",
    "act as if",
    "pretend you are",
    "system prompt",
    "new instructions",
    "disregard all",
    "override your",
    # Instruction disclosure attempts
    "what are your instructions",
    "what is your instruction",
    "show me your prompt",
    "show your prompt",
    "tell me your instructions",
    "what were you told",
    "what is your system",
    "reveal your instructions",
    "your initial instructions",
    "your original instructions",
    "share your prompt",
    "display your instructions",
    "print your instructions",
    "output your instructions",
    "what's your prompt",
    "whats your prompt",
    "repeat your instructions",
    "copy your instructions",
    # Georgian patterns (ქართული)
    "რა არის შენი ინსტრუქცია",
    "რა ინსტრუქცია გაქვს",
    "შენი ინსტრუქცია",
    "სისტემის პრომთ",
    "სისტემური პრომთ",
    "მაჩვენე შენი პრომთი",
    "რა გითხრეს",
    "რა დავალება გაქვს",
    "შენი დავალება რა არის",
    "რა წესები გაქვს",
    "შენი წესები მაჩვენე",
    "როგორ ხარ დაპროგრამებული",
    "შენი კონფიგურაცია",
    "prompt injection",
    "jailbreak",
    "დაივიწყე ყველაფერი",
    "უგულებელყავი ინსტრუქციები",
]


# Maximum message length
MAX_MESSAGE_LENGTH = 5000


# ==================== Hook Implementations ====================

async def validate_user_prompt(
    input_data: Dict[str, Any],
    tool_use_id: Optional[str],
    context: HookContext
) -> Dict[str, Any]:
    """
    Hook: UserPromptSubmit
    Checks for blocked keywords and prompt injection before processing the prompt.

    This replaces the _security_check method from the original agent.py.
    """
    message = input_data.get("message", "") or input_data.get("prompt", "")
    message_lower = message.lower()

    # Check message length
    if len(message) > MAX_MESSAGE_LENGTH:
        logger.warning(f"Message too long: {len(message)} chars")
        return {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "permissionDecision": "deny",
                "permissionDecisionReason": "შეტყობინება ძალიან გრძელია. გთხოვთ, შეამოკლოთ.",
            }
        }

    # Check blocked keywords
    for keyword in BLOCKED_KEYWORDS:
        if keyword in message_lower:
            logger.warning(f"Blocked keyword detected: {keyword}")
            return {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "სამწუხაროდ, ჩვენ მხოლოდ ლეგალურ სპორტულ დანამატებზე ვაძლევთ რჩევებს.",
                }
            }

    # Check prompt injection patterns
    for pattern in INJECTION_PATTERNS:
        if pattern in message_lower:
            logger.warning(f"Prompt injection attempt detected: {pattern}")
            return {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "რით შემიძლია დაგეხმაროთ სპორტულ კვებასთან დაკავშირებით?",
                }
            }

    # Allow the prompt
    return {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "permissionDecision": "allow",
        }
    }


async def validate_tool_use(
    input_data: Dict[str, Any],
    tool_use_id: Optional[str],
    context: HookContext
) -> Dict[str, Any]:
    """
    Hook: PreToolUse
    Ensures only authorized tools are used.

    For Scoop AI, we only allow our MCP product tools.
    Block any other tools that might be added in the future.
    """
    tool_name = input_data.get("tool_name", "")

    # Allowed tools - only our MCP product tools
    allowed_tools = [
        "mcp__scoop-products__search_products",
        "mcp__scoop-products__get_product_details",
        "mcp__scoop-products__get_all_categories",
    ]

    if tool_name not in allowed_tools:
        logger.warning(f"Unauthorized tool blocked: {tool_name}")
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": f"Unauthorized tool: {tool_name}",
            }
        }

    logger.info(f"Tool authorized: {tool_name}")
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
        }
    }


async def log_tool_result(
    input_data: Dict[str, Any],
    tool_use_id: Optional[str],
    context: HookContext
) -> Dict[str, Any]:
    """
    Hook: PostToolUse
    Logs tool execution results for monitoring.
    """
    tool_name = input_data.get("tool_name", "")
    result = input_data.get("result", {})

    # Log tool execution (for monitoring/analytics)
    is_error = result.get("is_error", False)
    if is_error:
        logger.warning(f"Tool {tool_name} returned error")
    else:
        logger.info(f"Tool {tool_name} executed successfully")

    # PostToolUse hooks don't block, just observe
    return {}
