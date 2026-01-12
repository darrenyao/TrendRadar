# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TrendRadar is a lightweight trending news aggregation tool that monitors hot topics across 15+ Chinese platforms (Toutiao, Baidu, Weibo, Douyin, Bilibili, Zhihu, etc.) and delivers notifications through multiple channels. Version 3.0.5, MCP v1.0.1.

## Commands

### Run Crawler
```bash
python main.py                    # Run once
python main.py --mode cron        # Continuous mode with scheduler
```

### MCP Server
```bash
python -m mcp_server.server       # STDIO mode (for AI clients)
./start-http.sh                   # HTTP mode on localhost:3333
```

### Installation
```bash
# macOS
./setup-mac.sh

# Windows
setup-windows.bat

# Manual
pip install -r requirements.txt
```

### Docker
```bash
docker build -f docker/Dockerfile -t trendradar:latest .
cd docker && docker-compose up -d
./deploy-vps.sh                   # VPS one-click deployment
```

## Architecture

### Core Components

**main.py** (~4600 lines) - Monolithic crawler and notifier:
- `DataFetcher`: HTTP client for fetching news from platform APIs
- `NewsAnalyzer`: Filters news based on keywords from `frequency_words.txt`
- `PushRecordManager`: Tracks push history and time windows
- Notifier functions: `send_to_feishu()`, `send_to_dingtalk()`, `send_to_wework()`, `send_to_telegram()`, `send_to_email()`, `send_to_ntfy()`

**mcp_server/** - FastMCP 2.0 server for AI integration:
- `server.py`: Entry point with tool definitions (`get_latest_news`, `get_trending_topics`, `search_news`, `analyze_trends`)
- `tools/`: Tool implementations (data_query, analytics, search_tools, config_mgmt, system)
- `services/`: Data access layer (data_service, parser_service, cache_service)
- `utils/`: Validators, error handling, date parsing

### Data Flow

1. Crawler fetches from external APIs → saves to `output/` as JSON/HTML
2. MCP server reads from `output/` directory
3. Notifiers push to IM platforms/email based on config

### Configuration

- `config/config.yaml`: Main config (platforms, weights, notification webhooks, report mode)
- `config/frequency_words.txt`: Keywords to monitor (supports `+word` must-include, `!word` must-exclude)
- Environment variables can override config (see `.env.example`)

### Report Modes (in config.yaml)

- `daily`: Summary with all matches + new items
- `current`: Current rankings with matches
- `incremental`: Only new matches (push only on updates)

## Key Patterns

- Beijing timezone (Asia/Shanghai) hardcoded throughout
- File-based storage in `output/` directory (no database)
- Supercronic for Docker scheduling
- Multi-arch Docker images (amd64, arm64)
- GitHub Actions runs hourly crawler workflow

## Dependencies

Python 3.10+, requires: requests, pytz, PyYAML, fastmcp, websockets
