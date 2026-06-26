
import os
from enum import Enum
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent


class LogMode(str, Enum):
    """Console logging verbosity for the addon."""

    SILENT = "silent"      # errors + session summary only
    EVENTS = "events"      # one clean line per captured canonical event (default)
    VERBOSE = "verbose"    # request URL + event details
    DEBUG = "debug"        # includes filtered-traffic counters


# Domains we care about (used for flow_filter + is_real_chat)
LLM_DOMAINS = tuple(
    d.strip()
    for d in os.getenv(
        "LLM_DOMAINS",
        "claude.ai,anthropic.com,a-api.anthropic.com,chatgpt.com,grok.com",
    ).split(",")
    if d.strip()
)

CHAT_PATH_KEYWORDS = tuple(
    k.strip()
    for k in os.getenv(
        "CHAT_PATH_KEYWORDS",
        "/v1/messages,/v1/chat/completions,chat_conversations/,/completion,backend-api,api/chat,conversation",
    ).split(",")
    if k.strip()
)

# Regex: ignore all hosts that are NOT claude/anthropic/openai (stops bing, spotify, etc.)
IGNORE_HOSTS_PATTERN = os.getenv(
    "IGNORE_HOSTS_PATTERN",
    r"^(?!.*(claude\.ai|anthropic\.com|a-api\.anthropic\.com|chatgpt\.com|grok\.com)).*",
)

LOG_MODE = LogMode(os.getenv("LOG_MODE", "events").lower())
EVENTS_FILE = Path(os.getenv("EVENTS_FILE", PROJECT_ROOT / "events.json"))
SAVE_EVENTS = os.getenv("SAVE_EVENTS", "true").lower() in ("1", "true", "yes")
LOG_SUMMARY_INTERVAL = int(os.getenv("LOG_SUMMARY_INTERVAL", "0"))  # 0 = only on shutdown

# Suppress mitmproxy's "client connect" / "server connect" noise (error = only failures)
TERMLOG_VERBOSITY = os.getenv("TERMLOG_VERBOSITY", "error")

# Addon-internal domain filter expression (mitmproxy 12+)
FLOW_FILTER = os.getenv(
    "FLOW_FILTER",
    " | ".join(f"~d {domain}" for domain in LLM_DOMAINS),
)
