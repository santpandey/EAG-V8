# EAG-V8 AI Agent Telegram Bot

## Project Overview
EAG-V8 is an advanced AI agent system designed to perform complex tasks using a multi-tool approach, including web search, email sending, and Google Sheets integration.

## Key Features
- Telegram Bot Interface
- Multi-Context Processor (MCP) Architecture
- Dynamic Tool Selection
- Web Search Capabilities
- Google Workspace Integration
  - Gmail Sending
  - Google Sheets Creation

## Setup Instructions

### 1. Telegram Bot Configuration
- Message @BotFather on Telegram
- Use `/newbot` command
- Follow instructions to get your bot token

### 2. Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configuration
- Open `config.py`
- Replace `'YOUR_BOT_TOKEN_HERE'` with your actual bot token
- Configure Google Cloud credentials

### 4. Google Cloud Setup
- Create a Google Cloud project
- Enable Gmail and Sheets APIs
- Download and configure:
  - `gmail.json`
  - `token.json`

### 5. Run the Bot
```bash
python telegram_bot.py
```

## Main Components
- `telegram_bot.py`: Telegram interface
- `agent.py`: Core agent logic
- `mcp_server_3.py`: Multi-tool processor
- `core/`: Agent architecture modules

## Current Capabilities
- Web searching
- Sending emails
- Creating Google Sheets
- Dynamic task processing

## Logging
Logs are generated in the application directory for debugging and tracking.

## Version
V8 (May 2025)

## License
Proprietary - EAG Technologies

## Bot Features
- `/start`: Greets the user
- `/help`: Shows available commands
- Echoes back any message sent to it

## Notes
- Ensure you have Python 3.7+ installed
- Keep your bot token secret!
