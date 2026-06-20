from mitmproxy import ctx, flowfilter, http

from config import EVENTS_FILE, FLOW_FILTER, SAVE_EVENTS, TERMLOG_VERBOSITY
from event_logger import EventLogger, silence_mitmproxy_logs
from event_store import append_event
from parsers import build_canonical_event, has_meaningful_content, is_on_llm_domain, is_real_chat


class LLMParserAddon:
    def __init__(self):
        self.logger = EventLogger()
        self._domain_filter = None

    def load(self, loader):
        loader.add_option(
            name="oximy_flow_filter",
            typespec=str,
            default=FLOW_FILTER,
            help="Only process flows matching this mitmproxy filter expression",
        )

    def configure(self, updated):
        if "oximy_flow_filter" in updated:
            expr = ctx.options.oximy_flow_filter.strip()
            if not expr:
                self._domain_filter = None
            else:
                try:
                    self._domain_filter = flowfilter.parse(expr)
                except ValueError as exc:
                    ctx.log.error(f"Invalid oximy_flow_filter: {exc}")
                    self._domain_filter = None
        else:
            return

        ctx.options.termlog_verbosity = TERMLOG_VERBOSITY
        silence_mitmproxy_logs(TERMLOG_VERBOSITY)

    def _should_process(self, flow: http.HTTPFlow) -> bool:
        if self._domain_filter:
            return bool(self._domain_filter(flow))
        return is_on_llm_domain(flow.request.pretty_host)

    def running(self):
        ctx.options.termlog_verbosity = TERMLOG_VERBOSITY
        silence_mitmproxy_logs(TERMLOG_VERBOSITY)
        self.logger.startup()
        self.logger.log.info(
            "Tip: run ./start_web.sh for a visual UI, or ./start_clean.sh for terminal-only."
        )

    def done(self):
        self.logger.shutdown()

    def request(self, flow: http.HTTPFlow):
        if not self._should_process(flow):
            return

        self.logger.stats.llm_flows_seen += 1
        if is_real_chat(flow):
            self.logger.stats.chat_endpoints_seen += 1
            self.logger.request_seen(flow.request.pretty_url)

    def response(self, flow: http.HTTPFlow):
        if not self._should_process(flow) or not is_real_chat(flow):
            return

        try:
            event = build_canonical_event(flow)
            if not has_meaningful_content(event.prompt, event.response_content):
                return

            prompt_len = len(event.prompt or "")
            response_len = len(event.response_content or "")

            self.logger.stats.chat_captured += 1
            self.logger.stats.by_tool[event.tool] = (
                self.logger.stats.by_tool.get(event.tool, 0) + 1
            )
            self.logger.event_captured(
                tool=event.tool,
                prompt_len=prompt_len,
                response_len=response_len,
                model=event.request_model,
                tokens_in=event.tokens_in,
                tokens_out=event.tokens_out,
            )

            if SAVE_EVENTS:
                append_event(EVENTS_FILE, event)

            self.logger.maybe_summary()

        except Exception as exc:
            self.logger.parse_error(f"Parse failed for {flow.request.pretty_url}: {exc}")


addons = [LLMParserAddon()]
