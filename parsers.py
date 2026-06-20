"""Vendor-specific payload parsing — reusable by proxy addon and replay harness."""

import hashlib
import json
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from mitmproxy import http

from config import CHAT_PATH_KEYWORDS, LLM_DOMAINS
from schemas import CanonicalEvent

# Rough $/1M tokens for demo cost estimates (not billing-accurate)
COST_PER_MILLION = {
    "claude-3-5-sonnet": {"in": 3.0, "out": 15.0},
    "claude-3-opus": {"in": 15.0, "out": 75.0},
    "gpt-4o": {"in": 2.5, "out": 10.0},
    "gpt-4o-mini": {"in": 0.15, "out": 0.6},
    "default": {"in": 3.0, "out": 12.0},
}


def is_on_llm_domain(host: str) -> bool:
    host = host.lower()
    return any(domain in host for domain in LLM_DOMAINS)


def is_real_chat(flow: http.HTTPFlow) -> bool:
    if flow.request.method != "POST":
        return False
    if not is_on_llm_domain(flow.request.pretty_host):
        return False

    path = flow.request.path.lower()
    noise = ("datadog", "analytics", "telemetry", "/events", "health", "metrics", "split.io")
    if any(token in path for token in noise):
        return False

    return True


def has_meaningful_content(prompt: Optional[str], response_content: Optional[str]) -> bool:
    """Skip empty heartbeats / metadata calls that match chat paths."""
    return bool((prompt or "").strip() or (response_content or "").strip())


def get_tool(host: str) -> str:
    host = host.lower()
    if "claude" in host or "anthropic" in host:
        return "anthropic"
    if "openai" in host:
        return "openai"
    return "other"


def extract_prompt(request_text: Optional[str]) -> Optional[str]:
    if not request_text:
        return None
    try:
        data = json.loads(request_text)
    except json.JSONDecodeError:
        return None

    if "messages" in data:
        contents = []
        for message in data.get("messages", []):
            content = message.get("content")
            if isinstance(content, str):
                contents.append(content)
            elif isinstance(content, list):
                for item in content:
                    if item.get("type") == "text":
                        contents.append(item.get("text", ""))
        return "\n".join(contents) or None

    if "prompt" in data:
        return data["prompt"]
    return None


def extract_response(response_text: str, content_type: str) -> Optional[str]:
    if not response_text:
        return None

    if "event-stream" in content_type:
        parts = []
        for line in response_text.splitlines():
            if not line.startswith("data: ") or "{" not in line:
                continue
            try:
                chunk = json.loads(line[6:])
            except json.JSONDecodeError:
                continue
            delta = chunk.get("delta", {}) or chunk
            if isinstance(delta, dict):
                if "text" in delta:
                    parts.append(delta["text"])
                elif delta.get("type") == "content_block_delta":
                    parts.append(delta.get("delta", {}).get("text", ""))
        return "".join(parts) or None

    try:
        data = json.loads(response_text)
    except json.JSONDecodeError:
        return None

    if isinstance(data.get("content"), str):
        return data["content"]
    if data.get("choices"):
        return data["choices"][0].get("message", {}).get("content")
    return None


def extract_model(request_text: Optional[str], response_text: Optional[str]) -> Optional[str]:
    for text in (request_text, response_text):
        if not text:
            continue
        try:
            data = json.loads(text.splitlines()[0] if "data: " in text[:20] else text)
        except (json.JSONDecodeError, IndexError):
            continue
        model = data.get("model")
        if model:
            return model
    return None


def estimate_tokens(text: Optional[str]) -> Optional[int]:
    if not text:
        return None
    return max(1, len(text) // 4)


def estimate_cost(model: Optional[str], tokens_in: Optional[int], tokens_out: Optional[int]) -> Optional[float]:
    if tokens_in is None and tokens_out is None:
        return None
    rates = COST_PER_MILLION.get(model or "", COST_PER_MILLION["default"])
    cost = 0.0
    if tokens_in:
        cost += (tokens_in / 1_000_000) * rates["in"]
    if tokens_out:
        cost += (tokens_out / 1_000_000) * rates["out"]
    return round(cost, 6)


def build_canonical_event(flow: http.HTTPFlow) -> CanonicalEvent:
    request_text = flow.request.text
    response_text = flow.response.get_text() or ""
    content_type = str(flow.response.headers.get("content-type", ""))

    prompt = extract_prompt(request_text)
    response_content = extract_response(response_text, content_type)
    model = extract_model(request_text, response_text)
    tokens_in = estimate_tokens(prompt)
    tokens_out = estimate_tokens(response_content)

    return CanonicalEvent(
        event_id=str(uuid.uuid4()),
        timestamp=datetime.utcnow(),
        tool=get_tool(flow.request.pretty_host),
        action="chat_completion",
        prompt=prompt[:500] if prompt else None,
        request_model=model,
        response_content=response_content[:1000] if response_content else None,
        response_model=model,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_estimate=estimate_cost(model, tokens_in, tokens_out),
        status="complete",
        raw_url=flow.request.pretty_url,
        raw_payload_hash=hashlib.sha256(response_text.encode()).hexdigest()[:16],
        metadata={"host": flow.request.pretty_host},
    )


def detect_schema_drift(request_text: Optional[str], tool: str) -> Optional[str]:
    """Flag payloads that look like chat but don't match known shapes."""
    if not request_text:
        return None
    try:
        data = json.loads(request_text)
    except json.JSONDecodeError:
        return "request_not_json"

    if tool == "anthropic" and "messages" not in data and "prompt" not in data:
        return "anthropic_unknown_shape"
    if tool == "openai" and "messages" not in data:
        return "openai_unknown_shape"
    return None


def event_from_fixture(
    *,
    tool: str,
    request_text: str,
    response_text: str,
    content_type: str = "application/json",
    url: str = "fixture://replay",
) -> Tuple[CanonicalEvent, Optional[str]]:
    """Build a canonical event from saved raw payloads (replay harness)."""
    prompt = extract_prompt(request_text)
    response_content = extract_response(response_text, content_type)
    model = extract_model(request_text, response_text)
    tokens_in = estimate_tokens(prompt)
    tokens_out = estimate_tokens(response_content)

    event = CanonicalEvent(
        event_id=str(uuid.uuid4()),
        timestamp=datetime.utcnow(),
        tool=tool,  # type: ignore[arg-type]
        action="chat_completion",
        prompt=prompt[:500] if prompt else None,
        request_model=model,
        response_content=response_content[:1000] if response_content else None,
        response_model=model,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_estimate=estimate_cost(model, tokens_in, tokens_out),
        status="complete",
        raw_url=url,
        raw_payload_hash=hashlib.sha256(response_text.encode()).hexdigest()[:16],
        metadata={"source": "replay_fixture"},
    )
    drift = detect_schema_drift(request_text, tool)
    return event, drift
