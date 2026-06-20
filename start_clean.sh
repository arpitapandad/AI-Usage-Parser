#!/usr/bin/env bash
# Clean terminal mode — only Oximy capture lines, no connection spam.
cd "$(dirname "$0")"
source venv/Scripts/activate
mitmdump -s llm_parser_addon.py -q --set termlog_verbosity=error
