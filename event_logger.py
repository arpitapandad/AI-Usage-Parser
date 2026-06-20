"""Structured console logging — separate from event persistence."""

import logging
from dataclasses import dataclass, field
from typing import Dict

from config import LogMode, LOG_MODE, LOG_SUMMARY_INTERVAL


def setup_logging() -> logging.Logger:
    """Use a dedicated logger so we never hijack mitmproxy's root logger."""
    logger = logging.getLogger("oximy")
    logger.propagate = False
    logger.setLevel(logging.DEBUG if LOG_MODE == LogMode.DEBUG else logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)

    return logger


def silence_mitmproxy_logs(level_name: str = "error") -> None:
    """Hide mitmproxy's client connect / server connect spam."""
    level = getattr(logging, level_name.upper(), logging.ERROR)

    try:
        from mitmproxy.log import MitmLogHandler
    except ImportError:
        MitmLogHandler = None  # type: ignore

    root = logging.getLogger()
    for handler in root.handlers:
        if MitmLogHandler and isinstance(handler, MitmLogHandler):
            handler.setLevel(level)
        elif handler.__class__.__name__ == "TermLogHandler":
            handler.setLevel(level)

    for name in ("mitmproxy", "mitmproxy.proxy", "mitmproxy.proxy.server"):
        logging.getLogger(name).setLevel(level)


@dataclass
class TrafficStats:
    llm_flows_seen: int = 0
    chat_endpoints_seen: int = 0
    chat_captured: int = 0
    parse_errors: int = 0
    by_tool: Dict[str, int] = field(default_factory=dict)

    def summary_line(self) -> str:
        tools = ", ".join(f"{k}={v}" for k, v in sorted(self.by_tool.items())) or "none"
        return (
            f"Session: {self.chat_captured} events captured ({tools}) | "
            f"{self.chat_endpoints_seen} chat endpoints / {self.llm_flows_seen} LLM flows "
            f"| {self.parse_errors} errors"
        )


class EventLogger:
    def __init__(self, mode: LogMode = LOG_MODE):
        self.mode = mode
        self.log = setup_logging()
        self.stats = TrafficStats()

    def startup(self) -> None:
        if self.mode == LogMode.SILENT:
            return
        self.log.info(
            f"Oximy parser ready | log_mode={self.mode.value} "
            f"| capturing chat completions only"
        )

    def request_seen(self, url: str) -> None:
        if self.mode in (LogMode.VERBOSE, LogMode.DEBUG):
            self.log.info(f"-> {url}")

    def event_captured(
        self,
        tool: str,
        prompt_len: int,
        response_len: int,
        model: str | None = None,
        tokens_in: int | None = None,
        tokens_out: int | None = None,
    ) -> None:
        if self.mode == LogMode.SILENT:
            return

        model_part = f" | {model}" if model else ""
        token_part = ""
        if tokens_in is not None or tokens_out is not None:
            token_part = f" | tokens {tokens_in or 0}/{tokens_out or 0}"

        if self.mode == LogMode.DEBUG:
            self.log.info(
                f"[event] {tool}{model_part} | prompt={prompt_len}ch "
                f"response={response_len}ch{token_part}"
            )
        else:
            self.log.info(
                f"Captured {tool}{model_part} | "
                f"{prompt_len}ch in -> {response_len}ch out{token_part}"
            )

    def parse_error(self, message: str) -> None:
        self.stats.parse_errors += 1
        self.log.error(message)

    def maybe_summary(self, force: bool = False) -> None:
        if self.mode == LogMode.SILENT and not force:
            return
        if force or (LOG_SUMMARY_INTERVAL and self.stats.chat_captured % LOG_SUMMARY_INTERVAL == 0):
            self.log.info(self.stats.summary_line())

    def shutdown(self) -> None:
        if self.mode != LogMode.DEBUG:
            self.log.info(self.stats.summary_line())
