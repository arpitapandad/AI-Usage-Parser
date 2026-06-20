#!/usr/bin/env bash
# Visual mode — open http://127.0.0.1:8081 in your browser to see flows.
# Use the UI search bar to focus on Claude / ChatGPT / Grok traffic after capture.
cd "$(dirname "$0")"
source venv/Scripts/activate
echo ""
echo "  Proxy:  127.0.0.1:8080  (set Windows proxy to this)"
echo "  Web UI: http://127.0.0.1:8081"
echo "  Search in the UI: ~m POST & (~d claude.ai | ~d anthropic.com | ~d a-api.anthropic.com | ~d chatgpt.com | ~d grok.com)"
echo ""
mitmweb -s llm_parser_addon.py --set termlog_verbosity=error --set view_filter='~m POST & (~d claude.ai | ~d anthropic.com | ~d a-api.anthropic.com | ~d chatgpt.com | ~d grok.com)'
