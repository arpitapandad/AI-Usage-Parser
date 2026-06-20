AI Usage Parser using mitmproxy

This is a lightweight AI traffic visibility demo built with mitmproxy that captures real browser-based LLM requests, normalizes them into a canonical event schema, and stores them for replay, inspection, and future analysis.

This project is a small but realistic prototype of the kind of observability and data-normalization work, that can be logged.

## What it does?

- Captures real AI chat traffic through mitmproxy
- Filters noisy browser traffic like assets, telemetry, and non-LLM requests
- Extracts prompts, responses, models, token estimates, and rough cost estimates
- Normalizes everything into a single `CanonicalEvent`
- Saves captured events to disk for replay and analysis
- Supports offline parser testing with saved fixtures
- Includes clean console logging with multiple verbosity modes

## Demo flow:

1. Start the proxy.
2. Turn on the Windows proxy.(Network & Settings)
3. Open Claude, ChatGPT, or Grok.
4. Send a message.
5. Watch only the relevant LLM POST traffic appear.
6. Inspect the captured canonical event.
7. Replay fixtures offline if you change the parser.

## What gets ignored

The parser intentionally ignores:

- image and asset requests
- telemetry and analytics requests
- non-LLM browser traffic
- empty capture events
- noisy background traffic from other apps


## Why this exists?

Modern LLM products do not speak one stable schema. In this prototype I have included ability to log 3 widely used AI's; Claude, ChatGPT, and Grok, all expose different request/response shapes, different streaming formats, and different traffic patterns.

This project solves that by:

- capturing browser traffic through a proxy
- filtering only real LLM chat completions
- parsing vendor-specific payloads into one stable event
- persisting structured events for replay and future analysis
- keeping the pipeline easy to debug and hard to break silently

## How to run:

### 1. Create and activate a virtual environment

```bash
python -m venv venv
source venv/Scripts/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Create your local config

```bash
cp .env.example .env
```

### 4. Run in visual mode

```bash
bash start_web.sh
```

This opens mitmweb at `http://127.0.0.1:8081`.

### 5. Or run in terminal mode

```bash
bash start_clean.sh
```

## Safety and privacy

This repository is designed to keep sensitive runtime data local:

- `.env` is not committed
- `events.json` stays local
- `venv/` stays local
- `.mitmproxy/` stays local


## License

For demo and application use.
