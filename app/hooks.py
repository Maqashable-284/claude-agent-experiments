"""
Security Hooks Module - Guardrails for Agent Safety.

This module implements PreToolUse hooks using the official
claude-agent-sdk HookMatcher and HookContext patterns.
"""

import re
from typing import Any, Set

# Import types from claude_agent_sdk
# Note: HookContext is passed as third argument to hook callbacks
try:
    from claude_agent_sdk import HookMatcher
    from claude_agent_sdk.types import HookContext
except ImportError:
    # Fallback types for development
    HookMatcher = dict
    HookContext = dict


# ==================== Blocked Content Definitions ====================

BLOCKED_KEYWORDS: Set[str] = {
    # Dangerous substances
    "steroids",
    "სტეროიდები",
    "anabolic",
    "ანაბოლიკური",
    "hgh",
    "growth hormone",
    "ზრდის ჰორმონი",
    "testosterone injection",
    "ტესტოსტერონის ინექცია",
    
    # Prompt injection attempts
    "ignore previous instructions",
    "ignore all instructions",
    "უგულებელყავი წინა ინსტრუქციები",
    "disregard your instructions",
    "forget your rules",
    "you are now",
    "act as if",
    "pretend you are",
    
    # Security-related
    "hack",
    "exploit",
    "injection",
    "bypass",
    "admin password",
    "root access",
    
    # System commands
    "rm -rf",
    "drop table",
    "delete from",
    "eval(",
    "exec(",
    "__import__",
}

# Regex patterns for suspicious content
SUSPICIOUS_PATTERNS = [
    re.compile(r'<script.*?>.*?</script>', re.IGNORECASE | re.DOTALL),
    re.compile(r'\{\{.*?\}\}'),  # Template injection
    re.compile(r'\$\{.*?\}'),    # Variable injection
    re.compile(r'[\x00-\x1f]'),  # Control characters
]


# ==================== Hook Callbacks ====================

async def security_guardrail(
    input_data: dict[str, Any],
    tool_use_id: str | None,
    context: Any  # HookContext
) -> dict[str, Any]:
    """
    Main security hook that blocks dangerous content.
    
    This hook is called before every tool execution (PreToolUse event).
    It checks for blocked keywords and suspicious patterns.
    
    Args:
        input_data: Contains 'tool_name' and 'tool_input'
        tool_use_id: Unique identifier for this tool use
        context: Hook context with signal and session info
    
    Returns:
        Empty dict to allow, or dict with permissionDecision='deny' to block
    """
    # Extract content to check
    content_to_check = _extract_text_content(input_data)
    content_lower = content_to_check.lower()
    
    # Check blocked keywords
    for keyword in BLOCKED_KEYWORDS:
        if keyword.lower() in content_lower:
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": f"დაბლოკილია უსაფრთხოების მიზეზით: აკრძალული შინაარსი"
                }
            }
    
    # Check suspicious patterns
    for pattern in SUSPICIOUS_PATTERNS:
        if pattern.search(content_to_check):
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "დაბლოკილია: აღმოჩენილია საეჭვო შაბლონი"
                }
            }
    
    # Check input length (prevent DoS)
    if len(content_to_check) > 10000:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "დაბლოკილია: მოთხოვნა ზედმეტად დიდია"
            }
        }
    
    # Allow the request
    return {}


async def audit_log_hook(
    input_data: dict[str, Any],
    tool_use_id: str | None,
    context: Any
) -> dict[str, Any]:
    """
    Audit logging hook - logs all tool usage.
    Always allows the request but logs it for monitoring.
    """
    import logging
    logger = logging.getLogger("scoop_ai.audit")
    
    tool_name = input_data.get("tool_name", "unknown")
    logger.info(f"[AUDIT] Tool: {tool_name} | ID: {tool_use_id}")
    
    return {}  # Always allow


async def medical_disclaimer_hook(
    input_data: dict[str, Any],
    tool_use_id: str | None,
    context: Any
) -> dict[str, Any]:
    """
    Hook that adds medical disclaimer for health-related queries.
    Modifies the input to include a disclaimer reminder.
    """
    # Keywords that might require medical disclaimer
    medical_keywords = {
        "medication", "medicine", "health", "dose", "dosage",
        "წამალი", "ჯანმრთელობა", "დოზა", "დოზირება"
    }
    
    content = _extract_text_content(input_data).lower()
    
    if any(kw in content for kw in medical_keywords):
        # Add flag for agent to include disclaimer
        return {
            "metadata": {
                "include_medical_disclaimer": True
            }
        }
    
    return {}


# ==================== Helper Functions ====================

def _extract_text_content(data: dict[str, Any]) -> str:
    """
    Extract all text content from hook input data.
    Handles nested structures recursively.
    """
    texts = []
    
    def extract_recursive(obj: Any) -> None:
        if isinstance(obj, str):
            texts.append(obj)
        elif isinstance(obj, dict):
            for value in obj.values():
                extract_recursive(value)
        elif isinstance(obj, (list, tuple)):
            for item in obj:
                extract_recursive(item)
    
    extract_recursive(data)
    return " ".join(texts)


def add_blocked_keyword(keyword: str) -> None:
    """Add a keyword to the blocked list at runtime."""
    BLOCKED_KEYWORDS.add(keyword.lower())


def remove_blocked_keyword(keyword: str) -> None:
    """Remove a keyword from the blocked list."""
    BLOCKED_KEYWORDS.discard(keyword.lower())


# ==================== Pre-configured Hook Matchers ====================

# Security hook for all tools
security_hook_matcher = {
    "hooks": [security_guardrail, audit_log_hook]
}

# Medical disclaimer for search tools
medical_hook_matcher = {
    "matcher": "mcp__scoop__search_products",
    "hooks": [medical_disclaimer_hook]
}
